import streamlit as st
import pandas as pd
import yfinance as yf
import ta
import plotly.graph_objects as go

@st.cache_data
def load_sp500():
    url = 'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies'
    df = pd.read_html(url)[0]
    return df['Symbol'].tolist()

tickers = load_sp500()

st.title("📊 Early Buy Signal Screener (S&P 500 + Pattern Detection)")

# Fetch historical data
@st.cache_data
def fetch_data(ticker, interval):
    try:
        return yf.download(ticker, period='5d', interval=interval, progress=False)
    except:
        return pd.DataFrame()

# --- Pattern Detection Functions ---
def detect_double_bottom(prices):
    lows = prices.rolling(window=3).min()
    low_points = lows[lows == prices]
    low_vals = low_points.dropna().tail(2).values
    if len(low_vals) == 2 and abs(low_vals[0] - low_vals[1]) / low_vals[0] < 0.02:
        return True
    return False

def is_falling_wedge(prices):
    recent = prices[-15:]
    return not recent.is_monotonic_decreasing and recent[-1] > recent.mean()

def is_bullish_flag(prices, volume):
    move_up = (prices[-10] - prices[-20]) / prices[-20]
    pullback = (prices[-1] - prices[-10]) / prices[-10]
    vol_now = volume[-5:].mean()
    vol_before = volume[-15:-5].mean()
    return move_up > 0.05 and pullback > -0.03 and vol_now < vol_before

# Analyze each stock
def analyze_stock(ticker):
    signals = []
    score = 0
    price = None
    patterns = []
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

        if label == "1h":
            try:
                if detect_double_bottom(df['Close']):
                    patterns.append("Double Bottom")
                if is_falling_wedge(df['Close']):
                    patterns.append("Falling Wedge")
                if is_bullish_flag(df['Close'], df['Volume']):
                    patterns.append("Bullish Flag")
            except:
                pass

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
        "Patterns": ", ".join(patterns) if patterns else "None",
        "Data": data_all
    }

# Run analysis
results = []
with st.spinner("Scanning S&P 500..."):
    for ticker in tickers:
        try:
            res = analyze_stock(ticker)
            if res and res["Signal"] != "🔴 No Signal":
                results.append(res)
        except:
            continue

# Display results
if results:
    df = pd.DataFrame(results)
    st.dataframe(df[["Ticker", "Price", "Signal", "Patterns", "Details"]])

    # Charts
    for r in results:
        with st.expander(f"📈 {r['Ticker']} Chart (1h)"):
            d = r["Data"].get("1h")
            if d is not None:
                fig = go.Figure()
                fig.add_trace(go.Scatter(x=d.index, y=d['Close'], mode='lines', name='Close'))
                fig.add_trace(go.Scatter(x=d.index, y=d['MACD'], mode='lines', name='MACD'))
                fig.add_trace(go.Scatter(x=d.index, y=d['Signal'], mode='lines', name='Signal Line'))
                fig.update_layout(title=f"{r['Ticker']} (1h)", xaxis_title="Time", yaxis_title="Price")
                st.plotly_chart(fig)
else:
    st.warning("No early buy signals found at this time.")
