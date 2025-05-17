
import streamlit as st
import pandas as pd
import yfinance as yf
import ta
import numpy as np

st.set_page_config(page_title="Swing Trade Signal Scanner", layout="wide")
st.title("📈 Swing Trade Signal Dashboard")

# User inputs
tickers_input = st.text_input("Enter ticker symbols (comma-separated)", value="NVDA, AAPL, MSFT, TSLA, SPY")
interval = st.selectbox("Select interval", options=["1d", "1h", "15m"])

# Set period based on interval
period_map = {"1d": "6mo", "1h": "30d", "15m": "5d"}
period = period_map[interval]

tickers = [ticker.strip().upper() for ticker in tickers_input.split(",")]

# Parameters
profit_target_pct = 0.10
stop_loss_pct = 0.05
entry_buffer_pct = 0.005

def find_support_resistance(prices, window=20):
    supports = []
    resistances = []

    for i in range(window, len(prices) - window):
        is_support = all(prices[i] < prices[i - j] and prices[i] < prices[i + j] for j in range(1, window))
        is_resistance = all(prices[i] > prices[i - j] and prices[i] > prices[i + j] for j in range(1, window))
        if is_support:
            supports.append(prices[i])
        if is_resistance:
            resistances.append(prices[i])

    supports = sorted(set(supports))
    resistances = sorted(set(resistances))
    return supports[-1] if supports else np.nan, resistances[0] if resistances else np.nan

results = []

for ticker in tickers:
    df = yf.download(ticker, period=period, interval=interval, progress=False)

    if df.empty:
        continue

    close_series = df['Close']
    if isinstance(close_series, pd.DataFrame):
        close_series = close_series.squeeze()

    df['RSI'] = ta.momentum.RSIIndicator(close=close_series).rsi()
    macd = ta.trend.MACD(close=close_series)
    df['MACD'] = macd.macd()
    df['MACD_SIGNAL'] = macd.macd_signal()
    df['20EMA'] = close_series.ewm(span=20).mean()
    df['50EMA'] = close_series.ewm(span=50).mean()
    df['SMA50'] = close_series.rolling(window=50).mean()
    df['SMA200'] = close_series.rolling(window=200).mean()

    volume = df['Volume']
    volume_avg = volume.rolling(window=10).mean()
    volume, volume_avg = volume.align(volume_avg, join='inner')
    df = df.loc[volume.index]

    df['Volume'] = volume
    df['Volume_Avg'] = volume_avg
    df['Volume_Spike'] = volume > volume_avg

    df.dropna(inplace=True)

    if df.empty:
        continue

    latest = df.iloc[-1]
    support, resistance = find_support_resistance(df['Close'])

    entry_signal = (
        latest['RSI'].item() > 30 and latest['RSI'].item() < 40 and
        latest['MACD'].item() > latest['MACD_SIGNAL'].item() and
        latest['Close'].item() > latest['20EMA'].item() and
        latest['Close'].item() < latest['50EMA'].item() and
        bool(latest['Volume_Spike'].item())
    )

    entry_watch = latest['High'] * (1 + entry_buffer_pct)
    target_price = entry_watch * (1 + profit_target_pct)
    stop_price = entry_watch * (1 - stop_loss_pct)

    results.append({
        "Ticker": ticker,
        "Latest Close": round(latest['Close'], 2),
        "Entry Watch Price": round(entry_watch, 2),
        "Sell Target (10%)": round(target_price, 2),
        "Stop-Loss (5%)": round(stop_price, 2),
        "RSI": round(latest['RSI'].item(), 2),
        "MACD > Signal": latest['MACD'].item() > latest['MACD_SIGNAL'].item(),
        "Volume": int(latest['Volume']),
        "Volume Spike": bool(latest['Volume_Spike'].item()),
        "SMA50": round(latest['SMA50'], 2),
        "SMA200": round(latest['SMA200'], 2),
        "Support": round(support, 2) if not np.isnan(support) else "N/A",
        "Resistance": round(resistance, 2) if not np.isnan(resistance) else "N/A",
        "Signal": "✅ BUY" if entry_signal else "❌ NO ENTRY"
    })

df = pd.DataFrame(results)

if not df.empty:
    st.dataframe(df)
    st.download_button("Download CSV", df.to_csv(index=False), file_name="swing_signals.csv")
else:
    st.info("No signals available for the selected tickers and interval.")
