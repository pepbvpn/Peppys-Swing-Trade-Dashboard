import yfinance as yf
import pandas as pd
import numpy as np
import streamlit as st
from streamlit_autorefresh import st_autorefresh

st.set_page_config(page_title="Day Trade Signal App", layout="wide")
st.title("📊 Day Trading Signal Scanner")

# 🔁 Auto-refresh every 2 minutes
st_autorefresh(interval=120000, limit=None, key="refresh")

# --- Ticker Input ---
tickers = st.text_input("Enter comma-separated tickers", value="AAPL,TSLA,SPY,NVDA,AMD").upper().split(",")

# --- Interval to Period Mapping ---
intervals = {
    "15m": "10d",
    "1h": "30d"
}

# --- Indicator Function ---
def compute_indicators(data):
    delta = data['Close'].diff().squeeze()
    gain = pd.Series(np.where(delta > 0, delta, 0), index=data.index)
    loss = pd.Series(np.where(delta < 0, -delta, 0), index=data.index)
    avg_gain = gain.rolling(window=14).mean()
    avg_loss = loss.rolling(window=14).mean()
    rs = avg_gain / avg_loss
    data['RSI'] = 100 - (100 / (1 + rs))

    ema12 = data['Close'].ewm(span=12, adjust=False).mean()
    ema26 = data['Close'].ewm(span=26, adjust=False).mean()
    data['MACD'] = ema12 - ema26
    data['Signal'] = data['MACD'].ewm(span=9, adjust=False).mean()

    data['TP'] = (data['High'] + data['Low'] + data['Close']) / 3
    volume = data['Volume']
    if isinstance(volume, pd.DataFrame):
        volume = volume.iloc[:, 0]
    data['VP'] = data['TP'] * volume
    data['Cumulative_VP'] = data['VP'].cumsum()
    data['Cumulative_Volume'] = volume.cumsum()
    data['VWAP'] = data['Cumulative_VP'] / data['Cumulative_Volume']

    data['SMA_50'] = data['Close'].rolling(window=50).mean()
    data['SMA_200'] = data['Close'].rolling(window=200).mean()
    
    return data

# --- Main Logic ---
results = []

for ticker in tickers:
    ticker_rows = []
    combined_scores = {}

    for interval, period in intervals.items():
        df = yf.download(ticker, interval=interval, period=period, progress=False)
        if df.empty:
            continue

        df = compute_indicators(df)
        latest = df.iloc[-1]

        # ✅ Safe checks with NaN handling
        rsi_signal = "✅" if pd.notna(latest['RSI']) and latest['RSI'] < 35 else "❌"
        macd_signal = "✅" if pd.notna(latest['MACD']) and pd.notna(latest['Signal']) and latest['MACD'] > latest['Signal'] else "❌"
        vwap_signal = "✅" if pd.notna(latest['VWAP']) and latest['Close'] > latest['VWAP'] else "❌"
        sma_trend = "✅" if pd.notna(latest['SMA_50']) and pd.notna(latest['SMA_200']) and latest['Close'] > latest['SMA_50'] > latest['SMA_200'] else "❌"

        score = [rsi_signal, macd_signal, vwap_signal, sma_trend].count("✅")
        combined_scores[interval] = score

        ticker_rows.append({
            "Ticker": ticker,
            "Interval": interval,
            "Close": round(latest['Close'], 2),
            "RSI": round(latest['RSI'], 2) if pd.notna(latest['RSI']) else "-",
            "MACD": round(latest['MACD'], 3) if pd.notna(latest['MACD']) else "-",
            "Signal": round(latest['Signal'], 3) if pd.notna(latest['Signal']) else "-",
            "VWAP": round(latest['VWAP'], 2) if pd.notna(latest['VWAP']) else "-",
            "SMA_50": round(latest['SMA_50'], 2) if pd.notna(latest['SMA_50']) else "-",
            "SMA_200": round(latest['SMA_200'], 2) if pd.notna(latest['SMA_200']) else "-",
            "RSI Signal": rsi_signal,
            "MACD Signal": macd_signal,
            "VWAP Signal": vwap_signal,
            "SMA Trend": sma_trend,
            "Trade Readiness Score": f"{score}/4"
        })

    # Final signal summary
    if combined_scores:
        score15 = combined_scores.get("15m", 0)
        score1h = combined_scores.get("1h", 0)

        if score15 == 4 and score1h == 4:
            final_signal = "🚨 PERFECT SETUP (4/4 x 2)"
        elif score15 >= 3 and score1h >= 3:
            final_signal = "🔥 Strong Buy"
        elif score1h >= 3 and score15 < 3:
            final_signal = "⏳ Wait for 15m"
        elif score15 >= 3 and score1h < 3:
            final_signal = "⚠️ Short-term Setup Only"
        else:
            final_signal = "❌ Skip"

        ticker_rows.append({
            "Ticker": ticker,
            "Interval": "Summary",
            "Close": "-",
            "RSI": "-",
            "MACD": "-",
            "Signal": "-",
            "VWAP": "-",
            "SMA_50": "-",
            "SMA_200": "-",
            "RSI Signal": "-",
            "MACD Signal": "-",
            "VWAP Signal": "-",
            "SMA Trend": "-",
            "Trade Readiness Score": f"{score15}/4 + {score1h}/4",
            "Final Signal": final_signal
        })

    results.extend(ticker_rows)

# --- Display Table ---
df = pd.DataFrame(results)
if not df.empty:
    st.dataframe(df.set_index(["Ticker", "Interval"]))
else:
    st.warning("No valid trade setups yet. Try again shortly.")
