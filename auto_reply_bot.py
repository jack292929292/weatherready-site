import os
import base64
import openai
from email.mime.text import MIMEText
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

# 🔐 Environment variables required:
# OPENAI_API_KEY — your OpenAI key
# EMAIL_ADDRESS — your Gmail address (e.g., weatherreadyinfo@gmail.com)

openai.api_key = os.environ["OPENAI_API_KEY"]
EMAIL_ADDRESS = os.environ["EMAIL_ADDRESS"]

def load_gmail_service():
    """Authenticate and return Gmail API service"""
    SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]
    if not os.path.exists("token.json"):
        raise FileNotFoundError("❌ token.json not found. Run OAuth setup first.")
    creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    return build("gmail", "v1", credentials=creds)

def get_unread_emails(service):
    """Fetch unread messages in inbox"""
    result = service.users().messages().list(userId="me", labelIds=["INBOX"], q="is:unread").execute()
    return result.get("messages", [])

def extract_email_details(service, msg_id):
    """Extract sender, subject, and body from message ID"""
    msg = service.users().messages().get(userId="me", id=msg_id, format="full").execute()
    headers = {h["name"]: h["value"] for h in msg["payload"]["headers"]}
    subject = headers.get("Subject", "(No subject)")
    sender = headers.get("From", "")
    parts = msg["payload"].get("parts", [])
    body = ""
    for part in parts:
        if part["mimeType"] == "text/plain":
            body_data = part["body"]["data"]
            body = base64.urlsafe_b64decode(body_data).decode("utf-8")
            break
    return sender, subject, body

def generate_reply(subject, body):
    """Call ChatGPT API to generate reply"""
    prompt = f"""You are the automated support assistant for Weather Ready, a long-range weather forecasting service in Perth.
You are friendly, accurate, and concise. Use clear formatting.
If a question is unclear, ask for clarification. If someone asks about forecast accuracy, pricing, or why a forecast isn't working, provide helpful responses in plain English.

Email Subject: {subject}
Email Body: {body}

Reply:"""

    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.4,
    )
    return response.choices[0].message.content.strip()

def send_email(service, to_email, subject, reply_text):
    """Send an email reply"""
    msg = MIMEText(reply_text)
    msg["to"] = to_email
    msg["from"] = EMAIL_ADDRESS
    msg["subject"] = f"Re: {subject}"

    raw_msg = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    body = {"raw": raw_msg}
    sent = service.users().messages().send(userId="me", body=body).execute()
    return sent.get("id")

def mark_email_as_read(service, msg_id):
    """Remove 'UNREAD' label"""
    service.users().messages().modify(
        userId="me", id=msg_id, body={"removeLabelIds": ["UNREAD"]}
    ).execute()

def main():
    print("📡 Weather Ready Auto Reply Bot Active...")
    service = load_gmail_service()
    messages = get_unread_emails(service)

    if not messages:
        print("✅ Inbox clear. No new messages.")
        return

    for msg in messages:
        msg_id = msg["id"]
        sender, subject, body = extract_email_details(service, msg_id)
        print(f"\n📨 New message from {sender} | Subject: {subject}")

        try:
            reply = generate_reply(subject, body)
            send_email(service, sender, subject, reply)
            mark_email_as_read(service, msg_id)
            print("✅ Reply sent and email marked as read.")
        except Exception as e:
            print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()
