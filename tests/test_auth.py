import os

from fastapi import HTTPException
from fastapi import Response

from app.auth import SignupRequest, _set_session, create_session, hash_password, verify_password, verify_session
from app.models import User


def run_checks() -> None:
    os.environ["SESSION_SECRET"] = "test-secret"
    password_hash = hash_password("correct-password")
    assert verify_password("correct-password", password_hash)
    assert not verify_password("wrong-password", password_hash)
    signup = SignupRequest(username="NewUser", email="USER@Example.com", display_name=" New User ", password="strong-password")
    assert signup.username == "NewUser"
    assert signup.email == "user@example.com"
    assert signup.display_name == "New User"
    token = create_session(1)
    assert token.count(".") == 2
    assert verify_session(token) == 1
    try:
        verify_session(token + "changed")
    except HTTPException as exc:
        assert exc.status_code == 401
    else:
        raise AssertionError("A modified session token was accepted")
    os.environ["COOKIE_SECURE"] = "true"
    response = Response()
    _set_session(response, User(id=1, username="rajeev", email="rajeev@example.com", display_name="Rajeev"))
    assert "HttpOnly" in response.headers["set-cookie"]
    assert "SameSite=strict" in response.headers["set-cookie"]
    assert "Secure" in response.headers["set-cookie"]


if __name__ == "__main__":
    run_checks()
    print("Authentication checks passed")
