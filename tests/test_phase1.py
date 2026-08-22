import os
from datetime import timedelta

os.environ["DATABASE_URL"] = "sqlite://"

from sqlalchemy.orm import Session
from pydantic import ValidationError

from app.api.tasks import create_task, delete_task, get_task, list_tasks, update_task
from app.database import Base, engine
from app.models import TaskStatus
from app.schemas import TaskCreate, TaskUpdate


def test_phase1_crud() -> None:
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        payload = TaskCreate(
            title="  Study Kafka  ",
            due_at="2026-08-23T21:00:00+05:30",
        )
        assert payload.due_at is not None
        assert payload.due_at.utcoffset() == timedelta(0)
        try:
            TaskCreate(title="Invalid timestamp", due_at="2026-08-23T21:00:00")
        except ValidationError:
            pass
        else:
            raise AssertionError("naive timestamp was accepted")
        created = create_task(payload, db)
        assert created.title == "Study Kafka"
        assert get_task(created.id, db) is created
        assert list_tasks(db) == [created]

        updated = update_task(
            created.id,
            TaskUpdate(status=TaskStatus.COMPLETED),
            db,
        )
        assert updated.completed_at is not None
        assert delete_task(created.id, db).status_code == 204
        assert list_tasks(db) == []


if __name__ == "__main__":
    test_phase1_crud()
