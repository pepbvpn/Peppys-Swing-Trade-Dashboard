import yfinance as yf
import pandas as pd

ticker = "AAPL"
interval = "1d"
period = "6mo"

print(f"\n📦 Downloading data for {ticker} with interval={interval}, period={period}...")
df = yf.download(ticker, interval=interval, period=period)

# Basic info
print(f"\n✅ Download complete — DataFrame shape: {df.shape}")
print("\n📊 DataFrame preview:")
print(df.head())

# Case 1: DataFrame is completely empty
if df.empty:
    print("❌ DataFrame is empty. Likely a download issue.")
    exit()

# Case 2: 'Close' column is missing
if 'Close' not in df.columns:
    print("❌ 'Close' column not found in DataFrame.")
    print("Available columns:", list(df.columns))
    exit()

# Case 3: 'Close' column exists — now check for NaNs
close_nan_count = df['Close'].isna().sum()
print(f"\n🔍 NaN count in 'Close': {close_nan_count}")
if close_nan_count > 0:
    print("⚠️ Warning: Missing values detected in 'Close' column.")
else:
    print("✅ 'Close' column is complete.")

# Case 4: Enough rows for SMA indicators
if len(df) < 200:
    print(f"⚠️ Only {len(df)} rows — not enough for 200-day SMA.")
else:
    print("✅ Sufficient data for 200-day indicators.")
