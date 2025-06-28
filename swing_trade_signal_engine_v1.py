import streamlit as st
import yfinance as yf
import pandas as pd
import ta

st.set_page_config(page_title="📈 Tomorrow's Best Swing Trade", layout="centered")
st.title("📈 Best Stock to Buy Tomorrow")
st.caption("Scans top tickers and gives one swing trade pick daily based on technicals")

# Define your tickers (can be full S&P 500 later)
TICKERS = ['AAPL', 'MSFT', 'NVDA', 'TSLA', 'AMZN', 'META', 'GOOGL', 'AMD', 'NFLX', 'BA']
st.write(f"Scanning {len(TICKERS)} tickers on 1D interval...")

def fetch_data(ticker):
    return yf.download(ticker, period="6mo", interval="1d")

def analyze(df):
    if df.empty or 'Close' not in df.columns or len(df) < 50:
        return None
    df = df.dropna(subset=['Close']).copy()

    # Indicators
    df['rsi'] = ta.momentum.RSIIndicator(df['Close']).rsi()
    macd = ta.trend.MACD(df['Close'])
    df['macd_cross'] = macd.macd() > macd.macd_signal()
    df['sma_50'] = df['Close'].rolling(50).mean()
    df['sma_200'] = df['Close'].rolling(200).mean()
    df['golden_cross'] = df['sma_50'] > df['sma_200']
    df['volume_spike'] = df['Volume'] > df['Volume'].rolling(20).mean() * 1.5
    df['obv'] = ta.volume.OnBalanceVolumeIndicator(df['Close'], df['Volume']).on_balance_volume()
    df['obv_trend'] = df['obv'].diff().rolling(5).mean() > 0

    latest = df.iloc[-1]
    score = sum([
        latest['rsi'] < 35,
        latest['macd_cross'],
        latest['golden_cross'],
        latest['volume_spike'],
        latest['obv_trend']
    ])

    return {
        "Price": round(latest['Close'], 2),
        "RSI": round(latest['rsi'], 2),
        "MACD > Signal": bool(latest['macd_cross']),
        "Golden Cross": bool(latest['golden_cross']),
        "Volume Spike": bool(latest['volume_spike']),
        "OBV Trend Up": bool(latest['obv_trend']),
        "Score": score
    }

# Scan all tickers
results = []
for ticker in TICKERS:
    df = fetch_data(ticker)
    result = analyze(df)
    if result:
        result['Ticker'] = ticker
        results.append(result)

# Show the top picks
if results:
    df_results = pd.DataFrame(results).sort_values(by="Score", ascending=False)
    top_pick = df_results[df_results['Score'] >= 4].head(1)

    if not top_pick.empty:
        st.subheader("🔥 Recommended Buy for Tomorrow:")
        st.write(top_pick.set_index("Ticker"))
    else:
        st.info("No strong setup today. Wait for better entries.")
else:
    st.error("No valid data from tickers.")

