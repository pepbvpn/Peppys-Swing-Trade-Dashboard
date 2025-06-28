import streamlit as st
import pandas as pd
import finnhub
import time
import ta
import plotly.graph_objects as go

# --- CONFIG ---
API_KEY = "d1g2cp1r01qk4ao0k610d1g2cp1r01qk4ao0k61g"
client = finnhub.Client(api_key=API_KEY)

# Load tickers (demo: top 100 US stocks)
tickers_df = pd.read_csv("https://raw.githubusercontent.com/datasets/s-and-p-500-companies/master/data/constituents.csv")
tickers = [t.replace('.', '-') for t in tickers_df["Symbol"].tolist()[:100]]

st.title("📈 US Market Screener (Finnhub + Patterns)")
st.caption("Scans for early momentum signals and bullish chart patterns")

# --- Candle Data Function (Fixed for 'D') ---
def get_finnhub_data(symbol, resolution='15', count=100):
    res_map = {'1': 60, '5': 300, '15': 900, '30': 1800, '60': 3600, 'D': 86400}
    duration = res_map.get(resolution, 900)
    now = int(time.time())
    past = now - count * duration
    try:
        res = client.stock_candles(symbol, resolution, past, now)
        if res.get('s') != 'ok':
            return pd.DataFrame()
        df = pd.DataFrame(res)
        df['t'] = pd.to_datetime(df['t'], unit='s')
        df.set_index('t', inplace=True)
        df.rename(columns={'c': 'Close', 'o': 'Open', 'h': 'High', 'l': 'Low', 'v': 'Volume'}, inplace=True)
        return df[['Open', 'High', 'Low', 'Close', 'Volume']]
    except Exception as e:
        print(f"[{symbol}] error: {e}")
        return pd.DataFrame()

# --- Pattern Detection ---
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

# --- Stock Analyzer ---
def analyze_stock(ticker):
    score = 0
    patterns = []
    signal_details = []
    price = None
    data_all = {}

    for label, resolution in [("15m", '15'), ("1h", '60'), ("1d", 'D')]:
        df = get_finnhub_data(ticker, resolution=resolution)
        time.sleep(1.1)  # stay within 60 req/min
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

        signal_details.append(f"{label}: {'✅' if bullish else '❌'}")
        data_all[label] = df

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
        "Details": " | ".join(signal_details),
        "Patterns": ", ".join(patterns) if patterns else "None",
        "Data": data_all
    }

# --- Run Screener ---
results = []
with st.spinner("Scanning top US stocks..."):
    for ticker in tickers:
        try:
            res = analyze_stock(ticker)
            if res and res["Signal"] != "🔴 No Signal":
                results.append(res)
        except Exception as e:
            if "403" in str(e):
                print(f"[{ticker}] restricted by plan.")
            else:
                print(f"[{ticker}] failed: {e}")
            continue

# --- Display Results ---
if results:
    df = pd.DataFrame(results)
    st.dataframe(df[["Ticker", "Price", "Signal", "Patterns", "Details"]])

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
    st.warning("No early signals found right now.")
