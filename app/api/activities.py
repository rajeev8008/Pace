from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.preferences import get_preferences
from app.auth import require_auth
from app.database import get_db
from app.models import Activity
from app.schemas import ActivityRead, ActivityUpdate


router = APIRouter(prefix="/activities", tags=["activities"])


@router.get("/today", response_model=list[ActivityRead])
def today(user_id: int = Depends(require_auth), db: Session = Depends(get_db)) -> list[Activity]:
    zone = ZoneInfo(get_preferences(db, user_id).timezone)
    local_now = datetime.now(timezone.utc).astimezone(zone)
    start = datetime.combine(local_now.date(), time.min, zone).astimezone(timezone.utc)
    end = datetime.combine(local_now.date() + timedelta(days=1), time.min, zone).astimezone(timezone.utc)
    return list(db.scalars(select(Activity).where(Activity.user_id == user_id, Activity.occurred_at >= start, Activity.occurred_at < end).order_by(Activity.occurred_at.desc())))


@router.get("/recent", response_model=list[ActivityRead])
def recent(days: int = Query(84, ge=1, le=366), user_id: int = Depends(require_auth), db: Session = Depends(get_db)) -> list[Activity]:
    zone = ZoneInfo(get_preferences(db, user_id).timezone)
    local_today = datetime.now(timezone.utc).astimezone(zone).date()
    start = datetime.combine(local_today - timedelta(days=days - 1), time.min, zone).astimezone(timezone.utc)
    return list(db.scalars(select(Activity).where(Activity.user_id == user_id, Activity.occurred_at >= start).order_by(Activity.occurred_at.desc())))


@router.patch("/{activity_id}", response_model=ActivityRead)
def update(activity_id: int, payload: ActivityUpdate, user_id: int = Depends(require_auth), db: Session = Depends(get_db)) -> Activity:
    activity = db.scalar(select(Activity).where(Activity.id == activity_id, Activity.user_id == user_id))
    if activity is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Activity not found")
    changes = payload.model_dump(exclude_unset=True)
    if not changes:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "At least one field is required")
    for field, value in changes.items():
        setattr(activity, field, value)
    db.commit(); db.refresh(activity)
    return activity


@router.delete("/{activity_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete(activity_id: int, user_id: int = Depends(require_auth), db: Session = Depends(get_db)) -> Response:
    activity = db.scalar(select(Activity).where(Activity.id == activity_id, Activity.user_id == user_id))
    if activity is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Activity not found")
    db.delete(activity); db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
