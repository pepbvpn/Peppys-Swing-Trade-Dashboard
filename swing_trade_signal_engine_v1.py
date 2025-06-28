def analyze_signals(df):
    if df.empty:
        st.error("❌ No data returned. Please check the ticker, interval, or period.")
        return None

    if 'Close' not in df.columns:
        st.error("❌ 'Close' column missing. Try a different interval or period.")
        st.write("Columns found:", list(df.columns))
        return None

    df = df.copy()
    df = df.dropna(subset=['Close'])

    # Technical Indicators
    df['rsi'] = ta.momentum.RSIIndicator(df['Close']).rsi()
    macd = ta.trend.MACD(df['Close'])
    df['macd'] = macd.macd()
    df['macd_signal'] = macd.macd_signal()
    df['sma50'] = ta.trend.SMAIndicator(df['Close'], window=50).sma_indicator()
    df['sma200'] = ta.trend.SMAIndicator(df['Close'], window=200).sma_indicator()

    latest = df.iloc[-1]
    signals = {
        "RSI < 30 (Oversold)": latest['rsi'] < 30,
        "MACD > Signal": latest['macd'] > latest['macd_signal'],
        "Price > SMA50": latest['Close'] > latest['sma50'],
        "SMA50 > SMA200": latest['sma50'] > latest['sma200']
    }

    score = sum(signals.values())
    if score == 4:
        rating = "🔥 High Conviction Buy"
    elif score == 3:
        rating = "⚠️ Watch List"
    else:
        rating = "❌ Skip for Now"

    return signals, score, rating, df.tail()
