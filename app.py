import os
import smtplib
from flask import Flask, request, redirect, render_template
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

app = Flask(__name__)

def send_email(recipient, subject, body):
    try:
        sender = os.environ["EMAIL_SENDER"]
        user = os.environ["EMAIL_USER"]
        password = os.environ["EMAIL_PASS"]

        msg = MIMEMultipart()
        msg["From"] = sender
        msg["To"] = recipient
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(user, password)
            server.send_message(msg)

    except Exception as e:
        print(f"EMAIL ERROR: {e}")

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        date = request.form["date"]
        email = request.form["email"]
        return redirect(f"/success?date={date}&email={email}")
    return render_template("index.html")

@app.route("/success")
def success():
    date = request.args.get("date")
    email = request.args.get("email")

    # Dummy forecast data
    forecast = f"Forecast for {date}\nMax Temp: 17.6°C\nRainfall: 55% chance of 13.9 mm"

    send_email(email, f"Forecast for {date}", forecast)

    return render_template("success.html", forecast=forecast)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
