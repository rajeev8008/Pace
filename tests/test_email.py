import os
from unittest.mock import patch

from app.services.email_service import send_email


def run_checks() -> None:
    settings = {
        "SMTP_HOST": "smtp.gmail.com",
        "SMTP_PORT": "587",
        "SMTP_USERNAME": "pace@example.com",
        "SMTP_PASSWORD": "app-password",
        "SMTP_FROM": "Pace <pace@example.com>",
        "SMTP_STARTTLS": "true",
    }
    with patch.dict(os.environ, settings), patch("app.services.email_service.smtplib.SMTP") as smtp_class:
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
