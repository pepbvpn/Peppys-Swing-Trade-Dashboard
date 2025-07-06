import yfinance as yf
import pandas as pd
import numpy as np
import streamlit as st

st.set_page_config(page_title="Day Trade Signal App", layout="wide")
st.title("📊 Day Trading Signal Scanner")

# Input tickers
tickers = st.text_input("Enter comma-separated tickers", "AAPL,TSLA,NVDA,SPY").upper().split(",")
tickers = [t.strip() for t in tickers if t.strip()]
intervals = {"15m": "10d", "1h": "30d"}

# Indicator logic
def compute_indicators(df):
    delta = df['Close'].diff()
    gain = pd.Series(np.where(delta > 0, delta, 0), index=df.index)
    loss = pd.Series(np.where(delta < 0, -delta, 0), index=df.index)
    avg_gain = gain.rolling(window=14).mean()
    avg_loss = loss.rolling(window=14).mean()
    rs = avg_gain / avg_loss
    df['RSI'] = 100 - (100 / (1 + rs))

    ema12 = df['Close'].ewm(span=12, adjust=False).mean()
    ema26 = df['Close'].ewm(span=26, adjust=False).mean()
    df['MACD'] = ema12 - ema26
    df['Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()

    df['TP'] = (df['High'] + df['Low'] + df['Close']) / 3
    df['VP'] = df['TP'] * df['Volume']
    df['Cumulative_VP'] = df['VP'].cumsum()
    df['Cumulative_Volume'] = df['Volume'].cumsum()
    df['VWAP'] = df['Cumulative_VP'] / df['Cumulative_Volume']

    df['SMA_50'] = df['Close'].rolling(window=50).mean()
    df['SMA_200'] = df['Close'].rolling(window=200).mean()
    return df

# Scan tickers
results = []

for ticker in tickers:
    combined_scores = {}
    for interval, period in intervals.items():
        df = yf.download(ticker, interval=interval, period=period, progress=False, auto_adjust=False)
        if df.empty:
            continue
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df = compute_indicators(df)
        latest = df.iloc[-1]

        # Signal logic
        signals = {
            "RSI": latest['RSI'] < 35 or latest['RSI'] > 70,
            "MACD": (latest['MACD'] > latest['Signal']) or (latest['MACD'] < latest['Signal']),
            "VWAP": (latest['Close'] > latest['VWAP']) or (latest['Close'] < latest['VWAP']),
            "SMA": (latest['Close'] > latest['SMA_50'] > latest['SMA_200']) or 
                   (latest['Close'] < latest['SMA_50'] < latest['SMA_200']),
        }
        score = sum(signals.values())
        combined_scores[interval] = score

        results.append({
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

    # Combined signal row
    score15 = combined_scores.get("15m", 0)
    score1h = combined_scores.get("1h", 0)
    if score15 >= 3 and score1h >= 3:
        signal = "🔥 Strong Buy"
    elif score1h >= 3 and score15 < 3:
        signal = "⏳ Wait for 15m"
    elif score15 >= 3 and score1h < 3:
        signal = "⚠️ Only short-term setup"
    else:
        signal = "❌ Skip"

    results.append({
        "Ticker": ticker,
        "Interval": "Summary",
        "Close": "",
        "RSI": "",
        "MACD": "",
        "Signal": "",
        "VWAP": "",
        "SMA_50": "",
        "SMA_200": "",
        "Score": f"{score15}/4 + {score1h}/4",
        "Trade Signal": signal
    })

# Display
df = pd.DataFrame(results)
if not df.empty:
    st.dataframe(df)
else:
    st.error("No data was retrieved. Try again or check tickers.")
