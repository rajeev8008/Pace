import os

from fastapi import HTTPException

from app.auth import create_session, verify_session


def run_checks() -> None:
    os.environ["SESSION_SECRET"] = "test-secret"
    token = create_session("rajeev")
    assert verify_session(token) == "rajeev"
    try:
        verify_session(token + "changed")
    except HTTPException as exc:
        assert exc.status_code == 401
    else:
        raise AssertionError("A modified session token was accepted")


if __name__ == "__main__":
    run_checks()
    print("Authentication checks passed")
