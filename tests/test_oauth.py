import os
from unittest.mock import patch

os.environ["DATABASE_URL"] = "sqlite://"

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.auth import _oauth_owner, oauth_providers
from app.api.tasks import create_task, list_tasks
from app.database import Base, engine
from app.schemas import TaskCreate


def run_checks() -> None:
    with patch.dict(os.environ, {"GITHUB_CLIENT_ID": "", "GITHUB_CLIENT_SECRET": "", "GOOGLE_CLIENT_ID": "", "GOOGLE_CLIENT_SECRET": ""}):
        assert oauth_providers() == {"github": False, "google": False}
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        owner = _oauth_owner(db, "github", "123", "owner@example.com", "Owner", "owner")
        assert owner.github_id == "123"
        assert owner.password_hash is None
        assert _oauth_owner(db, "google", "abc", "owner@example.com", "Owner", "owner").google_id == "abc"
        friend = _oauth_owner(db, "github", "456", "friend@example.com", "Friend", "friend")
        assert friend.id != owner.id
        assert friend.email == "friend@example.com"
        assert _oauth_owner(db, "google", "xyz", "friend@example.com", "Friend", "friend").id == friend.id
        create_task(TaskCreate(title="Owner private task"), owner.id, db)
        create_task(TaskCreate(title="Friend private task"), friend.id, db)
        assert [task.title for task in list_tasks(owner.id, db)] == ["Owner private task"]
        assert [task.title for task in list_tasks(friend.id, db)] == ["Friend private task"]


if __name__ == "__main__":
    run_checks()
    print("OAuth checks passed")
