
import streamlit as st
import pandas as pd
import yfinance as yf
import ta

st.set_page_config(page_title="Swing Trade Dashboard", layout="wide")
st.title("📈 Advanced Swing Trade Dashboard")

# User input: tickers and interval
tickers_input = st.text_input("Enter tickers (comma-separated)", value="NVDA, AAPL, MSFT, TSLA, SPY")
interval = st.selectbox("Select interval", options=["15m", "1h", "1d"])
tickers = [ticker.strip().upper() for ticker in tickers_input.split(",")]

# yfinance period based on interval
period_map = {
    "15m": "5d",
    "1h": "30d",
    "1d": "6mo"
}
period = period_map[interval]

# Constants
profit_target_pct = 0.10
stop_loss_pct = 0.05
entry_buffer_pct = 0.005

results = []

# Scan each ticker
for ticker in tickers:
    try:
        df = yf.download(ticker, period=period, interval=interval, progress=False)
        if df.empty or len(df) < 50:
            st.warning(f"{ticker}: Not enough data to process.")
            continue

        df.dropna(inplace=True)
        close_series = df['Close'].squeeze()

        # Indicators with safe alignment
        rsi = ta.momentum.RSIIndicator(close=close_series).rsi()
        macd = ta.trend.MACD(close=close_series)
        df['RSI'] = rsi
        df['MACD'] = macd.macd()
        df['MACD_SIGNAL'] = macd.macd_signal()
        df['20EMA'] = df['Close'].ewm(span=20).mean()
        df['50EMA'] = df['Close'].ewm(span=50).mean()
        df['Volume_Avg'] = df['Volume'].rolling(window=10).mean()
        df['Volume_Spike'] = df['Volume'] > df['Volume_Avg']

        df = df.dropna()
        latest = df.iloc[-1]

        entry_signal = (
            latest['RSI'] > 30 and latest['RSI'] < 40 and
            latest['MACD'] > latest['MACD_SIGNAL'] and
            latest['Close'] > latest['20EMA'] and
            latest['Close'] < latest['50EMA'] and
            latest['Volume_Spike']
        )

        entry_watch = latest['High'] * (1 + entry_buffer_pct)
        target_price = entry_watch * (1 + profit_target_pct)
        stop_price = entry_watch * (1 - stop_loss_pct)

        results.append({
            "Ticker": ticker,
            "Latest Close": round(latest['Close'], 2),
            f"Entry Watch ({interval})": round(entry_watch, 2),
            "Target (+10%)": round(target_price, 2),
            "Stop-Loss (-5%)": round(stop_price, 2),
            f"RSI ({interval})": round(latest['RSI'], 2),
            "MACD > Signal": latest['MACD'] > latest['MACD_SIGNAL'],
            "Volume Spike": bool(latest['Volume_Spike']),
            "Signal": "✅ BUY" if entry_signal else "❌"
        })

    except Exception as e:
        st.warning(f"Could not load {ticker}: {e}")

# Display results
df = pd.DataFrame(results)
st.dataframe(df)

# Exportable CSV
if not df.empty:
    st.download_button("📥 Download Signal Data as CSV", df.to_csv(index=False), file_name="swing_signals.csv")
