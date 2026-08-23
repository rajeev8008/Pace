import os
from unittest.mock import patch

os.environ["DATABASE_URL"] = "sqlite://"

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.auth import _oauth_owner, oauth_providers
from app.database import Base, engine


def run_checks() -> None:
    with patch.dict(os.environ, {"GITHUB_CLIENT_ID": "", "GITHUB_CLIENT_SECRET": "", "GOOGLE_CLIENT_ID": "", "GOOGLE_CLIENT_SECRET": ""}):
        assert oauth_providers() == {"github": False, "google": False}
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        owner = _oauth_owner(db, "github", "123", "owner@example.com", "Owner", "owner")
        assert owner.github_id == "123"
        assert owner.password_hash is None
        assert _oauth_owner(db, "google", "abc", "owner@example.com", "Owner", "owner").google_id == "abc"
        try:
            _oauth_owner(db, "github", "456", "attacker@example.com", "Other", "other")
        except HTTPException as exc:
            assert exc.status_code == 403
        else:
            raise AssertionError("An OAuth identity with a different email took over the owner account")


if __name__ == "__main__":
    run_checks()
    print("OAuth checks passed")
