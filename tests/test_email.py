import json
import os
from unittest.mock import patch

from app.services.email_service import send_email


def run_checks() -> None:
    with patch.dict(os.environ, {"RESEND_API_KEY": "test-key", "RESEND_FROM": "Pace <pace@example.com>"}), patch("app.services.email_service.urlopen") as send:
        send.return_value.__enter__.return_value = object()
        send_email("owner@example.com", "Reminder", "Do the thing")
        request = send.call_args.args[0]
        assert request.get_header("Authorization") == "Bearer test-key"
        assert json.loads(request.data) == {"from": "Pace <pace@example.com>", "to": ["owner@example.com"], "subject": "Reminder", "text": "Do the thing"}


if __name__ == "__main__":
    run_checks()
    print("Email checks passed")
