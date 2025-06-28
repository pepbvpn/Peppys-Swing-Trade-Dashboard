import yfinance as yf
import pandas as pd
import ta

def analyze(ticker, interval="1d", period="6mo"):
    try:
        df = yf.download(ticker, interval=interval, period=period)
        if df.empty or 'Close' not in df.columns:
            print(f"⚠️ Skipping {ticker} — no data.")
            return None

        df.dropna(subset=['Close'], inplace=True)

        if len(df) < 200:
            print(f"⚠️ Skipping {ticker} — not enough data.")
            return None

        # Add technical indicators
        df['RSI'] = ta.momentum.RSIIndicator(df['Close']).rsi()
        macd = ta.trend.MACD(df['Close'])
        df['MACD_Cross'] = macd.macd_diff() > 0
        df['SMA50'] = df['Close'].rolling(50).mean()
        df['SMA200'] = df['Close'].rolling(200).mean()
        df['GoldenCross'] = df['SMA50'] > df['SMA200']
        df['VolSpike'] = df['Volume'] > df['Volume'].rolling(20).mean() * 1.5
        obv = ta.volume.OnBalanceVolumeIndicator(df['Close'], df['Volume'])
        df['OBVTrend'] = obv.on_balance_volume().diff().rolling(5).mean() > 0

        latest = df.iloc[-1]

        score = sum([
            latest['RSI'] < 35,
            latest['MACD_Cross'],
            latest['GoldenCross'],
            latest['VolSpike'],
            latest['OBVTrend']
        ])

        return {
            "Ticker": ticker,
            "Price": round(latest['Close'], 2),
            "RSI": round(latest['RSI'], 2),
            "MACD_Cross": bool(latest['MACD_Cross']),
            "GoldenCross": bool(latest['GoldenCross']),
            "VolSpike": bool(latest['VolSpike']),
            "OBVTrend": bool(latest['OBVTrend']),
            "TradeScore": score
        }
    except Exception as e:
        print(f"❌ Error processing {ticker}: {e}")
        return None

# Try it on a few stocks
tickers = ["AAPL", "MSFT", "NVDA", "TSLA", "AMZN"]
results = [analyze(ticker) for ticker in tickers]
results = [r for r in results if r]  # Remove None

# Convert to DataFrame and show
df_result = pd.DataFrame(results)
print(df_result.sort_values("TradeScore", ascending=False))
