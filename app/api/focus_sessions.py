from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth import require_auth
from app.models import Activity, DailyTask, FocusSession
from app.schemas import FocusSessionRead, FocusSessionStart, FocusSessionStop


router = APIRouter(prefix="/focus-sessions", tags=["focus sessions"])


def utc_aware(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)


@router.post("/start", response_model=FocusSessionRead, status_code=status.HTTP_201_CREATED)
def start_focus_session(payload: FocusSessionStart, user_id: int = Depends(require_auth), db: Session = Depends(get_db)) -> FocusSession:
    if db.scalar(select(FocusSession.id).where(FocusSession.user_id == user_id, FocusSession.ended_at.is_(None)).limit(1)):
        raise HTTPException(status.HTTP_409_CONFLICT, "A focus session is already active")
    if payload.daily_task_id is not None and not db.scalar(select(DailyTask.id).where(DailyTask.id == payload.daily_task_id, DailyTask.user_id == user_id)):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Linked daily routine not found")
    session = FocusSession(user_id=user_id, **payload.model_dump(), started_at=datetime.now(timezone.utc), active_slot=True)
    db.add(session)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "A focus session is already active") from None
    db.refresh(session)
    return session


@router.post("/{session_id}/stop", response_model=FocusSessionRead)
def stop_focus_session(session_id: int, payload: FocusSessionStop | None = None, user_id: int = Depends(require_auth), db: Session = Depends(get_db)) -> FocusSession:
    session = db.scalar(select(FocusSession).where(FocusSession.id == session_id, FocusSession.user_id == user_id).with_for_update())
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
    routine = db.scalar(select(DailyTask).where(DailyTask.id == session.daily_task_id, DailyTask.user_id == user_id)) if session.daily_task_id else None
    minutes = max(1, round(session.duration_seconds / 60))
    detail = f"{session.category} · " if routine and session.category else ""
    db.add(Activity(user_id=user_id, type="FOCUS", source_type="focus", source_id=session.id, title=routine.title if routine else session.category or "Focus session", detail=f"{detail}Focused for {minutes} min", occurred_at=ended_at))
    db.commit()
    db.refresh(session)
    return session


@router.get("", response_model=list[FocusSessionRead])
def list_focus_sessions(user_id: int = Depends(require_auth), db: Session = Depends(get_db)) -> list[FocusSession]:
    return list(db.scalars(select(FocusSession).where(FocusSession.user_id == user_id).order_by(FocusSession.started_at.desc())))


@router.get("/active", response_model=FocusSessionRead | None)
def get_active_focus_session(user_id: int = Depends(require_auth), db: Session = Depends(get_db)) -> FocusSession | None:
    return db.scalar(select(FocusSession).where(FocusSession.user_id == user_id, FocusSession.ended_at.is_(None)))
