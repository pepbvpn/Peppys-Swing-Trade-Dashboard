
import pandas as pd
import numpy as np
import ta
import time
import requests
import streamlit as st
from math import ceil

API_KEY = "d1g2cp1r01qk4ao0k610d1g2cp1r01qk4ao0k61g"

st.set_page_config(page_title="Day Trading Dashboard", layout="wide")
st.title("📊 Day Trading Dashboard")

tab1, tab2 = st.tabs(["📈 Scout (S&P 500 Scan)", "📋 Buy & Track"])

# ========= Scout Mode ========= #
with tab1:
    st.subheader("📈 S&P 500 Smart Scanner")
    st.sidebar.header("Scout Settings")
    interval = st.sidebar.selectbox("Time Interval", ["5", "15", "30"], index=1)
    lookback_candles = st.sidebar.slider("Candles to Analyze", 50, 300, 100)

    @st.cache_data
    def load_sp500():
        url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
        df = pd.read_html(url)[0]
        return df["Symbol"].tolist()

    tickers = load_sp500()
    batch_size = 50
    num_batches = ceil(len(tickers) / batch_size)
    selected_batch = st.sidebar.selectbox(
        "Select Batch (Each ~50 tickers)",
        options=[f"Batch {i+1}" for i in range(num_batches)]
    )
    batch_index = int(selected_batch.split(" ")[1]) - 1
    current_batch = tickers[batch_index * batch_size : (batch_index + 1) * batch_size]

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

    scan_button = st.sidebar.button("🔍 Start Scan")
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
                time.sleep(1)

        if results:
            result_df = pd.DataFrame(results)
            result_df.sort_values(by=["Score", "Ticker"], ascending=[False, True], inplace=True)
            st.success(f"Scan complete! Showing results for {selected_batch}")
            st.dataframe(result_df, use_container_width=True)
        else:
            st.warning("No valid signals found.")

# ========= Buy & Track Mode ========= #
with tab2:
    st.subheader("📋 Buy & Track Mode")
    symbol = st.text_input("Enter Ticker (e.g., AAPL)", value="AAPL")
    buy_price = st.number_input("Your Buy Price ($)", value=100.0, format="%.2f")
    interval_bt = st.selectbox("Interval", ["5", "15", "30"], index=1, key="bt_interval")
    lookback_bt = st.slider("Candles to Fetch", 50, 300, 100, key="bt_lookback")
    check_button = st.button("Check Sell Signals")

    def check_sell_signals(df, buy_price):
        df['rsi'] = ta.momentum.RSIIndicator(df['c']).rsi()
        df['macd'] = ta.trend.MACD(df['c']).macd_diff()
        df['vwap'] = (df['v'] * (df['h'] + df['l'] + df['c']) / 3).cumsum() / df['v'].cumsum()
        df['vol_avg'] = df['v'].rolling(20).mean()

        last = df.iloc[-1]
        signals = {
            "RSI > 70": last['rsi'] > 70,
            "MACD < 0": last['macd'] < 0,
            "Price < VWAP": last['c'] < last['vwap'],
            "Volume Drop": last['v'] < last['vol_avg']
        }

        score = sum(signals.values())
        if score >= 3:
            status = "🔻 Time to Sell"
        elif score == 2:
            status = "⚠️ Watch Closely"
        else:
            status = "✅ Hold"

        return {
            "Current Price": round(last['c'], 2),
            "Buy Price": round(buy_price, 2),
            "Unrealized P/L": round(last['c'] - buy_price, 2),
            "Sell Signal Score": score,
            "Recommendation": status,
            **signals
        }

    if check_button:
        df = fetch_ohlcv(symbol.upper(), interval_bt, lookback_bt)
        if df.empty:
            st.error("Failed to fetch data. Try again.")
        else:
            result = check_sell_signals(df, buy_price)
            st.subheader("🔍 Signal Analysis")
            st.write(pd.DataFrame([result]))
