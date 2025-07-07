import yfinance as yf
import pandas as pd
import numpy as np
import streamlit as st
from streamlit_autorefresh import st_autorefresh
from scipy.signal import argrelextrema

st.set_page_config(page_title="Entry Signal Dashboard", layout="wide")
st.title("📈 Peppy's Final Intraday Entry Signal Dashboard")

# 🔁 Auto-refresh every 2 minutes
st_autorefresh(interval=120000, limit=None, key="refresh")

# --- User Inputs ---
ticker = st.text_input("Enter Ticker Symbol", value="AAPL")

# --- Show Current Price ---
if ticker:
    try:
        info = yf.Ticker(ticker).info
        current_price = info.get("regularMarketPrice")
        if current_price:
            st.subheader(f"📌 Current Market Price of {ticker.upper()}: ${round(current_price, 2)}")
    except:
        st.warning("Could not fetch current price. Try another ticker.")

option_type = st.selectbox("Trade Direction", ["CALL", "PUT"])
intervals = ["15m", "1h", "1d"]

# --- Indicator Calculations ---
def compute_indicators(data):
    delta = data['Close'].diff()
    gain = np.where(delta > 0, delta, 0)
    loss = np.where(delta < 0, -delta, 0)
    avg_gain = pd.Series(gain, index=data.index).rolling(window=14).mean()
    avg_loss = pd.Series(loss, index=data.index).rolling(window=14).mean()
    rs = avg_gain / avg_loss
    data['RSI'] = 100 - (100 / (1 + rs))

    ema12 = data['Close'].ewm(span=12, adjust=False).mean()
    ema26 = data['Close'].ewm(span=26, adjust=False).mean()
    data['MACD'] = ema12 - ema26
    data['Signal'] = data['MACD'].ewm(span=9, adjust=False).mean()

    data['TP'] = (data['High'] + data['Low'] + data['Close']) / 3
    data['VP'] = data['TP'] * data['Volume']
    data['Cumulative_VP'] = data['VP'].cumsum()
    data['Cumulative_Volume'] = data['Volume'].cumsum()
    data['VWAP'] = data['Cumulative_VP'] / data['Cumulative_Volume']

    data['SMA_50'] = data['Close'].rolling(window=50).mean()
    data['SMA_200'] = data['Close'].rolling(window=200).mean()
    return data

# --- Support/Resistance Detection ---
def get_support_resistance(data, order=10):
    close = data['Close']
    local_min = argrelextrema(close.values, np.less_equal, order=order)[0]
    local_max = argrelextrema(close.values, np.greater_equal, order=order)[0]
    support = close.iloc[local_min].tail(3).mean() if len(local_min) > 0 else np.nan
    resistance = close.iloc[local_max].tail(3).mean() if len(local_max) > 0 else np.nan
    return round(support, 2), round(resistance, 2)

# --- Results Collection ---
results = []

for interval in intervals:
    period = {"15m": "10d", "1h": "30d", "1d": "1y"}[interval]
    df = yf.download(ticker, interval=interval, period=period, progress=False)

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    if df.empty:
        continue

    df = compute_indicators(df)
    latest = df.iloc[-1]
    price = latest['Close']

    support, resistance = get_support_resistance(df)
    near_support = "Yes" if not np.isnan(support) and price <= support * 1.02 else "No"
    near_resistance = "Yes" if not np.isnan(resistance) and price >= resistance * 0.98 else "No"

    # Breakout Strength Logic
    avg_volume = df['Volume'].rolling(window=20).mean().iloc[-1]
    current_volume = latest['Volume']
    if not np.isnan(resistance) and price > resistance:
        if current_volume >= 1.5 * avg_volume:
            breakout_strength = "Strong"
        else:
            breakout_strength = "Weak"
    else:
        breakout_strength = "No Breakout"

    # Signal Logic
    signals = {
        "RSI Signal": "✅" if (option_type == "CALL" and latest['RSI'] < 35) or
                               (option_type == "PUT" and latest['RSI'] > 70) else "❌",
        "MACD Signal": "✅" if (option_type == "CALL" and latest['MACD'] > latest['Signal']) or
                                (option_type == "PUT" and latest['MACD'] < latest['Signal']) else "❌",
        "VWAP Signal": "✅" if (option_type == "CALL" and price > latest['VWAP']) or
                                (option_type == "PUT" and price < latest['VWAP']) else "❌",
        "SMA Trend": "✅" if (option_type == "CALL" and price > latest['SMA_50'] > latest['SMA_200']) or
                               (option_type == "PUT" and price < latest['SMA_50'] < latest['SMA_200']) else "❌"
    }

    score = list(signals.values()).count("✅")

    results.append({
        "Interval": interval,
        "Close": round(price, 2),
        "RSI": round(latest['RSI'], 2),
        "MACD": round(latest['MACD'], 3),
        "Signal": round(latest['Signal'], 3),
        "VWAP": round(latest['VWAP'], 2),
        "SMA_50": round(latest['SMA_50'], 2),
        "SMA_200": round(latest['SMA_200'], 2),
        "Support": support,
        "Resistance": resistance,
        "Near Support": near_support,
        "Near Resistance": near_resistance,
        "Breakout Strength": breakout_strength,
        **signals,
        "Trade Readiness Score": f"{score}/4"
    })

# --- Display ---
if results:
    st.dataframe(pd.DataFrame(results).set_index("Interval"))
else:
    st.warning("No data found. Try a different ticker or wait for more candles to build.")
