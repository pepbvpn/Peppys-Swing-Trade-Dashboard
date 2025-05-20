
import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go

# Streamlit setup
st.set_page_config(page_title="Day Trading Signal Dashboard", layout="wide")
st.title("📈 Day Trading Signal Dashboard")

# Sidebar
ticker = st.sidebar.text_input("Enter Ticker Symbol", value="AAPL")
interval = st.sidebar.selectbox("Select Interval", ["1m", "5m", "15m", "30m", "1h", "1d"])
period = st.sidebar.selectbox("Select Data Period", ["1d", "5d", "7d", "1mo"])

# Load data
@st.cache_data
def get_data(ticker, interval, period):
    df = yf.download(ticker, interval=interval, period=period)
    df.dropna(inplace=True)
    return df

df = get_data(ticker, interval, period)

# Calculate indicators
df["EMA9"] = ta.ema(df["Close"], length=9)
df["EMA21"] = ta.ema(df["Close"], length=21)
df["SMA50"] = ta.sma(df["Close"], length=50)
df["SMA200"] = ta.sma(df["Close"], length=200)
df["RSI"] = ta.rsi(df["Close"], length=14)
macd = ta.macd(df["Close"])
df = pd.concat([df, macd], axis=1)
df["OBV"] = ta.obv(df["Close"], df["Volume"])
df["ATR"] = ta.atr(df["High"], df["Low"], df["Close"], length=14)
bb = ta.bbands(df["Close"])
df = pd.concat([df, bb], axis=1)

# Signal logic
latest = df.iloc[-1]
signal = ""
if latest["RSI"] < 30 and latest["MACD_12_26_9"] > latest["MACDs_12_26_9"]:
    signal = "🔼 BUY SIGNAL"
elif latest["RSI"] > 70 and latest["MACD_12_26_9"] < latest["MACDs_12_26_9"]:
    signal = "🔽 SELL SIGNAL"
else:
    signal = "⏸️ WAIT / NO STRONG SIGNAL"

# Signal summary
st.subheader(f"📌 Signal for {ticker}")
st.markdown(f"**Signal:** {signal}")
st.markdown(f"**RSI:** {latest['RSI']:.2f}")
st.markdown(f"**MACD:** {latest['MACD_12_26_9']:.2f}")
st.markdown(f"**OBV:** {latest['OBV']:.2f}")
st.markdown(f"**ATR:** {latest['ATR_14']:.2f}")

# Chart
fig = go.Figure()
fig.add_trace(go.Candlestick(x=df.index,
                             open=df["Open"],
                             high=df["High"],
                             low=df["Low"],
                             close=df["Close"], name="Candles"))
fig.add_trace(go.Scatter(x=df.index, y=df["EMA9"], mode="lines", name="EMA9"))
fig.add_trace(go.Scatter(x=df.index, y=df["EMA21"], mode="lines", name="EMA21"))
fig.add_trace(go.Scatter(x=df.index, y=df["SMA50"], mode="lines", name="SMA50"))
fig.add_trace(go.Scatter(x=df.index, y=df["SMA200"], mode="lines", name="SMA200"))
fig.update_layout(title=f"{ticker} Price Chart", xaxis_title="Date", yaxis_title="Price", height=600)
st.plotly_chart(fig, use_container_width=True)

# Latest Data Table
st.subheader("📊 Latest Data")
st.dataframe(df.tail(10))
