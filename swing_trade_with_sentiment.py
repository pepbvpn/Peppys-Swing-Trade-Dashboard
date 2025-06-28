import streamlit as st
import pandas as pd
import yfinance as yf
import ta
import plotly.graph_objects as go

# Load S&P 500 tickers from Wikipedia (or from CSV for speed)
@st.cache_data
def load_sp500():
    url = 'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies'
    df = pd.read_html(url)[0]
    return df['Symbol'].tolist()

tickers = load_sp500()

st.title("🚨 Early Buy Signal Screener (S&P 500)")
st.caption("Scans 15m, 1h, and 1d intervals for pre-rally momentum")

@st.cache_data
def fetch_data(ticker, interval):
    try:
        return yf.download(ticker, period='5d', interval=interval, progress=False)
    except:
        return pd.DataFrame()

def analyze_stock(ticker):
    signals = []
    score = 0
    price = None
    data_all = {}

    for label, interval in [("15m", "15m"), ("1h", "60m"), ("1d", "1d")]:
        df = fetch_data(ticker, interval)
        if df.empty or len(df) < 50:
            continue
        df['RSI'] = ta.momentum.RSIIndicator(df['Close'], window=14).rsi()
        macd = ta.trend.MACD(df['Close'])
        df['MACD'] = macd.macd()
        df['Signal'] = macd.macd_signal()
        df['VolumeAvg'] = df['Volume'].rolling(window=20).mean()

        latest = df.iloc[-1]
        price = latest['Close']
        rsi = latest['RSI']
        macd_cross = latest['MACD'] > latest['Signal']
        volume_spike = latest['Volume'] > 1.5 * latest['VolumeAvg']
        bullish = rsi > 25 and rsi < 40 and macd_cross and volume_spike

        if label in ["15m", "1h"] and bullish:
            score += 1
        if label == "1d" and rsi > 40:
            score += 1

        data_all[label] = df
        signals.append(f"{label}: {'✅' if bullish else '❌'}")

    if score >= 3:
        signal = "🟢 Early Rally"
    elif score == 2:
        signal = "🟠 Rally Forming"
    else:
        signal = "🔴 No Signal"

    return {
        "Ticker": ticker,
        "Price": round(price, 2) if price else "N/A",
        "Signal": signal,
        "Details": " | ".join(signals),
        "Data": data_all
    }

# Run analysis (can be slow; optimize later)
results = []
with st.spinner("Scanning S&P 500..."):
    for ticker in tickers:
        try:
            res = analyze_stock(ticker)
            if res and res["Signal"] != "🔴 No Signal":
                results.append(res)
        except:
            continue

if results:
    df = pd.DataFrame(results)
    st.dataframe(df[["Ticker", "Price", "Signal", "Details"]])

    # Charts
    for r in results:
        with st.expander(f"📊 {r['Ticker']} Chart (1h)"):
            d = r["Data"].get("1h")
            if d is not None:
                fig = go.Figure()
                fig.add_trace(go.Scatter(x=d.index, y=d['Close'], mode='lines', name='Close'))
                fig.add_trace(go.Scatter(x=d.index, y=d['MACD'], mode='lines', name='MACD'))
                fig.add_trace(go.Scatter(x=d.index, y=d['Signal'], mode='lines', name='Signal Line'))
                fig.update_layout(title=f"{r['Ticker']} (1h)", xaxis_title="Time", yaxis_title="Price")
                st.plotly_chart(fig)
else:
    st.warning("No early buy signals found right now.")
