import yfinance as yf
import pandas as pd
import numpy as np
import streamlit as st
import requests
from streamlit_autorefresh import st_autorefresh
from scipy.signal import argrelextrema
from datetime import datetime, timedelta

st.set_page_config(page_title="Entry Signal Dashboard", layout="wide")
st.title("📈 Peppy's Final Intraday Entry Signal Dashboard")

# 🔁 Auto-refresh every 2 minutes
st_autorefresh(interval=120000, limit=None, key="refresh")

# --- User Inputs ---
ticker = st.text_input("Enter Ticker Symbol", value="AAPL")
lookback_days = st.selectbox(
    "Select Lookback Period for Insider & Analyst Activity:",
    options=[30, 60, 90],
    format_func=lambda x: f"Last {x} Days"
)

# --- Date Range for Filtering ---
today = datetime.today()
from_date = (today - timedelta(days=lookback_days)).strftime("%Y-%m-%d")
to_date = today.strftime("%Y-%m-%d")

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

# --- Finnhub API Key ---
finnhub_api_key = "d1g2cp1r01qk4ao0k610d1g2cp1r01qk4ao0k61g"

# --- News Sentiment ---
def fetch_news_sentiment(symbol, api_key):
    url = f"https://finnhub.io/api/v1/news-sentiment?symbol={symbol}&token={api_key}"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            bullish = data.get("sentiment", {}).get("bullishPercent", 0)
            bearish = data.get("sentiment", {}).get("bearishPercent", 0)
            score = bullish - bearish
            sentiment = (
                "Positive" if score > 5 else
                "Negative" if score < -5 else
                "Neutral"
            )
            return sentiment, round(bullish, 2), round(bearish, 2)
        else:
            return "Unavailable", 0, 0
    except:
        return "Error", 0, 0

sentiment, bullish, bearish = fetch_news_sentiment(ticker, finnhub_api_key)
st.markdown("### 📰 News Sentiment")
st.write(f"**Overall Sentiment:** {sentiment}")
st.write(f"**Bullish %:** {bullish}%")
st.write(f"**Bearish %:** {bearish}%")

# --- Analyst Ratings ---
st.markdown("### 📊 Analyst Recommendations")
analyst_url = f"https://finnhub.io/api/v1/stock/recommendation?symbol={ticker}&token={finnhub_api_key}"
try:
    response = requests.get(analyst_url)
    data = response.json()
    filtered = [r for r in data if from_date <= r['period'] <= to_date]
    if filtered:
        df_analyst = pd.DataFrame(filtered)[["period", "strongBuy", "buy", "hold", "sell", "strongSell"]]
        st.dataframe(df_analyst.set_index("period"))
    else:
        st.info("No analyst data found for selected range.")
except:
    st.warning("Failed to fetch analyst data.")

# --- Insider Trades ---
st.markdown("### 🕵️ Insider Transactions")
insider_url = f"https://finnhub.io/api/v1/stock/insider-transactions?symbol={ticker}&from={from_date}&to={to_date}&token={finnhub_api_key}"
try:
    response = requests.get(insider_url)
    data = response.json().get("data", [])
    if data:
        df_insider = pd.DataFrame(data)[["name", "transactionDate", "transactionType", "share", "price"]]
        st.dataframe(df_insider.sort_values("transactionDate", ascending=False).reset_index(drop=True))
    else:
        st.info("No insider trades found for selected range.")
except:
    st.warning("Failed to fetch insider trade data.")

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
        breakout_strength = "Strong" if current_volume >= 1.5 * avg_volume else "Weak"
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

# --- Display Final Data ---
if results:
    st.markdown("### 📋 Indicator & Signal Summary")
    st.dataframe(pd.DataFrame(results).set_index("Interval"))
else:
    st.warning("No data found. Try a different ticker or wait for more candles to build.")
