import os
import base64
import openai
from email.mime.text import MIMEText
from datetime import datetime
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

openai.api_key = os.environ["OPENAI_API_KEY"]
EMAIL_ADDRESS = os.environ["EMAIL_ADDRESS"]
SPREADSHEET_ID = os.environ["SHEET_ID"]

ALLOWED_SENDERS = ["@gmail.com", "@mycompany.com"]  # 🔒 Only reply to these domains

def load_gmail_service():
    scopes = ["https://www.googleapis.com/auth/gmail.modify"]
    creds = Credentials.from_authorized_user_file("token.json", scopes)
    return build("gmail", "v1", credentials=creds)

def get_unread_emails(service):
    result = service.users().messages().list(userId="me", labelIds=["INBOX"], q="is:unread").execute()
    return result.get("messages", [])

def extract_email(service, msg_id):
    msg = service.users().messages().get(userId="me", id=msg_id, format="full").execute()
    headers = {h["name"]: h["value"] for h in msg["payload"]["headers"]}
    subject = headers.get("Subject", "(No subject)")
    sender = headers.get("From", "")
    body = ""
    for part in msg["payload"].get("parts", []):
        if part["mimeType"] == "text/plain":
            data = part["body"]["data"]
            body = base64.urlsafe_b64decode(data).decode("utf-8")
            break
    return sender, subject, body

def is_approved_sender(sender):
    return any(sender.lower().endswith(domain) for domain in ALLOWED_SENDERS)

def generate_reply(subject, body):
    prompt = f"""You are the automated support assistant for Weather Ready, a long-range weather forecasting service in Perth.
Respond clearly and helpfully.

Subject: {subject}
Email: {body}

Reply:"""

    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.4,
    )
    return response.choices[0].message.content.strip()

def send_email(service, to_email, subject, reply_text):
    msg = MIMEText(reply_text)
    msg["to"] = to_email
    msg["from"] = EMAIL_ADDRESS
    msg["subject"] = f"Re: {subject}"
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    return service.users().messages().send(userId="me", body={"raw": raw}).execute()

def mark_as_read(service, msg_id):
    service.users().messages().modify(userId="me", id=msg_id, body={"removeLabelIds": ["UNREAD"]}).execute()

def log_to_sheets(sender, subject, body, reply_text):
    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = Credentials.from_authorized_user_file("token.json", scopes)
    sheet = build("sheets", "v4", credentials=creds).spreadsheets()

    now = datetime.now().isoformat()
    values = [[now, sender, subject, body.replace("\n", " "), reply_text.replace("\n", " ")]]
    body = {"values": values}
    sheet.values().append(
        spreadsheetId=SPREADSHEET_ID,
        range="A1",
        valueInputOption="USER_ENTERED",
        body=body
    ).execute()

def main():
    print("📡 Weather Ready AutoBot Running...")
    service = load_gmail_service()
    messages = get_unread_emails(service)

    if not messages:
        print("✅ Inbox clear.")
        return

    for msg in messages:
        msg_id = msg["id"]
        sender, subject, body = extract_email(service, msg_id)
        print(f"\n📨 From: {sender} | Subject: {subject}")

        if not is_approved_sender(sender):
            print("⛔ Skipping unapproved sender.")
            continue

        try:
            reply = generate_reply(subject, body)
            send_email(service, sender, subject, reply)
            mark_as_read(service, msg_id)
            log_to_sheets(sender, subject, body, reply)
            print("✅ Replied + Logged.")
        except Exception as e:
            print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()
