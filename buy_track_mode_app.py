import yfinance as yf
import pandas as pd
import numpy as np
import streamlit as st
from streamlit_autorefresh import st_autorefresh

st.set_page_config(page_title="Custom Ticker Trade Scanner", layout="wide")
st.title("📊 Custom Ticker Trade Readiness Scanner")
st_autorefresh(interval=300000, limit=None, key="refresh")  # Refresh every 5 min

option_type = st.selectbox("Trade Direction", ["CALL", "PUT"])

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

    return data

def get_trade_score(ticker, interval, option_type="CALL"):
    try:
        period = {"15m": "10d", "1h": "30d", "1d": "1y"}[interval]
        df = yf.download(ticker, interval=interval, period=period, progress=False)

        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        if df.empty:
            return 0

        df = compute_indicators(df)
        df.dropna(inplace=True)
        latest = df.iloc[-1]

        signals = {
            "RSI": (option_type == "CALL" and latest['RSI'] < 35) or (option_type == "PUT" and latest['RSI'] > 70),
            "MACD": (option_type == "CALL" and latest['MACD'] > latest['Signal']) or (option_type == "PUT" and latest['MACD'] < latest['Signal']),
            "VWAP": (option_type == "CALL" and latest['Close'] > latest['VWAP']) or (option_type == "PUT" and latest['Close'] < latest['VWAP']),
            "SMA": (option_type == "CALL" and latest['Close'] > latest['SMA_50'] > latest['SMA_200']) or (option_type == "PUT" and latest['Close'] < latest['SMA_50'] < latest['SMA_200'])
        }
        return sum(signals.values())
    except Exception:
        return 0

st.info("Scanning selected tickers. This may take a few moments...")
results = []
for ticker in tickers_to_scan:
    scores = {
        interval: get_trade_score(ticker, interval, option_type)
        for interval in ["15m", "1h", "1d"]
    }
    if all(score >= 3 for score in scores.values()):
        results.append({"Ticker": ticker, **scores})

if results:
    st.success("✅ Tickers with Trade Readiness ≥ 3/4 across all timeframes")
    st.dataframe(pd.DataFrame(results))
else:
    st.warning("No tickers found with strong multi-interval setup right now.")
