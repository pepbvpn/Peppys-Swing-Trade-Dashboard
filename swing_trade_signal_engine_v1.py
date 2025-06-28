import streamlit as st
import pandas as pd
import yfinance as yf
import ta

st.set_page_config(page_title="Swing Trade Signal Engine", layout="wide")
st.title("📊 Swing Trade Signal Engine")
st.caption("Uses RSI, MACD, SMA, Volume, VWAP, and OBV to generate a Trade Readiness Score")

# ---- SETTINGS ----
TICKERS = st.multiselect(
    "Select tickers to scan",
    options=['AAPL', 'MSFT', 'NVDA', 'TSLA', 'AMZN'],
    default=['AAPL', 'MSFT', 'NVDA']
)

INTERVAL = st.selectbox("Interval", ["1d", "1h", "15m"])

# ---- FUNCTION TO DOWNLOAD DATA ----
def fetch_data(ticker, interval):
    if interval == "1d":
        return yf.download(ticker, period="6mo", interval=interval)
    elif interval == "1h":
        return yf.download(ticker, period="1mo", interval=interval)
    else:  # 15m
        return yf.download(ticker, period="5d", interval=interval)

# ---- ANALYSIS FUNCTION ----
def analyze(df):
    if df.empty or 'Close' not in df.columns:
        return None

    df = df.dropna(subset=['Close']).copy()
    if len(df) < 50:
        return None

    try:
        df['rsi'] = ta.momentum.RSIIndicator(df['Close']).rsi()
        macd = ta.trend.MACD(df['Close'])
        df['macd'] = macd.macd()
        df['signal'] = macd.macd_signal()
        df['macd_cross'] = df['macd'] > df['signal']
        df['sma_50'] = df['Close'].rolling(window=50).mean()
        df['sma_200'] = df['Close'].rolling(window=200).mean()
        df['golden_cross'] = df['sma_50'] > df['sma_200']
        df['volume_spike'] = df['Volume'] > df['Volume'].rolling(20).mean() * 1.5
        df['vwap'] = (df['High'] + df['Low'] + df['Close']) / 3
        df['above_vwap'] = df['Close'] > df['vwap']
        df['obv'] = ta.volume.OnBalanceVolumeIndicator(df['Close'], df['Volume']).on_balance_volume()
        df['obv_trend'] = df['obv'].diff().rolling(5).mean() > 0
    except Exception:
        return None

    latest = df.iloc[-1]
    score = sum([
        latest['rsi'] < 35,
        latest['macd_cross'],
        latest['golden_cross'],
        latest['volume_spike'],
        latest['above_vwap'],
        latest['obv_trend']
    ])

    if score == 6:
        label = "🔥 High Conviction Buy"
    elif score >= 4:
        label = "⚠️ Watch List"
    else:
        label = "❌ Skip for Now"

    return {
        "Price": round(latest['Close'], 2),
        "RSI": round(latest['rsi'], 2),
        "MACD > Signal": bool(latest['macd_cross']),
        "Golden Cross": bool(latest['golden_cross']),
        "Volume Spike": bool(latest['volume_spike']),
        "Above VWAP": bool(latest['above_vwap']),
        "OBV Uptrend": bool(latest['obv_trend']),
        "Score": score,
        "Signal": label
    }

# ---- RUN ANALYSIS ----
results = []

for ticker in TICKERS:
    try:
        df = fetch_data(ticker, INTERVAL)
        df.name = ticker
        result = analyze(df)
        if result:
            result["Ticker"] = ticker
            results.append(result)
        else:
            st.warning(f"⚠️ Skipping {ticker} — not enough valid data or no signal.")
    except Exception as e:
        st.error(f"❌ Error loading {ticker}: {e}")

# ---- DISPLAY RESULTS ----
if results:
    df_results = pd.DataFrame(results).sort_values(by="Score", ascending=False)
    st.dataframe(df_results.set_index("Ticker"))
else:
    st.info("No valid signals found.")
