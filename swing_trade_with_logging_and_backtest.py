
import streamlit as st
import pandas as pd
import yfinance as yf
import ta
import matplotlib.pyplot as plt
import io

st.set_page_config(page_title="Swing Trade Dashboard with Charts", layout="wide")
st.title("📈 Swing Trade Signal Dashboard with Mini Charts")

tickers_input = st.text_input("Enter ticker symbols (comma-separated)", value="NVDA, AAPL, MSFT, TSLA, SPY")
interval = st.selectbox("Select interval", options=["1d", "1h", "15m"])
period_map = {"1d": "1y", "1h": "60d", "15m": "10d"}
period = period_map[interval]
tickers = [ticker.strip().upper() for ticker in tickers_input.split(",")]

def generate_mini_chart(ticker, interval="1d", period="6mo"):
    df = yf.download(ticker, period=period, interval=interval, progress=False)
    if df.empty or len(df) < 50:
        return None

    df['SMA50'] = df['Close'].rolling(window=50).mean()
    df['SMA200'] = df['Close'].rolling(window=200).mean()

    close_series = df['Close'].squeeze()
    volume_series = df['Volume'].squeeze()

    obv = ta.volume.OnBalanceVolumeIndicator(close=close_series, volume=volume_series).on_balance_volume()
    df['OBV'] = obv

    fig, ax = plt.subplots(2, 1, figsize=(6, 4), gridspec_kw={'height_ratios': [3, 1]})
    ax[0].plot(df.index, df['Close'], label="Price", linewidth=1.5)
    ax[0].plot(df.index, df['SMA50'], label="SMA50", linestyle="--")
    ax[0].plot(df.index, df['SMA200'], label="SMA200", linestyle="--")
    ax[0].legend()
    ax[0].grid(True)

    ax[1].plot(df.index, df['OBV'], label="OBV", color="purple", linewidth=1.2)
    ax[1].set_title("OBV")
    ax[1].grid(True)

    plt.tight_layout()
    buf = io.BytesIO()
    plt.savefig(buf, format="png")
    buf.seek(0)
    plt.close(fig)
    return buf

# Generate signal data and display chart
for ticker in tickers:
    st.subheader(f"{ticker} Signal + Chart")

    df = yf.download(ticker, period=period, interval=interval, progress=False)
    if df.empty or len(df) < 50:
        st.warning(f"Not enough data for {ticker}")
        continue

    df['RSI'] = ta.momentum.RSIIndicator(close=df['Close'].squeeze()).rsi()
    df['SMA50'] = df['Close'].rolling(window=50).mean()
    df['SMA200'] = df['Close'].rolling(window=200).mean()

    latest = df.iloc[-1]
    sma50 = latest['SMA50']
    sma200 = latest['SMA200']
    rsi = latest['RSI']

    if sma50 > sma200 and latest['Close'] > sma50:
        signal = "✅ BUY"
    else:
        signal = "❌ WAIT"

    info = {
        "Ticker": ticker,
        "Close": round(latest['Close'], 2),
        "RSI": round(rsi, 2),
        "SMA50": round(sma50, 2),
        "SMA200": round(sma200, 2),
        "Signal": signal
    }

    st.dataframe(pd.DataFrame([info]))

    img_buf = generate_mini_chart(ticker, interval=interval, period=period)
    if img_buf:
        st.image(img_buf, caption=f"{ticker} Chart", use_column_width=True)


# 🔄 Trade Logging Section
st.sidebar.header("📘 Trade Log")

# Initialize session state for trade log
if "trade_log" not in st.session_state:
    st.session_state.trade_log = []

# Add form to view log
if st.session_state.trade_log:
    st.sidebar.subheader("Logged Trades")
    log_df = pd.DataFrame(st.session_state.trade_log)
    st.sidebar.dataframe(log_df)

    # Download button
    csv = log_df.to_csv(index=False).encode('utf-8')
    st.sidebar.download_button(
        label="Download Trade Log",
        data=csv,
        file_name='trade_log.csv',
        mime='text/csv'
    )

# Add buttons to log trades per ticker
for ticker in tickers:
    df = yf.download(ticker, period=period, interval=interval, progress=False)
    if df.empty or len(df) < 50:
        continue

    latest = df.iloc[-1]
    close_price = round(latest['Close'], 2)

    if st.button(f"📝 Log Trade for {ticker} at ${close_price}"):
        st.session_state.trade_log.append({
            "Date": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M"),
            "Ticker": ticker,
            "Entry Price": close_price,
            "Signal Type": "Swing" if interval in ["1h", "15m"] else "Long-Term"
        })
        st.success(f"Logged {ticker} trade at ${close_price}")


# 📈 Backtesting Section
st.header("📊 Backtesting Engine")

bt_ticker = st.text_input("Enter ticker to backtest", value="NVDA")
bt_interval = st.selectbox("Backtest interval", options=["1d", "1h"], index=0)
bt_period = "1y" if bt_interval == "1d" else "60d"

df_bt = yf.download(bt_ticker, period=bt_period, interval=bt_interval, progress=False)
if not df_bt.empty and len(df_bt) > 50:
    df_bt['RSI'] = ta.momentum.RSIIndicator(close=df_bt['Close']).rsi()
    macd = ta.trend.MACD(close=df_bt['Close'])
    df_bt['MACD'] = macd.macd()
    df_bt['MACD_SIGNAL'] = macd.macd_signal()
    df_bt['20EMA'] = df_bt['Close'].ewm(span=20).mean()
    df_bt['50EMA'] = df_bt['Close'].ewm(span=50).mean()
    volume_avg = df_bt['Volume'].rolling(window=10).mean()
    df_bt['Volume_Spike'] = df_bt['Volume'] > volume_avg
    df_bt.dropna(inplace=True)

    # Simulate trades
    trades = []
    for i in range(len(df_bt)-1):
        row = df_bt.iloc[i]
        next_day = df_bt.iloc[i+1]
        entry_price = next_day['Open']
        target = entry_price * 1.10
        stop = entry_price * 0.95

        # Entry logic
        entry = (
            row['RSI'] > 30 and row['RSI'] < 40 and
            row['MACD'] > row['MACD_SIGNAL'] and
            row['Close'] > row['20EMA'] and
            row['Close'] < row['50EMA'] and
            row['Volume_Spike']
        )

        if entry:
            for j in range(i+1, len(df_bt)):
                high = df_bt.iloc[j]['High']
                low = df_bt.iloc[j]['Low']
                if high >= target:
                    result = "Win"
                    exit_price = target
                    break
                elif low <= stop:
                    result = "Loss"
                    exit_price = stop
                    break
            else:
                result = "Open"
                exit_price = df_bt.iloc[-1]['Close']

            trades.append({
                "Entry Date": df_bt.index[i+1].strftime("%Y-%m-%d"),
                "Entry Price": round(entry_price, 2),
                "Exit Price": round(exit_price, 2),
                "Result": result,
                "Return %": round((exit_price - entry_price) / entry_price * 100, 2)
            })

    if trades:
        results_df = pd.DataFrame(trades)
        st.dataframe(results_df)
        win_rate = (results_df['Result'] == "Win").mean() * 100
        avg_return = results_df["Return %"].mean()
        st.metric("Win Rate", f"{win_rate:.2f}%")
        st.metric("Avg Return", f"{avg_return:.2f}%")
    else:
        st.info("No signals triggered during this period.")
else:
    st.warning("Not enough data to backtest.")
