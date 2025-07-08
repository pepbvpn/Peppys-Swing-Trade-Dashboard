import yfinance as yf
import pandas as pd
import numpy as np
import streamlit as st
from streamlit_autorefresh import st_autorefresh

st.set_page_config(page_title="Custom Ticker Trade Scanner", layout="wide")
st.title("📊 Custom Ticker Trade Readiness Scanner")
st_autorefresh(interval=300000, limit=None, key="refresh")  # Refresh every 5 min

option_type = st.selectbox("Trade Direction", ["CALL", "PUT"])
min_score = st.slider("Minimum Score per Interval (out of 4)", min_value=1, max_value=4, value=2)

# Custom tickers to scan
tickers_to_scan = [
    "TSLA", "NVDA", "AAPL", "SPY", "QQQ", "META", "AMD", "AMZN", "MSFT", "BABA", "PLTR", "COIN",
    "NFLX", "RIVN", "SNOW", "MU", "SHOP", "AFRM", "LCID", "UBER", "GOOGL", "GOOG", "BRK.B", "LLY",
    "AVGO", "JNJ", "V", "JPM", "XOM", "UNH", "PG", "MA", "WMT", "ORCL", "HOOD"
]

def compute_indicators(data):
    delta = data['Close'].diff()
    gain = pd.Series(np.where(delta > 0, delta, 0), index=data.index)
    loss = pd.Series(np.where(delta < 0, -delta, 0), index=data.index)
    avg_gain = gain.rolling(window=14).mean()
    avg_loss = loss.rolling(window=14).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    data['RSI'] = rsi

    ema12 = data['Close'].ewm(span=12, adjust=False).mean()
    ema26 = data['Close'].ewm(span=26, adjust=False).mean()
    macd = ema12 - ema26
    signal = macd.ewm(span=9, adjust=False).mean()
    data['MACD'] = macd
    data['Signal'] = signal

    data['TP'] = (data['High'] + data['Low'] + data['Close']) / 3
    volume = data['Volume'] if isinstance(data['Volume'], pd.Series) else data['Volume'].iloc[:, 0]
    data['VP'] = data['TP'] * volume
    data['Cumulative_VP'] = data['VP'].cumsum()
    data['Cumulative_Volume'] = volume.cumsum()
    data['VWAP'] = data['Cumulative_VP'] / data['Cumulative_Volume']

    data['SMA_50'] = data['Close'].rolling(window=50).mean()
    data['SMA_200'] = data['Close'].rolling(window=200).mean()

    obv = [0]
    for i in range(1, len(data)):
        if data['Close'].iloc[i] > data['Close'].iloc[i - 1]:
            obv.append(obv[-1] + data['Volume'].iloc[i])
        elif data['Close'].iloc[i] < data['Close'].iloc[i - 1]:
            obv.append(obv[-1] - data['Volume'].iloc[i])
        else:
            obv.append(obv[-1])
    data['OBV'] = obv
    data['OBV_Slope'] = pd.Series(obv).diff().rolling(window=5).mean()

    return data

def get_signals(latest, option_type):
    return {
        "RSI": (option_type == "CALL" and latest['RSI'] < 35) or (option_type == "PUT" and latest['RSI'] > 70),
        "MACD": (option_type == "CALL" and latest['MACD'] > latest['Signal']) or (option_type == "PUT" and latest['MACD'] < latest['Signal']),
        "VWAP": (option_type == "CALL" and latest['Close'] > latest['VWAP']) or (option_type == "PUT" and latest['Close'] < latest['VWAP']),
        "SMA": (option_type == "CALL" and latest['Close'] > latest['SMA_50'] > latest['SMA_200']) or (option_type == "PUT" and latest['Close'] < latest['SMA_50'] < latest['SMA_200'])
    }

def get_trade_score_and_sentiment(ticker, interval, option_type="CALL"):
    try:
        period = {"15m": "10d", "1h": "30d", "1d": "1y"}[interval]
        df = yf.download(ticker, interval=interval, period=period, progress=False)

        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        if df.empty:
            return 0, "No data"

        df = compute_indicators(df)
        df.dropna(inplace=True)
        latest = df.iloc[-1]
        signals = get_signals(latest, option_type)
        score = list(signals.values()).count(True)

        slope = latest['OBV_Slope']
        if slope > 0:
            sentiment = "Accumulating"
        elif slope < 0:
            sentiment = "Distributing"
        else:
            sentiment = "Neutral"

        return score, sentiment
    except Exception:
        return 0, "Error"

st.info("Scanning selected tickers. This may take a few moments...")
results = []
for ticker in tickers_to_scan:
    passes_filter = True
    row = {"Ticker": ticker}
    sentiments = []
    for interval in ["15m", "1h", "1d"]:
        score, sentiment = get_trade_score_and_sentiment(ticker, interval, option_type)
        if score < min_score:
            passes_filter = False
            break
        row[f"{interval} Score"] = f"{score}/4"
        sentiments.append(f"{interval}: {sentiment}")
    if passes_filter:
        row["Institutional Sentiment"] = ", ".join(sentiments)
        results.append(row)

if results:
    st.success(f"✅ Tickers with Trade Readiness ≥ {min_score}/4 across all timeframes (15m, 1h, 1d)")
    st.dataframe(pd.DataFrame(results))
else:
    st.warning("No tickers found with the desired multi-interval setup right now.")
