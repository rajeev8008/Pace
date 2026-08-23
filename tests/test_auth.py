import os

from fastapi import HTTPException

from app.auth import SignupRequest, create_session, hash_password, verify_password, verify_session


def run_checks() -> None:
    os.environ["SESSION_SECRET"] = "test-secret"
    password_hash = hash_password("correct-password")
    assert verify_password("correct-password", password_hash)
    assert not verify_password("wrong-password", password_hash)
    signup = SignupRequest(username="rajeev", email="RAJEEV@example.com", display_name=" Rajeev ", password="example111")
    assert signup.email == "rajeev@example.com"
    assert signup.display_name == "Rajeev"
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
