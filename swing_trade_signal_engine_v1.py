import yfinance as yf
import pandas as pd

# Choose a ticker to test
ticker = "AAPL"

# Try loading data
print(f"\n📦 Downloading data for: {ticker}")
df = yf.download(ticker, interval="1d", period="6mo")

# Show DataFrame shape
print(f"\n🧾 DataFrame shape: {df.shape}")

# Display first few rows
print("\n📊 First 5 rows:")
print(df.head())

# Check for 'Close' column
if 'Close' not in df.columns:
    print("❌ 'Close' column not found.")
else:
    print("✅ 'Close' column found.")

    # Check for NaN in Close
    nan_count = df['Close'].isna().sum()
    if nan_count > 0:
        print(f"⚠️ {nan_count} NaN values found in 'Close' column.")
    else:
        print("✅ No NaNs in 'Close'.")

    # Check number of rows (for SMA200 to work, need at least 200 rows)
    if len(df) < 200:
        print(f"⚠️ Only {len(df)} rows — not enough for SMA(200).")
    else:
        print("✅ Enough data for SMA(200).")
