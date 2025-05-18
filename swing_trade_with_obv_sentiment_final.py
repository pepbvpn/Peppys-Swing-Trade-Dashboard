
import streamlit as st
import pandas as pd
import yfinance as yf
import ta
import numpy as np

st.set_page_config(page_title="Swing Trade Scanner", layout="wide")
st.title("📈 Swing Trade Signal Dashboard")

tickers_input = st.text_input("Enter ticker symbols (comma-separated)", value="NVDA, AAPL, MSFT, TSLA, SPY")
interval = st.selectbox("Select interval", options=["1d", "1h", "15m"])
period_map = {"1d": "1y", "1h": "60d", "15m": "10d"}
period = period_map[interval]

tickers = [ticker.strip().upper() for ticker in tickers_input.split(",")]

profit_target_pct = 0.10
stop_loss_pct = 0.05
entry_buffer_pct = 0.005

def find_support_resistance_fallback(prices, window=10):
    supports, resistances = [], []
    prices = np.array(prices).flatten()

    for i in range(window, len(prices) - window):
        is_support = all(prices[i] < prices[i - j] and prices[i] < prices[i + j] for j in range(1, window))
        is_resistance = all(prices[i] > prices[i - j] and prices[i] > prices[i + j] for j in range(1, window))
        if is_support:
            supports.append(float(prices[i]))
        if is_resistance:
            resistances.append(float(prices[i]))

    supports = sorted(set(supports))
    resistances = sorted(set(resistances))

    if supports and resistances:
        return supports[-1], resistances[0]
    elif prices.size > 0:
        return float(np.nanmin(prices)), float(np.nanmax(prices))
    else:
        return np.nan, np.nan

results = []

for ticker in tickers:
    df = yf.download(ticker, period=period, interval=interval, progress=False)

    if df.empty or len(df) < 100:
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

    # Calculate OBV
    if "Volume" in df.columns and "Close" in df.columns:
        volume_series = df["Volume"]
        if isinstance(close_series, pd.DataFrame):
            close_series = close_series.squeeze()
        if isinstance(volume_series, pd.DataFrame):
            volume_series = volume_series.squeeze()

        common_index = close_series.index.intersection(volume_series.index)
        close_series = close_series.loc[common_index]
        volume_series = volume_series.loc[common_index]
        df = df.loc[common_index]

        obv = ta.volume.OnBalanceVolumeIndicator(close=close_series, volume=volume_series).on_balance_volume()
        df["OBV"] = obv

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
    support, resistance = find_support_resistance_fallback(df['Close'].values)

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

    price = latest['Close'].item()
    sma50 = latest['SMA50'].item()
    sma200 = latest['SMA200'].item()

    if (
        price > sma200 and
        sma50 > sma200 and
        "OBV" in df.columns and
        (latest["OBV"] - df["OBV"].rolling(window=20).mean().iloc[-1]) > 0
    ):
        longterm_signal = "✅ BUY & HOLD"
    elif (
        price > sma50 and
        sma50 > sma200 * 0.9 and
        "OBV" in df.columns and
        (latest["OBV"] - df["OBV"].rolling(window=10).mean().iloc[-1]) > 0
    ):
        longterm_signal = "🟡 Early Entry"
    else:
        longterm_signal = "❌ WAIT"

    # Determine institutional sentiment based on OBV trend
    if "OBV" in df.columns and len(df["OBV"]) >= 6:
        obv_diff = df["OBV"].iloc[-1] - df["OBV"].iloc[-6]
        if obv_diff > 0:
            sentiment = "📈 Accumulating"
        elif obv_diff < 0:
            sentiment = "📉 Distributing"
        else:
            sentiment = "➖ Neutral"
    else:
        sentiment = "❓ Unknown"

    if not np.isnan(price) and not np.isnan(sma50) and not np.isnan(sma200):
        if price > sma50 and sma50 > sma200:
            trend = "📈 Bullish"
        elif price < sma50 and sma50 < sma200:
            trend = "📉 Bearish"
        else:
            trend = "↔️ Neutral"
    else:
        trend = "❓ Not enough data"

    results.append({
        "Ticker": ticker,
        "Latest Close": round(price, 2),
        "Entry Watch Price": round(entry_watch, 2),
        "Sell Target (10%)": round(target_price, 2),
        "Stop-Loss (5%)": round(stop_price, 2),
        "RSI": round(latest['RSI'].item(), 2),
        "MACD > Signal": latest['MACD'].item() > latest['MACD_SIGNAL'].item(),
        "Volume": int(latest['Volume']),
        "Volume Spike": bool(latest['Volume_Spike'].item()),
        "SMA50": round(sma50, 2),
        "SMA200": round(sma200, 2),
        "Support": round(support, 2) if not np.isnan(support) else "N/A",
        "Resistance": round(resistance, 2) if not np.isnan(resistance) else "N/A",
        "Trend": trend,
        "Institutional Sentiment": sentiment,
        "Long-Term Signal": longterm_signal,
        "Signal": "✅ BUY" if entry_signal else "❌ NO ENTRY"
    })

df = pd.DataFrame(results)

if not df.empty:
    st.dataframe(df)
    st.download_button("Download CSV", df.to_csv(index=False), file_name="swing_signals.csv")
else:
    st.info("No signals available for the selected tickers and interval.")
