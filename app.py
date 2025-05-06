from flask import Flask, render_template, request, redirect, url_for
import os
import smtplib
from email.mime.text import MIMEText
import pandas as pd

app = Flask(__name__)

# Load your forecast data from Excel
df = pd.read_excel("WeatherReady2025_POWERQUERY_READY.xlsx", sheet_name="Sheet2")
df['Date'] = pd.to_datetime(df['Date'])

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        date_str = request.form.get("date")
        email = request.form.get("email")
        try:
            date_obj = pd.to_datetime(date_str).normalize()
            forecast_row = df[df['Date'] == date_obj]
            if forecast_row.empty:
                return render_template("index.html", error="No forecast found for that date.")
            max_temp = forecast_row["MaxPredict2"].values[0]
            rain_prob = forecast_row["RainfallProbability"].values[0]
            rain_amt = forecast_row["RainfallProbable(mm)"].values[0]

            forecast = f"Forecast for {date_str}\nMax Temp: {max_temp}°C\nRainfall: {rain_prob}% chance of {rain_amt} mm"

            send_forecast_email(email, forecast)

            return redirect(url_for("success", date=date_str, email=email))
        except Exception as e:
            return render_template("index.html", error=f"Error processing request: {e}")
    return render_template("index.html")

@app.route("/success")
def success():
    date = request.args.get("date")
    email = request.args.get("email")
    forecast_row = df[df['Date'] == pd.to_datetime(date).normalize()]
    if forecast_row.empty:
        return "Forecast not found."

    max_temp = forecast_row["MaxPredict2"].values[0]
    rain_prob = forecast_row["RainfallProbability"].values[0]
    rain_amt = forecast_row["RainfallProbable(mm)"].values[0]

    return f"""
    Forecast for {date}<br>
    Max Temp: {max_temp}°C<br>
    Rainfall: {rain_prob}% chance of {rain_amt} mm<br>
    <br>
    Email sent to: {email}
    """

def send_forecast_email(recipient_email, forecast_text):
    try:
        sender_email = os.environ["EMAIL_SENDER"]
        password = os.environ["EMAIL_PASS"]
    except KeyError as ke:
        print(f"EMAIL ERROR: {ke}")
        return

    msg = MIMEText(forecast_text)
    msg['Subject'] = "Your Weather Ready Forecast"
    msg['From'] = sender_email
    msg['To'] = recipient_email

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(sender_email, password)
            server.sendmail(sender_email, recipient_email, msg.as_string())
            print(f"Email sent to {recipient_email}")
    except Exception as e:
        print(f"EMAIL SEND FAILED: {e}")

if __name__ == "__main__":
    app.run(debug=False, port=10000)
