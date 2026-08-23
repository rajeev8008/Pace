from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Preference
from app.schemas import PreferenceRead, PreferenceUpdate


router = APIRouter(prefix="/preferences", tags=["preferences"])


def get_preferences(db: Session) -> Preference:
    preferences = db.get(Preference, 1)
    if preferences is None:
        preferences = Preference(id=1)
        db.add(preferences)
        db.commit()
        db.refresh(preferences)
    return preferences


@router.get("", response_model=PreferenceRead)
def read_preferences(db: Session = Depends(get_db)) -> Preference:
    return get_preferences(db)


@router.patch("", response_model=PreferenceRead)
def update_preferences(
    payload: PreferenceUpdate, db: Session = Depends(get_db)
) -> Preference:
    changes = payload.model_dump(exclude_unset=True)
    if not changes:
        raise HTTPException(status_code=422, detail="At least one field is required")

    preferences = get_preferences(db)
    for field, value in changes.items():
        setattr(preferences, field, value)
    db.commit()
    db.refresh(preferences)
    return preferences
