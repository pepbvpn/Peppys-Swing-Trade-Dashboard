import yfinance as yf
import pandas as pd
import numpy as np
import streamlit as st
import plotly.graph_objects as go
import ta

# Define tickers and interval options
tickers = ["TSLA", "AAPL", "NVDA", "AMZN", "MSFT"]
interval_options = {
    "15 Minutes": "15m",
    "30 Minutes": "30m",
    "1 Hour": "60m",
    "1 Day": "1d"
}

# Streamlit UI
st.title("📈 Real-Time Buy Signal Screener")
interval_label = st.selectbox("Select Time Interval", list(interval_options.keys()))
interval = interval_options[interval_label]

# Function to analyze one stock
def analyze_stock(ticker, interval):
    try:
        data = yf.download(ticker, period="5d", interval=interval, progress=False)
        if data.empty or len(data) < 50:
            return None
        
        data['RSI'] = ta.momentum.RSIIndicator(data['Close'], window=14).rsi()
        macd = ta.trend.MACD(data['Close'])
        data['MACD'] = macd.macd()
        data['Signal'] = macd.macd_signal()
        data['SMA50'] = data['Close'].rolling(window=50).mean()
        data['SMA200'] = data['Close'].rolling(window=200).mean()
        data['AvgVolume'] = data['Volume'].rolling(window=20).mean()
        
        latest = data.iloc[-1]
        rsi_signal = latest['RSI'] < 35
        macd_signal = latest['MACD'] > latest['Signal']
        sma_signal = latest['SMA50'] > latest['SMA200']
        volume_signal = latest['Volume'] > 2 * latest['AvgVolume']
        
        signal_count = sum([rsi_signal, macd_signal, sma_signal, volume_signal])
        if signal_count == 4:
            strength = "✅ Strong Buy"
        elif signal_count >= 2:
            strength = "⚠️ Watch"
        else:
            strength = "❌ None"
        
        return {
            "Ticker": ticker,
            "Price": round(latest['Close'], 2),
            "RSI": round(latest['RSI'], 1),
            "MACD > Signal": macd_signal,
            "SMA50 > SMA200": sma_signal,
            "Volume Spike": volume_signal,
            "Buy Signal": strength,
            "Data": data
        }
    except Exception:
        return None

# Analyze all stocks
results = []
for ticker in tickers:
    result = analyze_stock(ticker, interval)
    if result:
        results.append(result)

# Show results
df = pd.DataFrame(results)
if not df.empty:
    st.dataframe(df[["Ticker", "Price", "RSI", "MACD > Signal", "SMA50 > SMA200", "Volume Spike", "Buy Signal"]])

    for res in results:
        with st.expander(f"📊 {res['Ticker']} Chart"):
            data = res["Data"]
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=data.index, y=data['Close'], mode='lines', name='Close'))
            fig.add_trace(go.Scatter(x=data.index, y=data['SMA50'], mode='lines', name='SMA50'))
            fig.add_trace(go.Scatter(x=data.index, y=data['SMA200'], mode='lines', name='SMA200'))
            fig.update_layout(title=f"{res['Ticker']} Price & SMA", xaxis_title="Time", yaxis_title="Price")
            st.plotly_chart(fig)
else:
    st.warning("No signals or data available for this interval.")
