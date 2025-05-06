from flask import Flask, render_template, request, redirect, url_for
import os
import smtplib
from email.message import EmailMessage
import pandas as pd

app = Flask(__name__)

# Load spreadsheet once
DATA_PATH = "WeatherReady2025_POWERQUERY_READY.xlsx"
df = pd.read_excel(DATA_PATH, sheet_name="Sheet2")

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        selected_date = request.form["date"]
        email = request.form["email"]
        return redirect(url_for("success", date=selected_date, email=email))
    return render_template("index.html")

@app.route("/success")
def success():
    date = request.args.get("date")
    email = request.args.get("email")

    try:
        forecast_row = df.loc[df["Date"] == pd.to_datetime(date)].iloc[0]
        max_temp = forecast_row["MaxPredict2"]
        rainfall_prob = forecast_row["RainfallProbability"]
        rainfall_mm = forecast_row["RainfallProbable(mm)"]
    except:
        return f"No forecast found for {date}"

    message_body = f"Forecast for {date}\nMax Temp: {max_temp}°C\nRainfall: {rainfall_prob}% chance of {rainfall_mm} mm"

    try:
        send_email(email, "Weather Forecast", message_body)
        email_status = "Email sent."
    except Exception as e:
        email_status = f"EMAIL ERROR: {e}"

    return f"{message_body}\n\n{email_status}"

def send_email(to_email, subject, body):
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = os.environ["EMAIL_SENDER"]
    msg["To"] = to_email
    msg.set_content(body)

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(os.environ["EMAIL_USER"], os.environ["EMAIL_PASS"])
        smtp.send_message(msg)

if __name__ == "__main__":
    app.run(debug=False, port=10000, host="0.0.0.0")
