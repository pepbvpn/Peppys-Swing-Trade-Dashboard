import finnhub
import pandas as pd
import time

# Your API Key
API_KEY = "d1g2cp1r01qk4ao0k610d1g2cp1r01qk4ao0k61g"
client = finnhub.Client(api_key=API_KEY)

# Test tickers (top 5 US stocks)
tickers = ["AAPL", "MSFT", "AMZN", "NVDA", "GOOGL"]

def get_finnhub_data(symbol, resolution='15', count=50):
    now = int(time.time())
    past = now - count * 60 * int(resolution)
    res = client.stock_candles(symbol, resolution, past, now)
    if res['s'] != 'ok':
        return pd.DataFrame()
    df = pd.DataFrame(res)
    df['t'] = pd.to_datetime(df['t'], unit='s')
    df.set_index('t', inplace=True)
    df.rename(columns={'c': 'Close', 'o': 'Open', 'h': 'High', 'l': 'Low', 'v': 'Volume'}, inplace=True)
    return df[['Open', 'High', 'Low', 'Close', 'Volume']]

for ticker in tickers:
    df = get_finnhub_data(ticker)
    print(f"\n{ticker} - Last 3 candles:")
    print(df.tail(3))
