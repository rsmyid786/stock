import time
import yfinance as yf

symbols = ['ADANIENT.NS', 'RELIANCE.NS', 'NSEI.NS']

for symbol in symbols:
    try:
        print(f"📈 Fetching {symbol}...")
        ticker = yf.Ticker(symbol)
        data = ticker.history(period="6mo", interval="1d")
        print(f"✅ {symbol}: {len(data)} rows")
    except Exception as e:
        print(f"❌ {symbol} failed: {e}")
    time.sleep(2)  # Add delay to prevent rate limits
