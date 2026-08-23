from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Activity, FocusSession, Task
from app.schemas import FocusSessionRead, FocusSessionStart, FocusSessionStop


router = APIRouter(prefix="/focus-sessions", tags=["focus sessions"])


def utc_aware(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)


@router.post("/start", response_model=FocusSessionRead, status_code=status.HTTP_201_CREATED)
def start_focus_session(payload: FocusSessionStart, db: Session = Depends(get_db)) -> FocusSession:
    if db.scalar(select(FocusSession.id).where(FocusSession.ended_at.is_(None)).limit(1)):
        raise HTTPException(status.HTTP_409_CONFLICT, "A focus session is already active")
    if payload.task_id is not None and db.get(Task, payload.task_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Linked task not found")
    session = FocusSession(**payload.model_dump(), started_at=datetime.now(timezone.utc), active_slot=True)
    db.add(session)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "A focus session is already active") from None
    db.refresh(session)
    return session


@router.post("/{session_id}/stop", response_model=FocusSessionRead)
def stop_focus_session(session_id: int, payload: FocusSessionStop | None = None, db: Session = Depends(get_db)) -> FocusSession:
    session = db.scalar(select(FocusSession).where(FocusSession.id == session_id).with_for_update())
    if session is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Focus session not found")
    if session.ended_at is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Focus session is already stopped")
    ended_at = datetime.now(timezone.utc)
    session.ended_at = ended_at
    session.duration_seconds = max(0, int((ended_at - utc_aware(session.started_at)).total_seconds()))
    session.active_slot = None
    if payload is not None and "notes" in payload.model_fields_set:
        session.notes = payload.notes
    task = db.get(Task, session.task_id) if session.task_id else None
    db.add(Activity(type="FOCUS", source_type="focus", source_id=session.id, title=session.category or (task.title if task else "Focus session"), detail=f"Focused for {max(1, round(session.duration_seconds / 60))} min", occurred_at=ended_at))
    db.commit()
    db.refresh(session)
    return session


@router.get("", response_model=list[FocusSessionRead])
def list_focus_sessions(db: Session = Depends(get_db)) -> list[FocusSession]:
    return list(db.scalars(select(FocusSession).order_by(FocusSession.started_at.desc())))


@router.get("/active", response_model=FocusSessionRead | None)
def get_active_focus_session(db: Session = Depends(get_db)) -> FocusSession | None:
    return db.scalar(select(FocusSession).where(FocusSession.ended_at.is_(None)))
