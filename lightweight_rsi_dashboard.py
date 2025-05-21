
import streamlit as st
import yfinance as yf
import pandas as pd
import ta
import plotly.graph_objects as go

# Streamlit setup
st.set_page_config(page_title="Lightweight RSI Dashboard", layout="wide")
st.title("📉 Quick RSI Check for Day Trading")

# Sidebar
ticker = st.sidebar.text_input("Enter Ticker Symbol", value="AAPL")
interval = st.sidebar.selectbox("Interval", ["5m", "15m", "1h"])
period = st.sidebar.selectbox("Period", ["1d", "5d"])

@st.cache_data
def get_data(ticker, interval, period):
    df = yf.download(ticker, interval=interval, period=period)
    df.dropna(inplace=True)
    return df

df = get_data(ticker, interval, period)

if df.empty:
    st.error("No data returned. Try a different interval or period.")
else:
    df["RSI"] = ta.momentum.RSIIndicator(close=df["Close"]).rsi()
    latest = df.iloc[-1]
    rsi_value = latest["RSI"]

    st.subheader(f"📊 RSI for {ticker}")
    st.markdown(f"**RSI:** {rsi_value:.2f}")

    fig = go.Figure()
    fig.add_trace(go.Candlestick(x=df.index,
                                 open=df["Open"], high=df["High"],
                                 low=df["Low"], close=df["Close"],
                                 name="Price"))
    fig.update_layout(title=f"{ticker} Price Chart", xaxis_title="Time", yaxis_title="Price", height=600)
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("📋 Data Preview")
    st.dataframe(df.tail(10))
