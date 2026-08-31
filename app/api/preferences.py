from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth import require_auth
from app.models import Preference, User
from app.schemas import PreferenceRead, PreferenceUpdate


router = APIRouter(prefix="/preferences", tags=["preferences"])


def get_preferences(db: Session, user_id: int) -> Preference:
    preferences = db.scalar(select(Preference).where(Preference.user_id == user_id))
    if preferences is None:
        user = db.get(User, user_id)
        preferences = Preference(user_id=user_id, email=user.email if user else None)
        db.add(preferences)
        db.commit()
        db.refresh(preferences)
    return preferences


@router.get("", response_model=PreferenceRead)
def read_preferences(user_id: int = Depends(require_auth), db: Session = Depends(get_db)) -> Preference:
    return get_preferences(db, user_id)


@router.patch("", response_model=PreferenceRead)
def update_preferences(
    payload: PreferenceUpdate, user_id: int = Depends(require_auth), db: Session = Depends(get_db)
) -> Preference:
    changes = payload.model_dump(exclude_unset=True)
    if not changes:
        raise HTTPException(status_code=422, detail="At least one field is required")

    preferences = get_preferences(db, user_id)
    for field, value in changes.items():
        setattr(preferences, field, value)
    if changes.keys() & {"timezone", "daily_digest_enabled", "daily_digest_time"}:
        preferences.next_daily_digest_at = None
    if changes.keys() & {
        "timezone",
        "weekly_summary_enabled",
        "weekly_summary_day",
        "weekly_summary_time",
    }:
        preferences.next_weekly_summary_at = None
    db.commit()
    db.refresh(preferences)
    return preferences
