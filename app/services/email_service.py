import json
import os
import smtplib
from email.message import EmailMessage
from urllib.request import Request, urlopen


def send_email(to: str | None, subject: str, body: str) -> None:
    if not to:
        raise ValueError("preference email is not configured")

    api_key = os.getenv("RESEND_API_KEY")
    if api_key:
        sender = os.getenv("RESEND_FROM")
        if not sender:
            raise ValueError("RESEND_FROM is not configured")
        request = Request(
            "https://api.resend.com/emails",
            data=json.dumps({"from": sender, "to": [to], "subject": subject, "text": body}).encode(),
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(request, timeout=30):
            return

    host = os.getenv("SMTP_HOST")
    if not host:
        print(f"[Email] To: {to}\nSubject: {subject}\n\n{body}")
        return

    message = EmailMessage()
    message["From"] = os.getenv("SMTP_FROM") or os.getenv("SMTP_USERNAME")
    message["To"] = to
    message["Subject"] = subject
    message.set_content(body)
    with smtplib.SMTP(host, int(os.getenv("SMTP_PORT", "587")), timeout=30) as smtp:
        if os.getenv("SMTP_STARTTLS", "true").lower() == "true":
            smtp.starttls()
        username = os.getenv("SMTP_USERNAME")
        if username:
            smtp.login(username, os.environ["SMTP_PASSWORD"])
        smtp.send_message(message)
