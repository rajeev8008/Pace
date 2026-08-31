import os
import smtplib
from email.message import EmailMessage


def send_email(to: str | None, subject: str, body: str) -> None:
    host = os.getenv("SMTP_HOST")
    if not host:
        print(f"[Email] To: {to or '(not configured)'}\nSubject: {subject}\n\n{body}")
        return
    if not to:
        raise ValueError("preference email is not configured")

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
