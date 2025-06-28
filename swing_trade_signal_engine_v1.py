import yfinance as yf
import pandas as pd
import ta

def analyze(ticker, interval="1d", period="6mo"):
    df = yf.download(ticker, interval=interval, period=period)
    if df.empty or 'Close' not in df.columns or df['Close'].isna().all():
        return f"❌ Skipping {ticker} — no valid data."

    df = df.dropna(subset=['Close']).copy()
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
        "Ticker": ticker,
        "Price": round(latest['Close'], 2),
        "RSI": round(latest['rsi'], 2),
        "MACD > Signal": bool(latest['macd_cross']),
        "Golden Cross": bool(latest['golden_cross']),
        "Volume Spike": bool(latest['volume_spike']),
        "OBV Trend Up": bool(latest['obv_trend']),
        "Score": score
    }

tickers = ["AAPL", "MSFT", "NVDA", "TSLA", "AMZN"]
results = [analyze(ticker) for ticker in tickers]
df = pd.DataFrame([r for r in results if isinstance(r, dict)])
print(df)
