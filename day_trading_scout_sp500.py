
import pandas as pd
import numpy as np
import ta
import time
import requests
import streamlit as st
from math import ceil

# ========= CONFIG ========= #
API_KEY = "d1g2cp1r01qk4ao0k610d1g2cp1r01qk4ao0k61g"

# ========= UI ========= #
st.set_page_config(page_title="Day Trading Scout", layout="wide")
st.title("📈 Smart Day Trading Scout – S&P 500 Scanner")

st.sidebar.header("Settings")
interval = st.sidebar.selectbox("Time Interval", ["5", "15", "30"], index=1)
lookback_candles = st.sidebar.slider("Candles to Analyze", 50, 300, 100)

# ========= LOAD S&P 500 ========= #
@st.cache_data
def load_sp500():
    url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
    df = pd.read_html(url)[0]
    return df["Symbol"].tolist()

tickers = load_sp500()

# ========= BATCHING ========= #
batch_size = 50
num_batches = ceil(len(tickers) / batch_size)
selected_batch = st.sidebar.selectbox(
    "Select Batch (Each ~50 tickers)",
    options=[f"Batch {i+1}" for i in range(num_batches)]
)
batch_index = int(selected_batch.split(" ")[1]) - 1
current_batch = tickers[batch_index * batch_size : (batch_index + 1) * batch_size]

scan_button = st.sidebar.button("🔍 Start Scan")

# ========= FETCH FROM FINNHUB ========= #
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

# ========= ANALYSIS ========= #
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

    if score == 4:
        label = "🔥 High Conviction Buy"
    elif score == 3:
        label = "⚠️ Watch List"
    else:
        label = "❌ Skip for Now"

    return {
        "Ticker": df.name,
        "Price": round(last['c'], 2),
        "Score": score,
        "Status": label,
        **signals
    }

# ========= SCAN ========= #
results = []
if scan_button:
    with st.spinner("Scanning tickers..."):
        for i, symbol in enumerate(current_batch):
            st.sidebar.write(f"{i+1}/{len(current_batch)} scanning: {symbol}")
            df = fetch_ohlcv(symbol, interval, lookback_candles)
            df.name = symbol
            data = analyze_stock(df)
            if data:
                results.append(data)
            time.sleep(1)  # Respect Finnhub rate limits

    if results:
        result_df = pd.DataFrame(results)
        result_df.sort_values(by=["Score", "Ticker"], ascending=[False, True], inplace=True)
        st.success(f"Scan complete! Showing results for {selected_batch}")
        st.dataframe(result_df, use_container_width=True)
    else:
        st.warning("No valid signals found.")
