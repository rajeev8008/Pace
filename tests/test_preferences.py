import os

os.environ["DATABASE_URL"] = "sqlite://"

from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.api.preferences import read_preferences, update_preferences
from app.database import Base, engine
from app.schemas import PreferenceUpdate


def test_preferences() -> None:
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        defaults = read_preferences(1, db)
        assert defaults.timezone == "Asia/Kolkata"
        assert defaults.daily_digest_enabled is False

        updated = update_preferences(
            PreferenceUpdate(
                email="user@example.com",
                timezone="Asia/Kolkata",
                daily_digest_enabled=True,
                daily_digest_time="20:30",
                weekly_summary_enabled=True,
                weekly_summary_day="MONDAY",
                weekly_summary_time="08:00",
            ),
            1, db,
        )
        assert updated.email == "user@example.com"
        assert updated.daily_digest_time.hour == 20
        assert read_preferences(2, db).daily_digest_enabled is False

        try:
            PreferenceUpdate(timezone="Not/A_Real_Zone")
        except ValidationError:
            pass
        else:
            raise AssertionError("invalid timezone was accepted")


if __name__ == "__main__":
    test_preferences()
