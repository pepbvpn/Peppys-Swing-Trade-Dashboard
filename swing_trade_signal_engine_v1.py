import streamlit as st
import yfinance as yf
import pandas as pd

st.title("🔍 Stock Data Debugger")

ticker = st.text_input("Enter stock ticker", value="AAPL")
interval = st.selectbox("Select interval", options=["1d", "1h", "15m"])
period = st.selectbox("Select period", options=["6mo", "1mo", "5d"])

if st.button("Fetch Data"):
    with st.spinner(f"Downloading data for {ticker}..."):
        df = yf.download(ticker, interval=interval, period=period)
    
    if df.empty:
        st.error("❌ No data returned. Check ticker, interval, or network.")
    elif 'Close' not in df.columns:
        st.error(f"❌ 'Close' column missing. Columns found: {list(df.columns)}")
    else:
        st.success(f"✅ Data fetched. {len(df)} rows")
        st.dataframe(df.tail())
        st.line_chart(df['Close'])
