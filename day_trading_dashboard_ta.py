import streamlit as st
import pandas as pd
import yfinance as yf
import ta
import numpy as np

st.set_page_config(page_title="Swing Trade Multi-Interval Scanner", layout="wide")
st.title("📈 Swing Trade Signal Strength Dashboard")

tickers = [
    "NVDA", "AAPL", "MSFT", "TSLA", "SPY", "AMZN", "HOOD", "META", "WMT", "UNH",
    "QQQ", "AMD", "TSM", "SMH", "XLY", "COIN", "AVGO", "BRK.B", "GOOGL"
]
st.markdown(f"**Scanning Tickers:** {', '.join(tickers)}")

intervals = ["15m", "1h", "1d"]
period_map = {"15m": "10d", "1h": "60d", "1d": "1y"}

def safe_round(val, digits=2):
    try:
        return round(float(val), digits)
    except:
        return "N/A"

def classify_strength(trends, sentiments):
    all_bullish = all(t == "📈 Bullish" for t in trends)
    all_accum = all(s == "📈 Accumulating" for s in sentiments)
    any_bearish_dist = any(t == "📉 Bearish" and s == "📉 Distributing" for t, s in zip(trends, sentiments))
    any_both = any(t == "📈 Bullish" and s == "📈 Accumulating" for t, s in zip(trends, sentiments))
    all_have_either = all(t == "📈 Bullish" or s == "📈 Accumulating" for t, s in zip(trends, sentiments))

    if all_bullish and all_accum:
        return "✅ PERFECT"
    elif all_have_either and any_both:
        return "💪 STRONG"
    elif any_bearish_dist:
        return "⚠️ WEAK"
    else:
        return "😐 NEUTRAL"

@st.cache_data(show_spinner=False)
def get_trend_sentiment(ticker, interval):
    try:
        df = yf.download(ticker, interval=interval, period=period_map[interval], progress=False)
        if df.empty or len(df) < 50:
            return "❓", "❓"

        close = df['Close']
        volume = df['Volume']
        obv = ta.volume.OnBalanceVolumeIndicator(close=close, volume=volume).on_balance_volume()
        df["OBV"] = obv
        sma50 = close.rolling(50).mean()
        sma200 = close.rolling(200).mean()

        trend = "❓"
        sentiment = "❓"

        if not np.isnan(close.iloc[-1]) and not np.isnan(sma50.iloc[-1]) and not np.isnan(sma200.iloc[-1]):
            if close.iloc[-1] > sma50.iloc[-1] and sma50.iloc[-1] > sma200.iloc[-1]:
                trend = "📈 Bullish"
            elif close.iloc[-1] < sma50.iloc[-1] and sma50.iloc[-1] < sma200.iloc[-1]:
                trend = "📉 Bearish"
            else:
                trend = "↔️ Neutral"

        if len(df["OBV"]) >= 6:
            obv_diff = df["OBV"].iloc[-1] - df["OBV"].iloc[-6]
            if obv_diff > 0:
                sentiment = "📈 Accumulating"
            elif obv_diff < 0:
                sentiment = "📉 Distributing"
            else:
                sentiment = "➖ Neutral"

        return trend, sentiment

    except Exception as e:
        return "❓", "❓"

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
    results.append({"Ticker": ticker, "Signal Strength": strength, **interval_details})

df = pd.DataFrame(results)

if not df.empty:
    st.dataframe(df)
    st.download_button("Download CSV", df.to_csv(index=False), file_name="multi_interval_signals.csv")
else:
    st.info("No data available for selected tickers.")
