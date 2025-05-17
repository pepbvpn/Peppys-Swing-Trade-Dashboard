
import streamlit as st
import pandas as pd
import yfinance as yf
import ta

st.set_page_config(page_title="Colab Swing Scanner", layout="wide")
st.title("📈 Swing Trade Signal Dashboard")

# Parameters
tickers = ["NVDA", "AAPL", "MSFT", "TSLA", "SPY"]
profit_target_pct = 0.10
stop_loss_pct = 0.05
entry_buffer_pct = 0.005

results = []

for ticker in tickers:
    df = yf.download(ticker, period="6mo", interval="1d", progress=False)

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
        "Volume Spike": bool(latest['Volume_Spike'].item()),
        "Signal": "✅ BUY" if entry_signal else "❌ NO ENTRY"
    })

df = pd.DataFrame(results)

if not df.empty:
    st.dataframe(df)
    st.download_button("Download CSV", df.to_csv(index=False), file_name="swing_signals.csv")
else:
    st.info("No signals available right now.")
