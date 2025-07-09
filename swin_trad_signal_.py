import streamlit as st
import pandas as pd
import yfinance as yf
import ta
import numpy as np
from datetime import datetime
from pytz import timezone
from streamlit_autorefresh import st_autorefresh

# Page setup
st.set_page_config(page_title="Swing Trade Multi-Interval Scanner", layout="wide")
st.title("📈 Peppy's Ultimate Swing Trade Signal Strength Dashboard")

# Auto-refresh every 5 minutes (300000 ms)
st_autorefresh(interval=300000, limit=None, key="auto-refresh")

# Display last refresh time in CST (24-hour format)
central = timezone('America/Chicago')
now_local = datetime.now(central)
st.caption(f"🔄 Last refreshed: {now_local.strftime('%Y-%m-%d %H:%M:%S CST')}")

# Tickers to scan
tickers = [
    "NVDA", "AAPL", "MSFT", "TSLA", "SPY", "AMZN", "HOOD", "META", "WMT", "UNH",
    "QQQ", "AMD", "TSM", "SMH", "XLY", "COIN", "AVGO", "BRK.B", "GOOGL"
]
st.markdown(f"**Scanning Tickers:** {', '.join(tickers)}")

intervals = ["15m", "1h", "1d"]
period_map = {"15m": "10d", "1h": "60d", "1d": "1y"}

# Final signal strength classification
def classify_strength(trends, sentiments):
    if all(t == "📈 Bullish" for t in trends) and all(s == "📈 Accumulating" for s in sentiments):
        return "✅ PERFECT"
    if sum(t == "📉 Bearish" for t in trends) >= 2 or all(s == "📉 Distributing" for s in sentiments):
        return "⚠️ WEAK"
    if any(t == "📉 Bearish" and s == "📉 Distributing" for t, s in zip(trends, sentiments)):
        return "⚠️ WEAK"
    if all(t in ["📈 Bullish", "↔️ Neutral"] for t in trends) and \
       all(s in ["📈 Accumulating", "📉 Distributing"] for s in sentiments):
        has_bullish_accum = any(t == "📈 Bullish" and s == "📈 Accumulating" for t, s in zip(trends, sentiments))
        if has_bullish_accum and sum(s == "📉 Distributing" for s in sentiments) <= 1:
            return "💪 STRONG"
    return "😐 NEUTRAL"

# Download + classify trend/sentiment per interval
@st.cache_data(show_spinner=False)
def get_trend_sentiment(ticker, interval):
    yf_ticker = "BRK-B" if ticker.upper() == "BRK.B" else ticker.upper()
    try:
        df = yf.download(yf_ticker, interval=interval, period=period_map[interval], progress=False)
        if df.empty or "Close" not in df.columns or "Volume" not in df.columns:
            return "❓", "❓"

        close = df["Close"].dropna().squeeze()
        volume = df["Volume"].dropna().squeeze()
        if len(close) < 60 or len(volume) < 60:
            return "❓", "❓"

        obv = ta.volume.OnBalanceVolumeIndicator(close=close, volume=volume).on_balance_volume()
        df["OBV"] = obv
        sma50 = close.rolling(50).mean()
        sma200 = close.rolling(200).mean()

        # Trend
        trend = "↔️ Neutral"
        if close.iloc[-1] > sma50.iloc[-1] > sma200.iloc[-1]:
            trend = "📈 Bullish"
        elif close.iloc[-1] < sma50.iloc[-1] < sma200.iloc[-1]:
            trend = "📉 Bearish"

        # Sentiment
        sentiment = "➖ Neutral"
        obv_diff = obv.iloc[-1] - obv.iloc[-6]
        if obv_diff > 0:
            sentiment = "📈 Accumulating"
        elif obv_diff < 0:
            sentiment = "📉 Distributing"

        return trend, sentiment

    except Exception as e:
        st.text(f"Error for {ticker} at {interval}: {e}")
        return "❓", "❓"

# Run scan
results = []
for ticker in tickers:
    trend_list, sentiment_list = [], []
    interval_details = {}
    for interval in intervals:
        trend, sentiment = get_trend_sentiment(ticker, interval)
        trend_list.append(trend)
        sentiment_list.append(sentiment)
        interval_details[f"{interval} Trend"] = trend
        interval_details[f"{interval} Sentiment"] = sentiment
    strength = classify_strength(trend_list, sentiment_list)
    display_ticker = "BRK.B" if ticker == "BRK.B" else ticker
    results.append({"Ticker": display_ticker, "Signal Strength": strength, **interval_details})

# Display results
df = pd.DataFrame(results)
if not df.empty:
    options = ["All"] + sorted(df["Signal Strength"].unique().tolist())
    selected = st.selectbox("Filter by Signal Strength", options)
    if selected != "All":
        df = df[df["Signal Strength"] == selected]
    st.dataframe(df)
    st.download_button("Download CSV", df.to_csv(index=False), file_name="multi_interval_signals.csv")
else:
    st.info("No data available for selected tickers.")
