from flask import Flask, render_template, request, redirect, url_for
import pandas as pd
import stripe
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
from datetime import datetime

app = Flask(__name__)

# Set up Stripe API key
stripe.api_key = os.environ.get("STRIPE_SECRET_KEY")

# Function to send email
def send_email(to_email, subject, forecast_text, transaction_id):
    msg = MIMEMultipart("related")
    msg["Subject"] = subject
    msg["From"] = f"Weather Ready <{os.environ['EMAIL_USER']}>"
    msg["To"] = to_email

    # Parse forecast details
    lines = forecast_text.strip().split("\n")
    max_temp = lines[0].split(":")[1].strip()
    rain_info = lines[1].split(":")[1].strip()
    forecast_date = subject.replace("Your Long-Range Weather Forecast – ", "")

    html_content = f"""
    <html>
      <body style="font-family: Arial, sans-serif; color: #333; line-height: 1.6;">
        <p>Thank you for your purchase from <strong>Weather Ready</strong>.</p>

        <p>Below is your custom forecast for the selected date:</p>

        <p><strong>Forecast Date:</strong> {forecast_date}<br>
        <strong>Maximum Temperature:</strong> {max_temp}<br>
        <strong>Rainfall:</strong> {rain_info}</p>

        <h3 style="margin-top: 25px;">Payment Details</h3>
        <p><strong>Amount Paid:</strong> AUD $0.99<br>
        <strong>Payment Method:</strong> Stripe<br>
        <strong>Transaction ID:</strong> {transaction_id}</p>

        <p>This email confirms the successful delivery of your long-range weather forecast and serves as your proof of purchase.
        Please retain this message for your records.</p>

        <p>If you have any questions, contact us at <a href="mailto:weatherreadyinfo@gmail.com">weatherreadyinfo@gmail.com</a>.</p>

        <p style="text-align: center; font-size: 12px; color: #999; margin-top: 30px;">
          © 2025 Weather Ready – Long-Range Weather Forecasting
        </p>
        <p style="text-align: center;">
          <img src="cid:weather_logo" alt="Weather Ready Logo" style="height: 60px; margin-top: 5px;" />
        </p>
      </body>
    </html>
    """

    msg_alt = MIMEMultipart("alternative")
    msg.attach(msg_alt)

    msg_alt.attach(MIMEText(forecast_text, "plain"))
    msg_alt.attach(MIMEText(html_content, "html"))

    with open("weather_ready_logo.png", "rb") as img:
        mime_img = MIMEImage(img.read(), _subtype="png")
        mime_img.add_header("Content-ID", "<weather_logo>")
        mime_img.add_header("Content-Disposition", "inline", filename="weather_ready_logo.png")
        msg.attach(mime_img)

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(os.environ["EMAIL_USER"], os.environ["EMAIL_PASS"])
        server.send_message(msg)

# Route for the main page (index.html)
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

# Route for important delivery information
@app.route("/important_delivery_information")
def important_delivery_information():
    return render_template("important_delivery_information.html")

# Route for legal disclaimers page
@app.route("/legal_disclaimers")
def legal_disclaimers():
    return render_template("legal_disclaimers.html")

# Route for forecast accuracy table page
@app.route("/forecast_accuracy")
def forecast_accuracy():
    return render_template("forecast_accuracy.html")

# Route for the success page after Stripe payment
@app.route("/success")
def success():
    selected_date = request.args.get("date")
    email = request.args.get("email")

    try:
        # Read forecast data from the Excel file
        df = pd.read_excel("WeatherReady2025_POWERQUERY_READY.xlsx", sheet_name="Sheet2")
        forecast_row = df[df["Date"] == selected_date].iloc[0]
        max_temp = forecast_row["MaxPredict2"]
        rain_prob = forecast_row["RainfallProbability"] * 100
        rain_amt = forecast_row["RainfallProbable(mm)"]
        forecast_text = f"Max Temp: {max_temp:.1f}°C\nRainfall: {rain_prob:.0f}% chance of {rain_amt:.1f} mm"
    except Exception as e:
        forecast_text = f"Forecast not available for the selected date.\n\nDATA ERROR: {e}"

    try:
        transaction_id = "pi_test_transaction_000000"
        send_email(
            to_email=email,
            subject=f"Your Long-Range Weather Forecast – {selected_date}",
            forecast_text=forecast_text,
            transaction_id=transaction_id
        )
    except Exception as e:
        error_msg = f"EMAIL ERROR: {e}"
        print(error_msg)
        forecast_text += f"\n\n{error_msg}"

    return render_template("result.html", forecast=forecast_text, date=selected_date)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
