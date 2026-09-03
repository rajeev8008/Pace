import os
from unittest.mock import patch

from fastapi import HTTPException

from app.main import health, run_jobs


def run_checks() -> None:
    assert health() == {"status": "ok"}
    with patch.dict(os.environ, {"CRON_SECRET": "test-cron-secret"}), patch("app.main.run_once", return_value=3):
        assert run_jobs("Bearer test-cron-secret") == {"processed": 3}
        try:
            run_jobs("Bearer wrong-secret")
        except HTTPException as exc:
            assert exc.status_code == 401
        else:
            raise AssertionError("The hosted job endpoint accepted an invalid secret")


if __name__ == "__main__":
    run_checks()
    print("Hosting checks passed")
