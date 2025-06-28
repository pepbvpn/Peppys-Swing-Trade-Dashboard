import streamlit as st
import yfinance as yf
import pandas as pd
import ta

st.set_page_config(page_title="📊 Swing Trade Signal Engine", layout="centered")

st.title("📊 Swing Trade Signal Engine")

# --- User Input ---
ticker = st.text_input("Enter Stock Ticker", value="TSLA").upper()
interval = st.selectbox("Interval", ["1d", "1h", "15m"])
period = st.selectbox("Period", ["1mo", "3mo", "7d"])

if ticker:
    try:
        df = yf.download(ticker, interval=interval, period=period)
        if df.empty:
            st.error("No data found. Please check the ticker symbol or interval.")
        else:
            df.dropna(inplace=True)

            # Calculate indicators
            rsi = ta.momentum.RSIIndicator(close=df['Close']).rsi()
            macd = ta.trend.MACD(close=df['Close'])
            macd_line = macd.macd()
            signal_line = macd.macd_signal()
            sma50 = ta.trend.SMAIndicator(close=df['Close'], window=50).sma_indicator()
            sma200 = ta.trend.SMAIndicator(close=df['Close'], window=200).sma_indicator()

            df['RSI'] = rsi
            df['MACD'] = macd_line
            df['MACD_Signal'] = signal_line
            df['SMA50'] = sma50
            df['SMA200'] = sma200

            # Latest values
            latest = df.iloc[-1]

            # Signal checks
            conditions = {
                "RSI < 30 (Oversold)": latest['RSI'] < 30,
                "MACD > Signal": latest['MACD'] > latest['MACD_Signal'],
                "SMA50 > SMA200": latest['SMA50'] > latest['SMA200'],
                "Price > SMA50": latest['Close'] > latest['SMA50']
            }

            score = sum(conditions.values())
            if score == 4:
                status = "🔥 High Conviction Buy"
            elif score == 3:
                status = "⚠️ Watch List"
            else:
                status = "❌ Skip for Now"

            # --- Display ---
            st.subheader("📈 Trade Signals")
            for label, passed in conditions.items():
                st.write(f"- {label}: {'✅' if passed else '❌'}")

            st.subheader("💡 Trade Readiness Score")
            st.write(f"**{score}/4** — {status}")

            st.subheader("📊 Recent Data")
            st.dataframe(df.tail())

    except Exception as e:
        st.error(f"❌ Error: {str(e)}")
