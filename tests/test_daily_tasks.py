import os

os.environ["DATABASE_URL"] = "sqlite://"

from sqlalchemy.orm import Session

from app.api.daily_tasks import create_daily_task, delete_daily_task, list_daily_tasks, set_today
from app.database import Base, engine
from app.schemas import DailyTaskCompletionUpdate, DailyTaskCreate


def test_daily_tasks() -> None:
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        task = create_daily_task(DailyTaskCreate(title="Exercise"), db)
        assert task.completed_today is False
        completed = set_today(task.id, DailyTaskCompletionUpdate(completed=True), db)
        assert completed.completed_today is True
        assert len(completed.completions) == 1
        reopened = set_today(task.id, DailyTaskCompletionUpdate(completed=False), db)
        assert reopened.completed_today is False
        assert delete_daily_task(task.id, db).status_code == 204
        assert list_daily_tasks(db) == []


if __name__ == "__main__":
    test_daily_tasks()
