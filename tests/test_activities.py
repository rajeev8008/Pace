import os
from datetime import datetime, timezone

os.environ["DATABASE_URL"] = "sqlite://"

from sqlalchemy.orm import Session

from app.api.activities import delete, today, update
from app.database import Base, engine
from app.models import Activity, Preference
from app.schemas import ActivityUpdate


def run_checks() -> None:
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add(Preference(id=1, timezone="Asia/Kolkata"))
        activity = Activity(type="TASK", title="Original", detail="Done", occurred_at=datetime.now(timezone.utc))
        db.add(activity); db.commit(); db.refresh(activity)
        assert today(db)[0].title == "Original"
        assert update(activity.id, ActivityUpdate(title="Edited"), db).title == "Edited"
        assert delete(activity.id, db).status_code == 204
        assert today(db) == []


if __name__ == "__main__":
    run_checks()
    print("Activity checks passed")
