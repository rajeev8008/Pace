import os
from datetime import timedelta
from unittest.mock import patch

os.environ["DATABASE_URL"] = "sqlite://"

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.api.daily_tasks import create_daily_task, delete_daily_task, list_daily_tasks, set_today
from app.database import Base, engine
from app.schemas import DailyTaskCompletionUpdate, DailyTaskCreate


def test_daily_tasks() -> None:
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        task = create_daily_task(DailyTaskCreate(title="Exercise"), 1, db)
        assert task.completed_today is False
        completed = set_today(task.id, DailyTaskCompletionUpdate(completed=True), 1, db)
        assert completed.completed_today is True
        assert len(completed.completions) == 1
        next_day = completed.completions[0] + timedelta(days=1)
        with patch("app.api.daily_tasks.today", return_value=next_day):
            tomorrow = list_daily_tasks(1, db)
            assert len(tomorrow) == 1
            assert tomorrow[0].id == task.id
            assert tomorrow[0].completed_today is False
            assert tomorrow[0].completions == completed.completions
            assert list_daily_tasks(2, db) == []
        try:
            delete_daily_task(task.id, 2, db)
        except HTTPException as error:
            assert error.status_code == 404
        else:
            raise AssertionError("Another user deleted the routine")
        reopened = set_today(task.id, DailyTaskCompletionUpdate(completed=False), 1, db)
        assert reopened.completed_today is False
        assert delete_daily_task(task.id, 1, db).status_code == 204
        assert list_daily_tasks(1, db) == []


if __name__ == "__main__":
    test_daily_tasks()
