import os
from datetime import datetime, timedelta, timezone
from uuid import uuid4
from zoneinfo import ZoneInfo

os.environ["DATABASE_URL"] = "sqlite://"
os.environ["SMTP_HOST"] = ""
os.environ["RESEND_API_KEY"] = ""

from sqlalchemy.orm import Session

from app.database import Base, SessionLocal, engine
from app.models import Activity, Job, JobStatus, JobType, Preference, Task
from scheduler.scheduler import claim_due_work
from worker.worker import process_job
from worker.handlers import bounds, daily_digest, weekly_summary


class FakePublisher:
    def __init__(self) -> None:
        self.topics = []

    def publish(self, topic: str, payload: dict, key: str) -> None:
        self.topics.append(topic)


def test_background_flow() -> None:
    Base.metadata.create_all(engine)
    now = datetime.now(timezone.utc)
    with Session(engine) as db:
        db.add(Preference(user_id=1, email="user@example.com"))
        task = Task(
            user_id=1,
            title="Due reminder",
            reminder_at=now - timedelta(minutes=1),
            created_at=now,
        )
        db.add(task)
        db.commit()
        assert len(claim_due_work(db, now)) == 1
        assert len(claim_due_work(db, now)) == 0
        reminder_job = db.query(Job).filter_by(task_id=task.id).one()
        settings = db.query(Preference).filter_by(user_id=1).one()
        settings.daily_digest_enabled = True
        settings.weekly_summary_enabled = True
        settings.next_daily_digest_at = now - timedelta(seconds=1)
        settings.next_weekly_summary_at = now - timedelta(seconds=1)
        db.commit()
        assert len(claim_due_work(db, now)) == 2
        assert len(claim_due_work(db, now)) == 0
        start, end = bounds(now.astimezone(ZoneInfo("Asia/Kolkata")).date(), ZoneInfo("Asia/Kolkata"))
        db.add_all(
            [
                Task(user_id=1, title="Done today", created_at=now, completed_at=now, status="COMPLETED"),
                Task(user_id=1, title="Due today", created_at=now, due_at=now),
                Task(user_id=1, title="Overdue", created_at=now, due_at=start - timedelta(hours=1)),
                Task(user_id=1, title="Due tomorrow", created_at=now, due_at=end + timedelta(hours=1)),
                Task(user_id=2, title="Other user's task", created_at=now, completed_at=now, status="COMPLETED"),
                Activity(user_id=1, type="ROUTINE", title="Morning stretch", detail="Daily routine completed", occurred_at=now),
                Activity(user_id=1, type="FOCUS", title="Deep work", detail="Focused for 25 min", occurred_at=now),
                Activity(user_id=1, type="GITHUB", title="Pushed a Pace commit", occurred_at=now),
                Activity(user_id=1, type="LEETCODE", title="Solved Two Sum", occurred_at=now),
                Activity(user_id=2, type="GITHUB", title="Other user's commit", occurred_at=now),
            ]
        )
        db.commit()
        digest = daily_digest(db, 1, now)
        assert "Completed today: 1" in digest
        assert "Pending today: 1" in digest
        assert "Overdue: 1" in digest
        assert "Due tomorrow" in digest
        assert "Morning stretch" in digest
        assert "Focused for 25 min" in digest
        assert "Other user's commit" not in digest
        assert "small consistent wins compound" in digest
        summary = weekly_summary(db, 1, now + timedelta(days=7))
        assert "Tasks created:" in summary
        assert "Routines completed: 1" in summary
        assert "Focus sessions: 1" in summary
        assert "GitHub activity: 1" in summary
        assert "LeetCode activity: 1" in summary
        assert "consistency is your real progress multiplier" in summary
        reminder_job_id = reminder_job.id

    publisher = FakePublisher()
    process_job(reminder_job_id, publisher)
    with SessionLocal() as db:
        assert db.get(Job, reminder_job_id).status == JobStatus.SUCCESS
        inline_failed = Job(
            id=str(uuid4()),
            user_id=1,
            type=JobType.TASK_REMINDER,
            occurrence_key="missing-inline-task",
            task_id=998,
            created_at=now,
        )
        db.add(inline_failed)
        db.commit()
        inline_failed_id = inline_failed.id

    process_job(inline_failed_id, None)
    with SessionLocal() as db:
        inline_failed = db.get(Job, inline_failed_id)
        assert inline_failed.status == JobStatus.QUEUED
        assert inline_failed.attempts == 1
        assert inline_failed.published_at is None

    with SessionLocal() as db:
        failed = Job(
            id=str(uuid4()),
            user_id=1,
            type=JobType.TASK_REMINDER,
            occurrence_key="missing-task",
            task_id=999,
            created_at=now,
        )
        db.add(failed)
        db.commit()
        failed_id = failed.id

    process_job(failed_id, publisher)
    process_job(failed_id, publisher)
    process_job(failed_id, publisher)
    with SessionLocal() as db:
        failed = db.get(Job, failed_id)
        assert failed.status == JobStatus.FAILED
        assert failed.attempts == 3
        assert publisher.topics[-1] == "productivity-jobs-dead"


if __name__ == "__main__":
    test_background_flow()
