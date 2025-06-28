import yfinance as yf
import pandas as pd

ticker = "AAPL"
interval = "1d"
period = "6mo"

print(f"\n📦 Downloading data for {ticker} with interval={interval}, period={period}...")
df = yf.download(ticker, interval=interval, period=period)

print(f"\n✅ Download complete — DataFrame shape: {df.shape}")
print("\n📊 DataFrame preview:")
print(df.head())

if df.empty:
    print("❌ DataFrame is empty.")
    exit()

if 'Close' not in df.columns:
    print("❌ 'Close' column not found. Available columns:")
    print(list(df.columns))
    exit()

try:
    close_nan_count = int(df['Close'].isna().sum())
    print(f"\n🔍 NaN count in 'Close': {close_nan_count}")
    if close_nan_count > 0:
        print("⚠️ Warning: Missing values in 'Close'.")
    else:
        print("✅ No NaNs in 'Close'.")
except Exception as e:
    print(f"❌ Error checking NaNs in 'Close': {e}")
    exit()

if len(df) < 200:
    print(f"⚠️ Only {len(df)} rows — not enough for SMA(200).")
else:
    print("✅ Sufficient data for 200-day indicators.")
