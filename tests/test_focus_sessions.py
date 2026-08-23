import os
from datetime import datetime, timezone

os.environ["DATABASE_URL"] = "sqlite://"

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.focus_sessions import get_active_focus_session, list_focus_sessions, start_focus_session, stop_focus_session
from app.database import Base, engine
from app.models import FocusSession, Task
from app.schemas import FocusSessionStart, FocusSessionStop


def test_focus_sessions() -> None:
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        task = Task(title="Write tests", created_at=datetime.now(timezone.utc))
        db.add(task); db.commit()
        active = start_focus_session(FocusSessionStart(category="Deep work", task_id=task.id, notes="No distractions"), db)
        assert active.ended_at is None
        assert active.duration_seconds is None
        assert get_active_focus_session(db).id == active.id

        try:
            start_focus_session(FocusSessionStart(category="Second"), db)
        except HTTPException as exc:
            assert exc.status_code == 409
        else:
            raise AssertionError("A second active focus session was allowed")

        db.add(FocusSession(category="Bypass", started_at=datetime.now(timezone.utc), active_slot=True))
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
        else:
            raise AssertionError("The database allowed a second active focus session")

        stopped = stop_focus_session(active.id, FocusSessionStop(notes="Finished"), db)
        assert stopped.ended_at is not None
        assert stopped.duration_seconds is not None and stopped.duration_seconds >= 0
        assert stopped.notes == "Finished"
        assert get_active_focus_session(db) is None
        assert list_focus_sessions(db)[0].id == active.id

        try:
            stop_focus_session(active.id, None, db)
        except HTTPException as exc:
            assert exc.status_code == 409
        else:
            raise AssertionError("A completed focus session was stopped twice")

        try:
            start_focus_session(FocusSessionStart(task_id=999), db)
        except HTTPException as exc:
            assert exc.status_code == 404
        else:
            raise AssertionError("A missing linked task was accepted")


if __name__ == "__main__":
    test_focus_sessions()
    print("Focus-session checks passed")
