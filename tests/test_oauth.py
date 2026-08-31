import os
from unittest.mock import patch

os.environ["DATABASE_URL"] = "sqlite://"

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.auth import LoginRequest, _oauth_owner, create_session, hash_password, login, oauth_providers, require_auth
from app.database import Base, engine
from app.models import User
from fastapi import Response
from datetime import datetime, timezone


def run_checks() -> None:
    os.environ["SESSION_SECRET"] = "test-secret"
    with patch.dict(os.environ, {"GITHUB_CLIENT_ID": "", "GITHUB_CLIENT_SECRET": "", "GOOGLE_CLIENT_ID": "", "GOOGLE_CLIENT_SECRET": ""}):
        assert oauth_providers() == {"github": False, "google": False}
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        owner = _oauth_owner(db, "github", "123", "owner@example.com", "Owner", "owner")
        assert owner.github_id == "123"
        assert owner.password_hash is None
        assert _oauth_owner(db, "google", "abc", "owner@example.com", "Owner", "owner").google_id == "abc"
        try:
            _oauth_owner(db, "github", "456", "friend@example.com", "Friend", "friend")
        except HTTPException as exc:
            assert exc.status_code == 403
        else:
            raise AssertionError("An OAuth identity with a different email took over the owner account")
        db.add(User(id=2, username="friend", email="friend@example.com", display_name="Friend", password_hash=hash_password("friend-password"), created_at=datetime.now(timezone.utc)))
        db.commit()
        try:
            login(LoginRequest(username="friend", password="friend-password"), Response(), db)
        except HTTPException as exc:
            assert exc.status_code == 401
        else:
            raise AssertionError("A non-owner account logged in")
        try:
            require_auth(create_session(2), db)
        except HTTPException as exc:
            assert exc.status_code == 401
        else:
            raise AssertionError("A non-owner session was accepted")


if __name__ == "__main__":
    run_checks()
    print("OAuth checks passed")
