import streamlit as st
import yfinance as yf
import pandas as pd
import ta

st.set_page_config(page_title="Swing Trade Signal Engine", layout="centered")

st.title("📊 Swing Trade Signal Engine")

# --- Sidebar Input ---
ticker = st.text_input("Enter Stock Ticker", value="TSLA").upper()
interval = st.selectbox("Interval", ["1d", "1h", "15m"])
period = st.selectbox("Period", ["3mo", "1mo", "7d"])

# --- Download Data ---
try:
    df = yf.download(ticker, interval=interval, period=period)
    if df.empty:
        st.error(f"❌ No data found for {ticker} at interval {interval}.")
    else:
        df.dropna(inplace=True)

        # Add Indicators
        df['rsi'] = ta.momentum.RSIIndicator(df['Close']).rsi()
        macd = ta.trend.MACD(df['Close'])
        df['macd'] = macd.macd()
        df['macd_signal'] = macd.macd_signal()
        df['sma50'] = ta.trend.SMAIndicator(df['Close'], window=50).sma_indicator()
        df['sma200'] = ta.trend.SMAIndicator(df['Close'], window=200).sma_indicator()

        latest = df.iloc[-1]

        # --- Trade Signal Conditions ---
        signals = {
            "RSI Oversold (RSI < 30)": latest["rsi"] < 30,
            "MACD Crossover (MACD > Signal)": latest["macd"] > latest["macd_signal"],
            "SMA50 > SMA200": latest["sma50"] > latest["sma200"],
            "Price > SMA50": latest["Close"] > latest["sma50"]
        }

        # --- Score ---
        score = sum(signals.values())
        if score == 4:
            rating = "🔥 High Conviction Buy"
        elif score == 3:
            rating = "⚠️ Watch List"
        else:
            rating = "❌ Skip for Now"

        # --- Display ---
        st.subheader("📈 Latest Trade Signals")
        for key, val in signals.items():
            st.write(f"- {key}: {'✅' if val else '❌'}")

        st.subheader("📊 Trade Readiness Score")
        st.markdown(f"**Score**: {score}/4 — **{rating}**")

        st.subheader("🔍 Recent Data Snapshot")
        st.dataframe(df.tail(5))

except Exception as e:
    st.error(f"❌ Error: {str(e)}")
