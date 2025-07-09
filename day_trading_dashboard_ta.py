import streamlit as st
import pandas as pd
import yfinance as yf
import ta
import numpy as np
from streamlit_autorefresh import st_autorefresh

# Page setup
st.set_page_config(page_title="Swing Trade Multi-Interval Scanner", layout="wide")
st.title("📈 Pep's Selected Stocks Swing Trade Signal Strength Dashboard")

# Auto-refresh every 2 minutes (120000 ms)
st_autorefresh(interval=120000, limit=None, key="auto-refresh")

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
    # ✅ PERFECT: All Bullish AND All Accumulating
    if all(t == "📈 Bullish" for t in trends) and all(s == "📈 Accumulating" for s in sentiments):
        return "✅ PERFECT"

    # ⚠️ WEAK:
    if sum(t == "📉 Bearish" for t in trends) >= 2:
        return "⚠️ WEAK"
    if all(s == "📉 Distributing" for s in sentiments):
        return "⚠️ WEAK"
    for t, s in zip(trends, sentiments):
        if t == "📉 Bearish" and s == "📉 Distributing":
            return "⚠️ WEAK"

    # 💪 STRONG:
    if all(t in ["📈 Bullish", "↔️ Neutral"] for t in trends) and \
       all(s in ["📈 Accumulating", "📉 Distributing"] for s in sentiments):
        
        has_bullish_and_accum = any(
            t == "📈 Bullish" and s == "📈 Accumulating"
            for t, s in zip(trends, sentiments)
        )
        distributing_count = sum(s == "📉 Distributing" for s in sentiments)

        if has_bullish_and_accum and distributing_count <= 1:
            return "💪 STRONG"

    # 😐 NEUTRAL
    return "😐 NEUTRAL"

# Download + classify trend/sentiment per interval
@st.cache_data(show_spinner=False)
def get_trend_sentiment(ticker, interval):
    yf_ticker = "BRK-B" if ticker.upper() == "BRK.B" else ticker.upper()

    try:
        df = yf.download(yf_ticker, interval=interval, period=period_map[interval], progress=False)
        if df.empty or "Close" not in df.columns or "Volume" not in df.columns:
            return "❓", "❓"

        close = df['Close']
        volume = df['Volume']

        if isinstance(close, pd.DataFrame):
            close = close.squeeze()
        if isinstance(volume, pd.DataFrame):
            volume = volume.squeeze()

        close = close.dropna()
        volume = volume.dropna()

        if len(close) < 60 or len(volume) < 60:
            return "❓", "❓"

        obv = ta.volume.OnBalanceVolumeIndicator(close=close, volume=volume).on_balance_volume()
        df["OBV"] = obv
        sma50 = close.rolling(50).mean()
        sma200 = close.rolling(200).mean()

        trend = "❓"
        sentiment = "❓"

        # Trend logic
        if not np.isnan(close.iloc[-1]) and not np.isnan(sma50.iloc[-1]) and not np.isnan(sma200.iloc[-1]):
            if close.iloc[-1] > sma50.iloc[-1] and sma50.iloc[-1] > sma200.iloc[-1]:
                trend = "📈 Bullish"
            elif close.iloc[-1] < sma50.iloc[-1] and sma50.iloc[-1] < sma200.iloc[-1]:
                trend = "📉 Bearish"
            else:
                trend = "↔️ Neutral"

        # Sentiment logic
        if "OBV" in df.columns and len(df["OBV"]) >= 6:
            obv_diff = df["OBV"].iloc[-1] - df["OBV"].iloc[-6]
            if obv_diff > 0:
                sentiment = "📈 Accumulating"
            elif obv_diff < 0:
                sentiment = "📉 Distributing"
            else:
                sentiment = "➖ Neutral"

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

# Display table
df = pd.DataFrame(results)
if not df.empty:
    st.dataframe(df)
    st.download_button("Download CSV", df.to_csv(index=False), file_name="multi_interval_signals.csv")
else:
    st.info("No data available for selected tickers.")
