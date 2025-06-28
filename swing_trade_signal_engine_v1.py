import streamlit as st
import yfinance as yf
import pandas as pd
import ta

st.set_page_config(page_title="📈 Swing Trade Scout", layout="wide")
st.title("📊 Swing Trade Signal Engine")

# Inputs
ticker = st.text_input("Enter Stock Ticker", value="AAPL")
interval = st.selectbox("Interval", ["1d", "1h", "15m"])
period = st.selectbox("Period", ["6mo", "3mo", "1mo", "5d"])

# Helper to calculate signals
def analyze_signals(df):
    if df.empty or 'Close' not in df.columns:
        return None

    df = df.dropna(subset=['Close']).copy()

    # Indicators
    df['rsi'] = ta.momentum.RSIIndicator(df['Close']).rsi()
    macd = ta.trend.MACD(df['Close'])
    df['macd'] = macd.macd()
    df['macd_signal'] = macd.macd_signal()
    df['sma50'] = ta.trend.SMAIndicator(df['Close'], window=50).sma_indicator()
    df['sma200'] = ta.trend.SMAIndicator(df['Close'], window=200).sma_indicator()

    # Most recent values
    latest = df.iloc[-1]
    signals = {
        "RSI Oversold (RSI < 30)": latest["rsi"] < 30,
        "MACD Bullish Crossover": latest["macd"] > latest["macd_signal"],
        "Price > SMA50": latest["Close"] > latest["sma50"],
        "SMA50 > SMA200": latest["sma50"] > latest["sma200"]
    }

    score = sum(signals.values())
    if score == 4:
        rating = "🔥 High Conviction Buy"
    elif score == 3:
        rating = "⚠️ Watch List"
    else:
        rating = "❌ Skip for Now"

    return signals, score, rating, df.tail()

# Scan Button
if st.button("Run Scan"):
    with st.spinner("Analyzing..."):
        df = yf.download(ticker, interval=interval, period=period)
        result = analyze_signals(df)

    if result:
        signals, score, rating, tail = result
        st.subheader(f"📌 Signal Summary for **{ticker.upper()}**")
        st.write(f"**Trade Readiness Score: {score}/4** → {rating}")
        st.write(signals)
        st.subheader("📉 Recent Price & Indicators")
        st.dataframe(tail)
        st.line_chart(df['Close'])
    else:
        st.error("Failed to analyze data. Try a different ticker or period.")
