from flask import Flask, render_template, request, redirect, url_for, jsonify  # <-- jsonify added
import pandas as pd
import stripe
import os
import smtplib
import uuid
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
from datetime import datetime, timedelta
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
import auto_reply_bot  # ✅ ADDED
from reply_utils import generate_reply  # ✅ NEW LINE

app = Flask(__name__)

# Stripe secret key from environment
stripe.api_key = os.environ.get("STRIPE_SECRET_KEY")

# Google Sheets ID
SPREADSHEET_ID = "15cUN4SWEzUYqOOJjN2G2PeGB2WA5LHH7kVNamXS9oIM"

# Log order to Google Sheets
def log_order_to_sheets(order_id, stripe_id, email, date, forecast_text):
    SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
    SERVICE_ACCOUNT_FILE = 'credentials.json'

    creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    service = build('sheets', 'v4', credentials=creds)
    sheet = service.spreadsheets()

    values = [[
        datetime.now().isoformat(),
        order_id,
        stripe_id,
        email if email else "N/A",
        date,
        forecast_text.replace('\n', ' | ')
    ]]
    body = {'values': values}
    sheet.values().append(
        spreadsheetId=SPREADSHEET_ID,
        range="A1",
        valueInputOption="USER_ENTERED",
        body=body
    ).execute()

# Send forecast email
def send_email(to_email, subject, forecast_text, transaction_id):
    msg = MIMEMultipart("related")
    msg["Subject"] = subject
    msg["From"] = f"Weather Ready <{os.environ['EMAIL_USER']}>"
    msg["To"] = to_email

    lines = forecast_text.strip().split("\n")
    max_temp = lines[0].split(":")[1].strip()
    rain_info = lines[1].split(":")[1].strip()
    forecast_date = subject.replace("Your Long-Range Weather Forecast – ", "")

    html_content = f"""
    <html>
      <body style="font-family: Arial, sans-serif; color: #333; line-height: 1.6;">
        <p>Thank you for your purchase from <strong>Weather Ready</strong>.</p>
        <p><strong>Forecast Date:</strong> {forecast_date}<br>
        <strong>Maximum Temperature:</strong> {max_temp}<br>
        <strong>Rainfall:</strong> {rain_info}</p>
        <h3 style="margin-top: 25px;">Order Details</h3>
        <p><strong>Order ID:</strong> {transaction_id}<br>
        <strong>Amount Paid:</strong> AUD $0.99<br>
        <strong>Payment Method:</strong> Stripe</p>
        <p>This email confirms the successful delivery of your long-range weather forecast and serves as your proof of purchase.</p>
        <p>Contact us: <a href="mailto:weatherreadyinfo@gmail.com">weatherreadyinfo@gmail.com</a></p>
        <p style="text-align: center; font-size: 12px; color: #999; margin-top: 30px;">
          © 2025 Weather Ready – Long-Range Weather Forecasting
        </p>
        <p style="text-align: center;">
          <img src="cid:weather_logo" alt="Weather Ready Logo" style="height: 60px;" />
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

# Homepage route
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
            success_url=url_for("success", _external=True) + f"?date={selected_date}&email={email}&session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=url_for("index", _external=True),
        )
        return redirect(session.url, code=303)

    min_date = (datetime.today() + timedelta(days=28)).strftime("%Y-%m-%d")
    return render_template("index.html", min_date=min_date)

# Forecast success route
@app.route("/success")
def success():
    selected_date = request.args.get("date")
    email = request.args.get("email")
    session_id = request.args.get("session_id")
    order_id = f"WR-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"

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
        stripe_session = stripe.checkout.Session.retrieve(session_id, expand=["payment_intent"])
        stripe_id = stripe_session.payment_intent.id
        full_order_id = f"{order_id}-{stripe_id[-6:].upper()}"

        send_email(
            to_email=email,
            subject=f"Your Long-Range Weather Forecast – {selected_date}",
            forecast_text=forecast_text,
            transaction_id=full_order_id
        )
        log_order_to_sheets(order_id, stripe_id, email, selected_date, forecast_text)
    except Exception as e:
        forecast_text += f"\n\nEMAIL ERROR: {e}"

    return render_template("result.html", forecast=forecast_text, date=selected_date)

# Other routes
@app.route("/important_delivery_information")
def important_delivery_information():
    return render_template("important_delivery_information.html")

@app.route("/legal_disclaimers")
def legal_disclaimers():
    return render_template("legal_disclaimers.html")

@app.route("/forecast_accuracy")
def forecast_accuracy():
    return render_template("forecast_accuracy.html")

# ✅ Added route to trigger auto-reply bot
@app.route("/run-bot")
def run_bot():
    try:
        auto_reply_bot.main()
        return {"status": "success"}
    except Exception as e:
        return {"status": "error", "message": str(e)}, 500

# ✅ NEW: Real-time chatbot endpoint
@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.get_json()
    subject = data.get("subject", "")
    message = data.get("message", "")
    reply = generate_reply(subject, message)
    return jsonify({"reply": reply})

# Launch
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
