import yfinance as yf
import pandas as pd
import numpy as np
import streamlit as st

st.set_page_config(page_title="Entry Signal Dashboard", layout="wide")
st.title("📈 Intraday Entry Signal Dashboard")

# --- User Inputs ---
ticker = st.text_input("Enter Ticker Symbol", value="AAPL")
option_type = st.selectbox("Trade Direction", ["CALL", "PUT"])
intervals = ["15m", "1h"]

# --- Function to Compute Indicators ---
def compute_indicators(data):
    # --- RSI ---
    delta = data['Close'].diff()
    gain = pd.Series(np.where(delta > 0, delta, 0), index=data.index)
    loss = pd.Series(np.where(delta < 0, -delta, 0), index=data.index)
    avg_gain = gain.rolling(window=14).mean()
    avg_loss = loss.rolling(window=14).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    data['RSI'] = rsi

    # --- MACD ---
    ema12 = data['Close'].ewm(span=12, adjust=False).mean()
    ema26 = data['Close'].ewm(span=26, adjust=False).mean()
    macd = ema12 - ema26
    signal = macd.ewm(span=9, adjust=False).mean()
    data['MACD'] = macd
    data['Signal'] = signal

    # --- VWAP ---
    data['TP'] = (data['High'] + data['Low'] + data['Close']) / 3
    volume = data['Volume'] if isinstance(data['Volume'], pd.Series) else data['Volume'].iloc[:, 0]
    data['VP'] = data['TP'] * volume
    data['Cumulative_VP'] = data['VP'].cumsum()
    data['Cumulative_Volume'] = volume.cumsum()
    data['VWAP'] = data['Cumulative_VP'] / data['Cumulative_Volume']

    # --- SMA ---
    data['SMA_50'] = data['Close'].rolling(window=50).mean()
    data['SMA_200'] = data['Close'].rolling(window=200).mean()

    return data

# --- Get and Display Data ---
results = []

for interval in intervals:
    period = "2d" if interval == "15m" else "7d"
    df = yf.download(ticker, interval=interval, period=period, progress=False)

    # 🔧 Flatten MultiIndex Columns if Present
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    if df.empty:
        continue

    df = compute_indicators(df)
    latest = df.iloc[-1]

    # --- Entry Signal Logic ---
    signals = {
        "RSI Signal": "✅" if (
            option_type == "CALL" and latest['RSI'] < 35
        ) or (
            option_type == "PUT" and latest['RSI'] > 70
        ) else "❌",
        "MACD Signal": "✅" if (
            option_type == "CALL" and latest['MACD'] > latest['Signal']
        ) or (
            option_type == "PUT" and latest['MACD'] < latest['Signal']
        ) else "❌",
        "VWAP Signal": "✅" if (
            option_type == "CALL" and latest['Close'] > latest['VWAP']
        ) or (
            option_type == "PUT" and latest['Close'] < latest['VWAP']
        ) else "❌",
        "SMA Trend": "✅" if (
            option_type == "CALL" and latest['Close'] > latest['SMA_50'] > latest['SMA_200']
        ) or (
            option_type == "PUT" and latest['Close'] < latest['SMA_50'] < latest['SMA_200']
        ) else "❌"
    }

    score = list(signals.values()).count("✅")

    results.append({
        "Interval": interval,
        "Close": round(latest['Close'], 2),
        "RSI": round(latest['RSI'], 2),
        "MACD": round(latest['MACD'], 3),
        "Signal": round(latest['Signal'], 3),
        "VWAP": round(latest['VWAP'], 2),
        "SMA_50": round(latest['SMA_50'], 2),
        "SMA_200": round(latest['SMA_200'], 2),
        **signals,
        "Trade Readiness Score": f"{score}/4"
    })

# --- Display Results ---
if results:
    st.dataframe(pd.DataFrame(results).set_index("Interval"))
else:
    st.warning("No data found. Try a different ticker or wait for more candles to build.")
