import warnings
import pandas as pd
import pymysql
from sqlalchemy import create_engine
from yahooquery import Ticker
import requests

# Suppress FutureWarnings
warnings.simplefilter(action='ignore', category=FutureWarning)

# ✅ Fetch NSE stock symbols dynamically from Wikipedia
def get_nse_stocks():
    print("🔄 Fetching NSE stock symbols from Wikipedia...")

    url = "https://en.wikipedia.org/wiki/NIFTY_50"
    tables = pd.read_html(url)

    for table in tables:
        if "Symbol" in table.columns:
            stock_list = table["Symbol"].tolist()
            stock_list = [symbol + ".NS" for symbol in stock_list]
            print(f"✅ Found {len(stock_list)} NSE stocks.")
            return stock_list

    print("❌ No NSE stocks found.")
    return []

# ✅ MySQL Database Connection
db_user = "root"
db_password = ""
db_host = "localhost"
db_name = "stock_data"

engine = create_engine(f"mysql+pymysql://{db_user}:{db_password}@{db_host}/{db_name}")

# ✅ Fetch NSE stocks
stock_symbols = get_nse_stocks()

# ✅ Loop through stocks & calculate MACD
for stock in stock_symbols:
    print(f"📊 Fetching data for {stock}...")

    try:
        ticker = Ticker(stock)
        data = ticker.history(period="6mo", interval="1d").reset_index()

        if "close" not in data.columns:
            print(f"⚠️ Skipping {stock} (missing 'close' price).")
            continue

        # ✅ MACD Calculation
        data["EMA_12"] = data["close"].ewm(span=12, adjust=False).mean()
        data["EMA_26"] = data["close"].ewm(span=26, adjust=False).mean()
        data["MACD"] = data["EMA_12"] - data["EMA_26"]
        data["Signal_lin"] = data["MACD"].ewm(span=9, adjust=False).mean()
        data["Histogram"] = data["MACD"] - data["Signal_lin"]  # FIXED

        data["stock_symbol"] = stock


        # ✅ Save to MySQL
        data[["date", "stock_symbol", "close", "MACD", "Signal_lin", "Histogram"]].to_sql(
            "macd_data_old", engine, if_exists="append", index=False
        )

        print(f"✅ {stock} data saved!")

    except Exception as e:
        print(f"❌ Error fetching data for {stock}: {e}")

print("✅ All stock data processing completed!")
