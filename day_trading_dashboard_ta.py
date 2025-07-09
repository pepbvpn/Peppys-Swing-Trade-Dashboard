import streamlit as st
import pandas as pd
import yfinance as yf
import ta
import numpy as np
import requests
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

# --------- Shared Config ---------
st.set_page_config(page_title="Multi-Dashboard Swing Trade App", layout="wide")
st.title("📊 Peppy's Multi-Dashboard Swing Trade Scanner")

# Refresh every 5 mins
st_autorefresh(interval=300000, limit=None, key="auto-refresh")

# Last refreshed time in CST
now = datetime.now().astimezone()
now_cst = now.astimezone().strftime('%Y-%m-%d %H:%M')
st.markdown(f"**Last Refreshed:** {now_cst} CST")

# --------- Functions Shared by Both Dashboards ---------
period_map = {"15m": "10d", "1h": "60d", "1d": "1y"}
intervals = ["15m", "1h", "1d"]

def classify_strength(trends, sentiments):
    if all(t == "📈 Bullish" for t in trends) and all(s == "📈 Accumulating" for s in sentiments):
        return "✅ PERFECT"
    if sum(t == "🔽 Bearish" for t in trends) >= 2:
        return "⚠️ WEAK"
    if all(s == "🔽 Distributing" for s in sentiments):
        return "⚠️ WEAK"
    for t, s in zip(trends, sentiments):
        if t == "🔽 Bearish" and s == "🔽 Distributing":
            return "⚠️ WEAK"
    if all(t in ["📈 Bullish", "↔️ Neutral"] for t in trends) and \
       all(s in ["📈 Accumulating", "📉 Distributing"] for s in sentiments):
        has_both = any(t == "📈 Bullish" and s == "📈 Accumulating" for t, s in zip(trends, sentiments))
        dist_count = sum(s == "📉 Distributing" for s in sentiments)
        if has_both and dist_count <= 1:
            return "💪 STRONG"
    return "😐 NEUTRAL"

@st.cache_data(show_spinner=False)
def get_trend_sentiment(ticker, interval):
    yf_ticker = "BRK-B" if ticker.upper() == "BRK.B" else ticker.upper()
    try:
        df = yf.download(yf_ticker, interval=interval, period=period_map[interval], progress=False)
        if df.empty or "Close" not in df.columns or "Volume" not in df.columns:
            return "❓", "❓"

        close = df['Close'].dropna().squeeze()
        volume = df['Volume'].dropna().squeeze()
        if len(close) < 60 or len(volume) < 60:
            return "❓", "❓"

        obv = ta.volume.OnBalanceVolumeIndicator(close=close, volume=volume).on_balance_volume()
        df["OBV"] = obv
        sma50 = close.rolling(50).mean()
        sma200 = close.rolling(200).mean()

        # Trend
        if close.iloc[-1] > sma50.iloc[-1] > sma200.iloc[-1]:
            trend = "📈 Bullish"
        elif close.iloc[-1] < sma50.iloc[-1] < sma200.iloc[-1]:
            trend = "🔽 Bearish"
        else:
            trend = "↔️ Neutral"

        # Sentiment
        obv_diff = df["OBV"].iloc[-1] - df["OBV"].iloc[-6]
        if obv_diff > 0:
            sentiment = "📈 Accumulating"
        elif obv_diff < 0:
            sentiment = "🔽 Distributing"
        else:
            sentiment = "➖ Neutral"

        return trend, sentiment
    except:
        return "❓", "❓"

# --------- Tab 1: S&P 500 Dashboard ---------
@st.cache_data(show_spinner=False)
def get_sp500_tickers():
    url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
    tables = pd.read_html(requests.get(url).text)
    df = tables[0]
    return df["Symbol"].str.replace(".", "-", regex=False).tolist()

def sp500_dashboard():
    tickers = get_sp500_tickers()
    st.subheader(f"S&P 500 Scanner — Scanning {len(tickers)} Stocks")

    results = []
    for ticker in tickers:
        trend_list, sentiment_list, interval_details = [], [], {}
        for interval in intervals:
            trend, sentiment = get_trend_sentiment(ticker, interval)
            trend_list.append(trend)
            sentiment_list.append(sentiment)
            interval_details[f"{interval} Trend"] = trend
            interval_details[f"{interval} Sentiment"] = sentiment

        strength = classify_strength(trend_list, sentiment_list)
        display_ticker = "BRK.B" if ticker == "BRK-B" else ticker
        results.append({"Ticker": display_ticker, "Signal Strength": strength, **interval_details})

    df = pd.DataFrame(results)
    signal_filter = st.selectbox("Filter by Signal Strength:", ["All"] + df["Signal Strength"].unique().tolist())
    if signal_filter != "All":
        df = df[df["Signal Strength"] == signal_filter]

    st.dataframe(df)
    st.download_button("Download CSV", df.to_csv(index=False), file_name="sp500_signals.csv")

# --------- Tab 2: Peppy's Custom Dashboard ---------
def custom_dashboard():
    tickers = [
        "NVDA", "AAPL", "MSFT", "TSLA", "SPY", "AMZN", "HOOD", "META", "WMT", "UNH",
        "QQQ", "AMD", "TSM", "SMH", "XLY", "COIN", "AVGO", "BRK.B", "GOOGL"
    ]
    st.subheader("Peppy's Custom Watchlist")

    results = []
    for ticker in tickers:
        trend_list, sentiment_list, interval_details = [], [], {}
        for interval in intervals:
            trend, sentiment = get_trend_sentiment(ticker, interval)
            trend_list.append(trend)
            sentiment_list.append(sentiment)
            interval_details[f"{interval} Trend"] = trend
            interval_details[f"{interval} Sentiment"] = sentiment

        strength = classify_strength(trend_list, sentiment_list)
        display_ticker = "BRK.B" if ticker == "BRK.B" else ticker
        results.append({"Ticker": display_ticker, "Signal Strength": strength, **interval_details})

    df = pd.DataFrame(results)
    signal_filter = st.selectbox("Filter by Signal Strength:", ["All"] + df["Signal Strength"].unique().tolist(), key="custom_filter")
    if signal_filter != "All":
        df = df[df["Signal Strength"] == signal_filter]

    st.dataframe(df)
    st.download_button("Download CSV", df.to_csv(index=False), file_name="custom_watchlist.csv")

# --------- Tabs ---------
tab1, tab2 = st.tabs(["S&P 500 Scanner", "Peppy's Watchlist"])
with tab1:
    sp500_dashboard()
with tab2:
    custom_dashboard()
