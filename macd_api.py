from flask import Flask, request, jsonify
import pandas as pd
import pymysql
from sqlalchemy import create_engine
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# MySQL connection settings
db_user = "root"
db_password = ""
db_host = "localhost"
db_name = "stock_data"

engine = create_engine(f"mysql+pymysql://{db_user}:{db_password}@{db_host}/{db_name}")

@app.route('/api/recalculate-macd', methods=['POST'])
def recalculate_macd():
    data = request.json
    stock = data['stock']
    date = data['date']
    custom_price = float(data['price'])

    try:
        df = pd.read_sql(f"SELECT date, close FROM macd_data WHERE stock_symbol = '{stock}' ORDER BY date ASC", engine)
        df['date'] = pd.to_datetime(df['date'])
        df.loc[df['date'] == pd.to_datetime(date), 'close'] = custom_price

        df["EMA_12"] = df["close"].ewm(span=12, adjust=False).mean()
        df["EMA_26"] = df["close"].ewm(span=26, adjust=False).mean()
        df["MACD"] = df["EMA_12"] - df["EMA_26"]
        df["Signal"] = df["MACD"].ewm(span=9, adjust=False).mean()
        df["Histogram"] = df["MACD"] - df["Signal"]

        row = df[df['date'] == pd.to_datetime(date)].iloc[0]
        return jsonify({
            "MACD": round(row["MACD"], 4),
            "Signal": round(row["Signal"], 4),
            "Histogram": round(row["Histogram"], 4)
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True, port=5000)
