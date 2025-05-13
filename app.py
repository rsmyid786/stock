from flask import Flask, request, jsonify
from flask_cors import CORS
import pandas as pd
import pymysql
from sqlalchemy import create_engine
from yahooquery import Ticker
import yfinance as yf
import time
import requests
import warnings
from datetime import datetime, timedelta
import xml.etree.ElementTree as ET  # Replaced lxml with built-in xml.etree.ElementTree

app = Flask(__name__)
CORS(app)

# 👇 Suppress FutureWarnings
warnings.simplefilter(action='ignore', category=FutureWarning)

# ✅ MySQL Database Connection
db_user = "u218267760_stock"
db_password = "+!s[CyA6"
db_host = "194.59.164.10"
db_name = "u218267760_stock"
engine = create_engine(f"mysql+pymysql://{db_user}:{db_password}@{db_host}/{db_name}")

# ✅ Function to get NSE stocks
import pandas as pd

def get_nse_stocks():
    print("🔄 Fetching NSE stock symbols from Wikipedia...")

    url = "https://en.wikipedia.org/wiki/NIFTY_50"
    tables = pd.read_html(url)

    stock_list = []

    for table in tables:
        if "Symbol" in table.columns:
            # Extract symbols and add .NS suffix
            nifty_50_symbols = table["Symbol"].tolist()
            nifty_50_symbols = [symbol + ".NS" for symbol in nifty_50_symbols]
            nifty_50_symbols.append("NSEI.NS")  # Add Nifty index
            print(f"✅ Found {len(nifty_50_symbols) - 1} Nifty 50 stocks and added Nifty index.")
            stock_list.extend(nifty_50_symbols)
            break

    if stock_list:
        print(f"✅ Total stocks including index: {len(stock_list)}")
    else:
        print("❌ No NSE stocks found.")
    
    return stock_list


# ✅ Route to fetch MACD data


@app.route('/api/fetch-stock', methods=['GET'])
def fetch_stock_data():
    try:
        ticker = yf.Ticker("ADANIENT.NS")
        data = ticker.history(period="6mo", interval="1d")
        
        # If the data is empty or there's no "Close" column, return an error message
        if data.empty or "Close" not in data.columns:
            return jsonify({"error": "No valid data found for ADANIENT.NS"}), 404

        # Convert the data into a JSON-friendly format (e.g., list of dictionaries)
        data_dict = data.reset_index().to_dict(orient="records")

        # Return the data as a JSON response
        return jsonify({"stock_data": data_dict})

    except Exception as e:
        return jsonify({"error": str(e)}), 500




# ✅ Route to fetch MACD data and store it
@app.route('/api/fetch-macd', methods=['GET'])
def fetch_macd_data():
    stock_symbols = get_nse_stocks()
    total_saved = 0
    days_back = 30
    start_date = datetime.now() - timedelta(days=days_back)

    # STEP 1: Load existing data in the last 30 days
    with engine.connect() as conn:
        existing_df = pd.read_sql(f"""
            SELECT stock_symbol, date FROM macd_data
            WHERE date >= '{start_date.date()}'
        """, conn)
        existing_df['date'] = pd.to_datetime(existing_df['date'])
    
    existing_map = {}
    for _, row in existing_df.iterrows():
        existing_map.setdefault(row['stock_symbol'], set()).add(row['date'].date())

    for stock in stock_symbols:
        try:
            print(f"🔍 Checking {stock}...")

            # Skip stocks that already have data for every day in the past month
            if stock in existing_map and len(existing_map[stock]) >= 20:
                print(f"✅ Skipping {stock}: Already has recent data.")
                continue

            print(f"📈 Fetching data for {stock}...")
            ticker = yf.Ticker(stock)
            data = ticker.history(period="1mo", interval="1d").reset_index()

            if data.empty or "Close" not in data.columns:
                print(f"⚠️ Skipping {stock}: No Close data.")
                continue

            # MACD logic
            data["EMA_12"] = data["Close"].ewm(span=12, adjust=False).mean()
            data["EMA_26"] = data["Close"].ewm(span=26, adjust=False).mean()
            data["MACD"] = data["EMA_12"] - data["EMA_26"]
            data["Signal_line"] = data["MACD"].ewm(span=9, adjust=False).mean()
            data["Histogram"] = data["MACD"] - data["Signal_line"]
            data["stock_symbol"] = stock

            data = data.rename(columns={
                "Open": "open",
                "High": "high",
                "Low": "low",
                "Close": "close",
                "Date": "date"
            })

            final_df = data[[
                "date", "stock_symbol", "open", "high", "low", "close",
                "MACD", "Signal_line", "Histogram"
            ]]

            # Remove rows that already exist
            if stock in existing_map:
                final_df = final_df[~final_df['date'].dt.date.isin(existing_map[stock])]

            if not final_df.empty:
                with engine.connect() as conn:
                    final_df.to_sql("macd_data", conn, if_exists="append", index=False)
                    total_saved += 1
            else:
                print(f"⏩ Skipping {stock}: All rows already exist.")

            time.sleep(1)

        except Exception as stock_error:
            print(f"❌ Error for {stock}: {stock_error}")
            continue

    return f"✅ {total_saved} stocks processed and saved."

# ✅ Recalculate MACD using database data + user price
@app.route('/api/recalculate-macd', methods=['POST'])
def recalculate_macd():
    data = request.json
    stock = data.get('stock')
    date_str = data.get('date')
    price = data.get('price')

    # ✅ Input validation
    if not stock or not date_str or price is None:
        return jsonify({"error": "Missing stock, date, or price"}), 400

    try:
        custom_price = float(price)
        target_date = pd.to_datetime(date_str)

        # ✅ Use parameterized query to avoid SQL injection
        query = """
            SELECT date, close FROM macd_data 
            WHERE stock_symbol = %s 
            ORDER BY date ASC
        """
        df = pd.read_sql(query, engine, params=(stock,))
        df['date'] = pd.to_datetime(df['date'])

        if target_date not in df['date'].values:
            return jsonify({"error": f"Date {date_str} not found for stock {stock}"}), 404

        # ✅ Replace close price on target date
        df.loc[df['date'] == target_date, 'close'] = custom_price

        # ✅ Recalculate MACD values
        df["EMA_12"] = df["close"].ewm(span=12, adjust=False).mean()
        df["EMA_26"] = df["close"].ewm(span=26, adjust=False).mean()
        df["MACD"] = df["EMA_12"] - df["EMA_26"]
        df["Signal_line"] = df["MACD"].ewm(span=9, adjust=False).mean()
        df["Histogram"] = df["MACD"] - df["Signal_line"]

        row = df[df['date'] == target_date].iloc[0]

        return jsonify({
            "MACD": round(row["MACD"], 4),
            "Signal": round(row["Signal_line"], 4),
            "Histogram": round(row["Histogram"], 4)
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ✅ Test route
@app.route('/test')
def test():
    return "Flask is working ✅"

# ✅ Run local server
if __name__ == "__main__":
    app.run(debug=True, port=5000)
