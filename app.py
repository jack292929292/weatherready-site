
from flask import Flask, request, jsonify, render_template
import pandas as pd
from datetime import datetime
import os

app = Flask(__name__)

# Load your Excel spreadsheet once when the app starts
DATA_PATH = os.path.join(os.path.dirname(__file__), "WeatherReady2025_POWERQUERY_READY.xlsx")
data = pd.read_excel(DATA_PATH, sheet_name="Sheet2")

# Make sure 'Date' column is in datetime.date format
data['Date'] = pd.to_datetime(data['Date']).dt.date

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/success")
def success():
    return render_template("success.html")

@app.route("/api/forecast")
def get_forecast():
    date_str = request.args.get("date")
    if not date_str:
        return jsonify({"error": "No date provided"}), 400

    try:
        requested_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        return jsonify({"error": "Invalid date format"}), 400

    row = data[data['Date'] == requested_date]
    if row.empty:
        return jsonify({"error": "No forecast available for this date"}), 404

    forecast = {
        "max_temp": row.iloc[0]["MaxPredict2"],
        "rainfall_probability": row.iloc[0]["RainfallProbability"],
        "rainfall_amount": row.iloc[0]["RainfallProbable(mm)"]
    }
    return jsonify(forecast)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000, debug=True)

