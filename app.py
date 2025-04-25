
from flask import Flask, request, jsonify, render_template
import pandas as pd
from datetime import datetime
import os
import stripe

app = Flask(__name__)

# Load forecast data
DATA_PATH = os.path.join(os.path.dirname(__file__), "WeatherReady2025_POWERQUERY_READY.xlsx")
data = pd.read_excel(DATA_PATH, sheet_name="Sheet2")
data['Date'] = pd.to_datetime(data['Date']).dt.strftime('%Y-%m-%d')

# Stripe setup using env variable
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/success")
def success():
    return render_template("success.html")

@app.route("/cancel")
def cancel():
    return "<h1>Payment cancelled. You can return and try again.</h1>"

@app.route("/api/forecast")
def get_forecast():
    date_str = request.args.get("date")
    if not date_str:
        return jsonify({"error": "No date provided"}), 400

    row = data[data['Date'] == date_str]
    if row.empty:
        return jsonify({"error": "No forecast available for this date"}), 404

    forecast = {
        "max_temp": round(row.iloc[0]["MaxPredict2"], 1),
        "rainfall_probability": int(round(row.iloc[0]["RainfallProbability"] * 100)),
        "rainfall_amount": round(row.iloc[0]["RainfallProbable(mm)"], 1)
    }
    return jsonify(forecast)

@app.route("/create-checkout-session", methods=["POST"])
def create_checkout_session():
    data = request.get_json()
    date = data.get("date", "")

    try:
        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[{
                "price_data": {
                    "currency": "aud",
                    "product_data": {
                        "name": f"Forecast for {date}",
                    },
                    "unit_amount": 99,
                },
                "quantity": 1,
            }],
            mode="payment",
            success_url=f"https://weatherready-site.onrender.com/success?date={date}",
            cancel_url="https://weatherready-site.onrender.com/cancel",
            metadata={"date": date}
        )
        return jsonify({"id": session.id})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
