import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
from streamlit_autorefresh import st_autorefresh

st.set_page_config(page_title="Day Trade Signal App", layout="wide")
st.title("📊 Peppy's Day Trading Signal Scanner")

# Auto refresh every 5 minutes
st_autorefresh(interval=5 * 60 * 1000, key="auto_refresh")

# Settings
tickers = ["TSLA", "AAPL", "AMD", "NVDA", "SPY", "QQQ", "MSFT", "META"]
interval = "15m"
period = "2d"

def compute_indicators(df):
    df['RSI'] = compute_rsi(df['Close'])
    df['EMA_12'] = df['Close'].ewm(span=12, adjust=False).mean()
    df['EMA_26'] = df['Close'].ewm(span=26, adjust=False).mean()
    df['MACD'] = df['EMA_12'] - df['EMA_26']
    df['Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
    df['TP'] = (df['High'] + df['Low'] + df['Close']) / 3
    df['VP'] = df['TP'] * df['Volume']
    df['Cumulative_VP'] = df['VP'].cumsum()
    df['Cumulative_Volume'] = df['Volume'].cumsum()
    df['VWAP'] = df['Cumulative_VP'] / df['Cumulative_Volume']
    df['SMA_50'] = df['Close'].rolling(window=50).mean()
    df['SMA_200'] = df['Close'].rolling(window=200).mean()
    return df

def compute_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

results = []

for ticker in tickers:
    df = yf.download(ticker, interval=interval, period=period, progress=False)

    if df.empty or len(df) < 50:
        continue

    df = compute_indicators(df)
    latest = df.iloc[-1]

    # Convert scalar values
    rsi = latest['RSI'].item()
    macd = latest['MACD'].item()
    signal = latest['Signal'].item()
    vwap = latest['VWAP'].item()
    close = latest['Close'].item()
    sma_50 = latest['SMA_50'].item()
    sma_200 = latest['SMA_200'].item()

    # Signals
    rsi_signal = "✅" if rsi < 35 else "❌"
    macd_signal = "✅" if macd > signal else "❌"
    vwap_signal = "✅" if close > vwap else "❌"
    sma_trend = "✅" if sma_50 > sma_200 and close > sma_50 else "❌"

    score = [rsi_signal, macd_signal, vwap_signal, sma_trend].count("✅")

    if score == 4:
        verdict = "🔥 Strong Buy"
    elif score == 3:
        verdict = "⚠️ Watchlist"
    else:
        verdict = "❌ Skip"

    results.append({
        "Ticker": ticker,
        "Close": close,
        "RSI": round(rsi, 2),
        "MACD > Signal": macd_signal,
        "Above VWAP": vwap_signal,
        "Trend (SMA50>200)": sma_trend,
        "Score": f"{score}/4",
        "Verdict": verdict
    })

# Display results
if results:
    st.dataframe(pd.DataFrame(results))
else:
    st.warning("No valid data to display.")
