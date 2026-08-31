import os
from unittest.mock import patch

os.environ["DATABASE_URL"] = "sqlite://"

from sqlalchemy.orm import Session

from app.auth import _oauth_owner, create_session, oauth_providers, require_auth
from app.database import Base, engine


def run_checks() -> None:
    os.environ["SESSION_SECRET"] = "test-secret"
    with patch.dict(os.environ, {"GITHUB_CLIENT_ID": "", "GITHUB_CLIENT_SECRET": "", "GOOGLE_CLIENT_ID": "", "GOOGLE_CLIENT_SECRET": ""}):
        assert oauth_providers() == {"github": False, "google": False}
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        first = _oauth_owner(db, "github", "123", "first@example.com", "First", "first")
        assert first.github_id == "123"
        assert first.password_hash is None
        assert _oauth_owner(db, "google", "abc", "first@example.com", "First", "first").id == first.id

        second = _oauth_owner(db, "github", "456", "second@example.com", "Second", "second")
        assert second.id != first.id
        assert _oauth_owner(db, "google", "def", "second@example.com", "Second", "second").id == second.id
        assert require_auth(create_session(first.id), db) == first.id
        assert require_auth(create_session(second.id), db) == second.id


if __name__ == "__main__":
    run_checks()
    print("OAuth checks passed")
