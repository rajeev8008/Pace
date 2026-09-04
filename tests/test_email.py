import os
import json
from unittest.mock import patch

from app.services.email_service import send_email


def run_checks() -> None:
    resend = {"RESEND_API_KEY": "re_test", "RESEND_FROM": "Pace <updates@pace.example>"}
    with patch.dict(os.environ, resend, clear=True), patch("app.services.email_service.urlopen") as send:
        send.return_value.__enter__.return_value.status = 200
        send_email("user@example.com", "Keep going", "You completed three tasks.")
        request = send.call_args.args[0]
        assert request.full_url == "https://api.resend.com/emails"
        assert request.headers["Authorization"] == "Bearer re_test"
        assert json.loads(request.data) == {
            "from": "Pace <updates@pace.example>",
            "to": ["user@example.com"],
            "subject": "Keep going",
            "text": "You completed three tasks.",
        }

    settings = {
        "SMTP_HOST": "smtp.gmail.com",
        "SMTP_PORT": "587",
        "SMTP_USERNAME": "pace@example.com",
        "SMTP_PASSWORD": "app-password",
        "SMTP_FROM": "Pace <pace@example.com>",
        "SMTP_STARTTLS": "true",
    }
    with patch.dict(os.environ, settings, clear=True), patch("app.services.email_service.smtplib.SMTP") as smtp_class:
        smtp = smtp_class.return_value.__enter__.return_value
        send_email("user@example.com", "Keep going", "You completed three tasks.")
        smtp.starttls.assert_called_once_with()
        smtp.login.assert_called_once_with("pace@example.com", "app-password")
        message = smtp.send_message.call_args.args[0]
        assert message["To"] == "user@example.com"
        assert message["From"] == "Pace <pace@example.com>"


if __name__ == "__main__":
    run_checks()
    print("Email checks passed")
