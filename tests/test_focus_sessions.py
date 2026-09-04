import os
from datetime import datetime, timezone

os.environ["DATABASE_URL"] = "sqlite://"

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.focus_sessions import format_duration, get_active_focus_session, list_focus_sessions, start_focus_session, stop_focus_session
from app.database import Base, engine
from app.models import Activity, DailyTask, FocusSession
from app.schemas import FocusSessionStart, FocusSessionStop


def test_focus_sessions() -> None:
    assert format_duration(25 * 60) == "25 minutes"
    assert format_duration(60 * 60) == "1 hour"
    assert format_duration((8 * 60 + 35) * 60) == "8 hours 35 minutes"
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        routine = DailyTask(user_id=1, title="Practice DSA", created_at=datetime.now(timezone.utc))
        db.add(routine); db.commit()
        active = start_focus_session(FocusSessionStart(category="Deep work", daily_task_id=routine.id, notes="No distractions"), 1, db)
        assert active.ended_at is None
        assert active.duration_seconds is None
        assert get_active_focus_session(1, db).id == active.id
        assert get_active_focus_session(2, db) is None

        try:
            start_focus_session(FocusSessionStart(category="Second"), 1, db)
        except HTTPException as exc:
            assert exc.status_code == 409
        else:
            raise AssertionError("A second active focus session was allowed")

        db.add(FocusSession(user_id=1, category="Bypass", started_at=datetime.now(timezone.utc), active_slot=True))
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
        else:
            raise AssertionError("The database allowed a second active focus session")

        stopped = stop_focus_session(active.id, FocusSessionStop(notes="Finished"), 1, db)
        assert stopped.ended_at is not None
        assert stopped.duration_seconds is not None and stopped.duration_seconds >= 0
        assert stopped.notes == "Finished"
        activity = db.query(Activity).filter_by(source_type="focus", source_id=active.id).one()
        assert activity.title == "Practice DSA"
        assert activity.detail.startswith("Deep work · Focused for")
        assert get_active_focus_session(1, db) is None
        assert list_focus_sessions(1, db)[0].id == active.id

        try:
            stop_focus_session(active.id, None, 1, db)
        except HTTPException as exc:
            assert exc.status_code == 409
        else:
            raise AssertionError("A completed focus session was stopped twice")

        try:
            start_focus_session(FocusSessionStart(daily_task_id=999), 1, db)
        except HTTPException as exc:
            assert exc.status_code == 404
        else:
            raise AssertionError("A missing linked daily routine was accepted")


if __name__ == "__main__":
    test_focus_sessions()
    print("Focus-session checks passed")
