import streamlit as st
import yfinance as yf
import pandas as pd
import ta

st.set_page_config(page_title="📊 Swing Trade Signal Engine")

st.title("📊 Swing Trade Signal Engine")

ticker = st.text_input("Enter Stock Ticker", value="TSLA")
interval = st.selectbox("Interval", ["1d", "1h", "15m"])
period = st.selectbox("Period", ["1mo", "3mo", "6mo", "1y"])

def fetch_data(ticker, interval, period):
    try:
        df = yf.download(ticker, interval=interval, period=period)
        return df
    except Exception as e:
        st.error(f"Failed to fetch data: {e}")
        return pd.DataFrame()

def analyze_signals(df):
    if df.empty:
        st.error("❌ No data returned. Please check the ticker, interval, or period.")
        return None

    if 'Close' not in df.columns:
        st.error("❌ 'Close' column not found in data. Try another interval or period.")
        st.write("Available columns:", list(df.columns))
        return None

    df = df.dropna(subset=['Close']).copy()

    # Indicators
    df['rsi'] = ta.momentum.RSIIndicator(df['Close']).rsi()
    macd = ta.trend.MACD(df['Close'])
    df['macd'] = macd.macd()
    df['macd_signal'] = macd.macd_signal()
    df['sma50'] = ta.trend.SMAIndicator(df['Close'], window=50).sma_indicator()
    df['sma200'] = ta.trend.SMAIndicator(df['Close'], window=200).sma_indicator()

    latest = df.iloc[-1]
    signals = {
        "RSI < 30 (Oversold)": latest['rsi'] < 30,
        "MACD > Signal": latest['macd'] > latest['macd_signal'],
        "Price > SMA50": latest['Close'] > latest['sma50'],
        "SMA50 > SMA200": latest['sma50'] > latest['sma200']
    }

    score = sum(signals.values())
    if score == 4:
        rating = "🔥 High Conviction Buy"
    elif score == 3:
        rating = "⚠️ Watch List"
    else:
        rating = "❌ Skip for Now"

    return signals, score, rating, df.tail()

if st.button("Analyze"):
    df = fetch_data(ticker, interval, period)
    result = analyze_signals(df)
    if result:
        signals, score, rating, preview = result
        st.subheader("🔍 Signal Breakdown")
        for k, v in signals.items():
            st.write(f"{k}: {'✅' if v else '❌'}")
        st.markdown(f"### 🧠 Trade Readiness Score: {score}/4 — **{rating}**")
        st.subheader("📈 Recent Data Preview")
        st.dataframe(preview)
