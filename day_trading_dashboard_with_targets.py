import yfinance as yf
import pandas as pd
import numpy as np
import streamlit as st

st.set_page_config(page_title="Day Trading Signal Scanner", layout="wide")
st.title("📈 Day Trading Scanner (15m + 1h) with Combined Trade Signal")

# --- Ticker Input ---
tickers = st.text_input("Enter comma-separated tickers", "AAPL,TSLA,NVDA,SPY,AMD,META").upper().split(",")
tickers = [t.strip() for t in tickers if t.strip()]

intervals = {"15m": "10d", "1h": "30d"}

# --- Indicator Function ---
def compute_indicators(data):
    delta = data['Close'].diff()
    gain = pd.Series(np.where(delta > 0, delta, 0), index=data.index)
    loss = pd.Series(np.where(delta < 0, -delta, 0), index=data.index)
    avg_gain = gain.rolling(window=14).mean()
    avg_loss = loss.rolling(window=14).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    data['RSI'] = rsi

    ema12 = data['Close'].ewm(span=12, adjust=False).mean()
    ema26 = data['Close'].ewm(span=26, adjust=False).mean()
    macd = ema12 - ema26
    signal = macd.ewm(span=9, adjust=False).mean()
    data['MACD'] = macd
    data['Signal'] = signal

    data['TP'] = (data['High'] + data['Low'] + data['Close']) / 3
    volume = data['Volume'] if isinstance(data['Volume'], pd.Series) else data['Volume'].iloc[:, 0]
    data['VP'] = data['TP'] * volume
    data['Cumulative_VP'] = data['VP'].cumsum()
    data['Cumulative_Volume'] = volume.cumsum()
    data['VWAP'] = data['Cumulative_VP'] / data['Cumulative_Volume']

    data['SMA_50'] = data['Close'].rolling(window=50).mean()
    data['SMA_200'] = data['Close'].rolling(window=200).mean()

    return data

# --- Scan Logic ---
raw_results = []

for ticker in tickers:
    interval_scores = {}
    for interval, period in intervals.items():
        df = yf.download(ticker, interval=interval, period=period, progress=False)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        if df.empty:
            continue

        df = compute_indicators(df)
        latest = df.iloc[-1]

        signals = {
            "RSI": latest['RSI'] < 35 or latest['RSI'] > 70,
            "MACD": (latest['MACD'] > latest['Signal']) or (latest['MACD'] < latest['Signal']),
            "VWAP": (latest['Close'] > latest['VWAP']) or (latest['Close'] < latest['VWAP']),
            "SMA": (latest['Close'] > latest['SMA_50'] > latest['SMA_200']) or 
                   (latest['Close'] < latest['SMA_50'] < latest['SMA_200']),
        }

        score = sum(signals.values())
        interval_scores[interval] = score

        raw_results.append({
            "Ticker": ticker,
            "Interval": interval,
            "Close": round(latest['Close'], 2),
            "RSI": round(latest['RSI'], 2),
            "MACD": round(latest['MACD'], 3),
            "Signal": round(latest['Signal'], 3),
            "VWAP": round(latest['VWAP'], 2),
            "SMA_50": round(latest['SMA_50'], 2),
            "SMA_200": round(latest['SMA_200'], 2),
            "Score": f"{score}/4"
        })

    # --- Combined Signal ---
    score_15m = interval_scores.get("15m", 0)
    score_1h = interval_scores.get("1h", 0)

    if score_15m >= 3 and score_1h >= 3:
        signal = "🔥 Strong Buy (Both 15m & 1h)"
    elif score_1h >= 3 and score_15m < 3:
        signal = "⏳ Wait for 15m Setup"
    elif score_15m >= 3 and score_1h < 3:
        signal = "⚠️ Short-Term Move Only"
    else:
        signal = "❌ Skip"

    raw_results.append({
        "Ticker": ticker,
        "Interval": "Summary",
        "Close": "",
        "RSI": "",
        "MACD": "",
        "Signal": "",
        "VWAP": "",
        "SMA_50": "",
        "SMA_200": "",
        "Score": f"{score_15m}/4 + {score_1h}/4",
        "Trade Signal": signal
    })

# --- Display Results ---
df = pd.DataFrame(raw_results)
if not df.empty:
    st.dataframe(df)
else:
    st.warning("No data returned. Try valid tickers or check your internet.")
