
import streamlit as st
import pandas as pd
import yfinance as yf
import ta
import matplotlib.pyplot as plt
import io

st.set_page_config(page_title="Swing Trade Dashboard with Charts", layout="wide")
st.title("📈 Swing Trade Signal Dashboard with Mini Charts")

tickers_input = st.text_input("Enter ticker symbols (comma-separated)", value="NVDA, AAPL, MSFT, TSLA, SPY")
interval = st.selectbox("Select interval", options=["1d", "1h", "15m"])
period_map = {"1d": "1y", "1h": "60d", "15m": "10d"}
period = period_map[interval]
tickers = [ticker.strip().upper() for ticker in tickers_input.split(",")]

def generate_mini_chart(ticker, interval="1d", period="6mo"):
    df = yf.download(ticker, period=period, interval=interval, progress=False)
    if df.empty or len(df) < 50:
        return None

    df['SMA50'] = df['Close'].rolling(window=50).mean()
    df['SMA200'] = df['Close'].rolling(window=200).mean()

    close_series = df['Close'].squeeze()
    volume_series = df['Volume'].squeeze()

    obv = ta.volume.OnBalanceVolumeIndicator(close=close_series, volume=volume_series).on_balance_volume()
    df['OBV'] = obv

    fig, ax = plt.subplots(2, 1, figsize=(6, 4), gridspec_kw={'height_ratios': [3, 1]})
    ax[0].plot(df.index, df['Close'], label="Price", linewidth=1.5)
    ax[0].plot(df.index, df['SMA50'], label="SMA50", linestyle="--")
    ax[0].plot(df.index, df['SMA200'], label="SMA200", linestyle="--")
    ax[0].legend()
    ax[0].grid(True)

    ax[1].plot(df.index, df['OBV'], label="OBV", color="purple", linewidth=1.2)
    ax[1].set_title("OBV")
    ax[1].grid(True)

    plt.tight_layout()
    buf = io.BytesIO()
    plt.savefig(buf, format="png")
    buf.seek(0)
    plt.close(fig)
    return buf

# Generate signal data and display chart
for ticker in tickers:
    st.subheader(f"{ticker} Signal + Chart")

    df = yf.download(ticker, period=period, interval=interval, progress=False)
    if df.empty or len(df) < 50:
        st.warning(f"Not enough data for {ticker}")
        continue

    df['RSI'] = ta.momentum.RSIIndicator(close=df['Close'].squeeze()).rsi()
    df['SMA50'] = df['Close'].rolling(window=50).mean()
    df['SMA200'] = df['Close'].rolling(window=200).mean()

    latest = df.iloc[-1]
    sma50 = latest['SMA50']
    sma200 = latest['SMA200']
    rsi = latest['RSI']

    if sma50 > sma200 and latest['Close'] > sma50:
        signal = "✅ BUY"
    else:
        signal = "❌ WAIT"

    info = {
        "Ticker": ticker,
        "Close": round(latest['Close'], 2),
        "RSI": round(rsi, 2),
        "SMA50": round(sma50, 2),
        "SMA200": round(sma200, 2),
        "Signal": signal
    }

    st.dataframe(pd.DataFrame([info]))

    img_buf = generate_mini_chart(ticker, interval=interval, period=period)
    if img_buf:
        st.image(img_buf, caption=f"{ticker} Chart", use_column_width=True)
