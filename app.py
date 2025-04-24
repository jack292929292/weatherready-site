from flask import Flask, render_template, request
import pandas as pd
import smtplib
from email.message import EmailMessage
import os

app = Flask(__name__)

# Load your Excel sheet
def load_forecast(date_str):
    df = pd.read_excel("WeatherReady2025_POWERQUERY_READY.xlsx", sheet_name="Sheet2")
    row = df[df["DateTime"].astype(str).str.startswith(date_str)]
    if row.empty:
        return None
    temp = row["MaxPredict2"].values[0]
    prob = row["RainfallProbability"].values[0] * 100  # Convert probability to %
    mm = row["RainfallProbable(mm)"].values[0]
    return {
        "temperature": round(temp, 1),
        "probability": round(prob),
        "rainfall_mm": round(mm, 1)
    }

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        date_input = request.form.get("date")
        email = request.form.get("email")

        forecast = load_forecast(date_input)
        if not forecast:
            return "Forecast not available for the selected date."

        max_temp = forecast["temperature"]
        rain_prob = forecast["probability"]
        rain_mm = forecast["rainfall_mm"]

        # Format result text
        result_text = f"Max Temp: {max_temp}°C\n{rain_prob}% chance of {rain_mm} mm"

        # Send email
        msg = EmailMessage()
        msg["Subject"] = f"Weather Ready Forecast for {date_input}"
        msg["From"] = os.environ["EMAIL_USER"]
        msg["To"] = email
        msg.set_content(result_text)

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(os.environ["EMAIL_USER"], os.environ["EMAIL_PASS"])
            smtp.send_message(msg)

        # Render result on screen
        return f"""
            <h2>Forecast for {date_input}</h2>
            <p><strong>Max Temp:</strong> {max_temp}°C</p>
            <p><strong>Rainfall:</strong> {rain_prob}% chance of {rain_mm} mm</p>
            <a href="/">← Forecast another day</a>
        """

    return '''
        <form method="post">
            <label for="date">Enter a date (YYYY-MM-DD):</label><br>
            <input type="date" name="date" required><br><br>
            <label for="email">Enter your email address:</label><br>
            <input type="email" name="email" required><br><br>
            <button type="submit">Get Forecast</button>
        </form>
    '''

if __name__ == "__main__":
    app.run(debug=True)
