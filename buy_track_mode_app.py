
import pandas as pd
import ta
import time
import requests
import streamlit as st

API_KEY = "d1g2cp1r01qk4ao0k610d1g2cp1r01qk4ao0k61g"

st.set_page_config(page_title="Buy & Track Mode", layout="centered")
st.title("📊 Stock Buy & Track Assistant")

symbol = st.text_input("Enter Ticker (e.g., AAPL)", value="AAPL")
buy_price = st.number_input("Your Buy Price ($)", value=100.0, format="%.2f")
interval = st.selectbox("Interval", ["5", "15", "30"], index=1)
lookback = st.slider("Candles to Fetch", 50, 300, 100)

check_button = st.button("Check Sell Signals")

def fetch_data(symbol, resolution, count):
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
    df = fetch_data(symbol.upper(), interval, lookback)
    if df.empty:
        st.error("Failed to fetch data. Try again.")
    else:
        result = check_sell_signals(df, buy_price)
        st.subheader("🔍 Signal Analysis")
        st.write(pd.DataFrame([result]))
