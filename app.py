from flask import Flask, request, render_template, redirect, url_for
import pandas as pd
import stripe
import os
import smtplib
from email.mime.text import MIMEText
from datetime import datetime

app = Flask(__name__)

stripe.api_key = os.environ.get("STRIPE_SECRET_KEY")

def send_email(to_email, subject, body):
    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = f"Weather Ready <{os.environ['EMAIL_USER']}>"
    msg["To"] = to_email

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(os.environ["EMAIL_USER"], os.environ["EMAIL_PASS"])
        server.send_message(msg)

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        selected_date = request.form["forecast_date"]
        email = request.form["email"]

        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[{
                "price_data": {
                    "currency": "aud",
                    "product_data": {
                        "name": f"Forecast for {selected_date}",
                    },
                    "unit_amount": 99,
                },
                "quantity": 1,
            }],
            mode="payment",
            success_url=url_for("success", _external=True) + f"?date={selected_date}&email={email}",
            cancel_url=url_for("index", _external=True),
        )
        return redirect(session.url, code=303)
    return render_template("index.html")

@app.route("/success")
def success():
    selected_date = request.args.get("date")
    email = request.args.get("email")
    try:
        df = pd.read_excel("WeatherReady2025_POWERQUERY_READY.xlsx", sheet_name="Sheet2")
        forecast_row = df[df["Date"] == selected_date].iloc[0]
        max_temp = forecast_row["MaxPredict2"]
        rain_prob = forecast_row["RainfallProbability"] * 100
        rain_amt = forecast_row["RainfallProbable(mm)"]
        forecast_text = f"Max Temp: {max_temp:.1f}°C\nRainfall: {rain_prob:.0f}% chance of {rain_amt:.1f} mm"
    except Exception as e:
        forecast_text = f"Forecast not available for the selected date.\n\nDATA ERROR: {e}"

    try:
        send_email(
            to_email=email,
            subject=f"Forecast for {selected_date}",
            body=forecast_text
        )
    except Exception as e:
        error_msg = f"EMAIL ERROR: {e}"
        print(error_msg)
        forecast_text += f"\n\n{error_msg}"

    return render_template("result.html", forecast=forecast_text, date=selected_date)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))

