import pandas as pd
import numpy as np
import ta
import time
import datetime
import requests
import streamlit as st

# ========= CONFIG ========= #
API_KEY = "d1g2cp1r01qk4ao0k610d1g2cp1r01qk4ao0k61g"  # ← Your Finnhub API Key
tickers = ['AAPL', 'MSFT', 'NVDA', 'AMD', 'TSLA', 'GOOGL', 'AMZN', 'META', 'NFLX', 'INTC']

# ========= UI LAYOUT ========= #
st.set_page_config(page_title="Day Trading Scout", layout="wide")
st.title("📈 Smart Day Trading Scout - Buy Signal Detector")

st.sidebar.header("Settings")
interval = st.sidebar.selectbox("Interval (min)", ["5", "15", "30"], index=1)
lookback_candles = st.sidebar.slider("Candles to Analyze", 50, 300, 100)
scan_button = st.sidebar.button("🔍 Start Scan")

# ========= DATA FETCH ========= #
def fetch_ohlcv(symbol, resolution, count):
    now = int(time.time())
    past = now - (count * 60 * int(resolution))
    url = f"https://finnhub.io/api/v1/stock/candle?symbol={symbol}&resolution={resolution}&from={past}&to={now}&token={API_KEY}"
    res = requests.get(url).json()
    if res.get("s") != "ok":
        return pd.DataFrame()
    df = pd.DataFrame({
        't': pd.to_datetime(res['t'], unit='s'),
        'o': res['o'],
        'h': res['h'],
        'l': res['l'],
        'c': res['c'],
        'v': res['v']
    })
    df.set_index('t', inplace=True)
    return df

# ========= INDICATOR LOGIC ========= #
def analyze_stock(df):
    if df.empty or len(df) < 30:
        return None
    df['rsi'] = ta.momentum.RSIIndicator(df['c']).rsi()
    df['macd'] = ta.trend.MACD(df['c']).macd_diff()
    df['vwap'] = (df['v'] * (df['h'] + df['l'] + df['c']) / 3).cumsum() / df['v'].cumsum()
    df['vol_spike'] = df['v'] > df['v'].rolling(20).mean() * 1.5

    last = df.iloc[-1]
    signals = {
        "RSI < 35": last['rsi'] < 35,
        "MACD > 0": last['macd'] > 0,
        "Price > VWAP": last['c'] > last['vwap'],
        "Volume Spike": last['vol_spike']
    }
    score = sum(signals.values())
    return {
        "Ticker": df.name,
        "Price": round(last['c'], 2),
        "Score": score,
        **signals
    }

# ========= RUN SCAN ========= #
results = []
if scan_button:
    with st.spinner("Scanning tickers..."):
        for symbol in tickers:
            df = fetch_ohlcv(symbol, interval, lookback_candles)
            df.name = symbol
            data = analyze_stock(df)
            if data:
                results.append(data)

    if results:
        result_df = pd.DataFrame(results)
        result_df.sort_values(by="Score", ascending=False, inplace=True)
        st.success(f"Scan complete! Showing top results for {interval}min interval:")
        st.dataframe(result_df, use_container_width=True)
    else:
        st.warning("No valid signals detected.")
