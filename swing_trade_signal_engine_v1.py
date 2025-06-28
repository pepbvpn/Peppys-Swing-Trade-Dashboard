
import pandas as pd
import yfinance as yf
import ta
import streamlit as st

st.set_page_config(page_title="Swing Trading Signal Engine", layout="wide")
st.title("📊 Swing Trading Signal Engine (v1)")

def load_data(ticker, interval='1d', period='6mo'):
    df = yf.download(ticker, interval=interval, period=period)
    df.dropna(inplace=True)
    return df

def analyze(df):
    if df.empty or len(df) < 50:
        return None

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

tickers = st.text_area("Enter Tickers (comma separated)", "AAPL,MSFT,NVDA,TSLA,AMZN").upper().split(',')
interval = st.selectbox("Interval", ["1d", "1h", "15m"], index=0)

analyze_button = st.button("🔍 Run Analysis")

if analyze_button:
    results = []
    for ticker in tickers:
        df = load_data(ticker.strip(), interval)
        analysis = analyze(df)
        if analysis:
            analysis["Ticker"] = ticker.strip()
            results.append(analysis)
    if results:
        df_result = pd.DataFrame(results).set_index("Ticker")
        st.success("✅ Analysis Complete")
        st.dataframe(df_result)
    else:
        st.warning("No valid signals found.")
