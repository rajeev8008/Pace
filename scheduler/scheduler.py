import argparse
import os
import time as clock
from datetime import date, datetime, time, timedelta, timezone
from uuid import uuid4
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import Job, JobStatus, JobType, Preference, Task, TaskStatus, Weekday
from messaging.kafka import JOBS_TOPIC, KafkaPublisher


def utc(local_date: date, local_time: time, zone: ZoneInfo) -> datetime:
    return datetime.combine(local_date, local_time, zone).astimezone(timezone.utc)


def aware(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)


def next_daily(now: datetime, preference: Preference) -> datetime:
    zone = ZoneInfo(preference.timezone)
    local_now = now.astimezone(zone)
    candidate = utc(local_now.date(), preference.daily_digest_time, zone)
    return candidate if candidate > now else utc(
        local_now.date() + timedelta(days=1), preference.daily_digest_time, zone
    )


def next_weekly(now: datetime, preference: Preference) -> datetime:
    zone = ZoneInfo(preference.timezone)
    local_now = now.astimezone(zone)
    weekday = list(Weekday).index(preference.weekly_summary_day)
    candidate_date = local_now.date() + timedelta(days=(weekday - local_now.weekday()) % 7)
    candidate = utc(candidate_date, preference.weekly_summary_time, zone)
    return candidate if candidate > now else utc(
        candidate_date + timedelta(days=7), preference.weekly_summary_time, zone
    )


def add_job(
    db: Session,
    user_id: int,
    job_type: JobType,
    occurrence_key: str,
    now: datetime,
    task_id: int | None = None,
) -> Job:
    job = Job(
        id=str(uuid4()),
        user_id=user_id,
        type=job_type,
        occurrence_key=occurrence_key,
        task_id=task_id,
        created_at=now,
    )
    db.add(job)
    return job


def claim_due_work(db: Session, now: datetime | None = None) -> list[Job]:
    now = now or datetime.now(timezone.utc)
    jobs = []
    reminders = db.scalars(
        select(Task)
        .where(
            Task.reminder_at <= now,
            Task.status == TaskStatus.PENDING,
            Task.reminder_processed_at.is_(None),
        )
        .with_for_update(skip_locked=True)
    )
    for task in reminders:
        jobs.append(
            add_job(
                db,
                task.user_id,
                JobType.TASK_REMINDER,
                f"reminder:{task.id}:{task.reminder_at.isoformat()}",
                now,
                task.id,
            )
        )
        task.reminder_processed_at = now

    for preference in db.scalars(select(Preference).with_for_update(skip_locked=True)):
        if preference.daily_digest_enabled:
            if preference.next_daily_digest_at is None:
                preference.next_daily_digest_at = next_daily(now, preference)
            elif aware(preference.next_daily_digest_at) <= now:
                due = aware(preference.next_daily_digest_at)
                jobs.append(add_job(db, preference.user_id, JobType.DAILY_DIGEST, f"daily:{due.isoformat()}", now))
                preference.next_daily_digest_at = next_daily(now, preference)
        if preference.weekly_summary_enabled:
            if preference.next_weekly_summary_at is None:
                preference.next_weekly_summary_at = next_weekly(now, preference)
            elif aware(preference.next_weekly_summary_at) <= now:
                due = aware(preference.next_weekly_summary_at)
                jobs.append(add_job(db, preference.user_id, JobType.WEEKLY_SUMMARY, f"weekly:{due.isoformat()}", now))
                preference.next_weekly_summary_at = next_weekly(now, preference)
    db.commit()
    return jobs


def payload(job: Job) -> dict:
    data = {
        "job_id": job.id,
        "type": job.type.value,
        "created_at": job.created_at.isoformat(),
        "attempt": job.attempts,
    }
    if job.task_id is not None:
        data["task_id"] = job.task_id
    return data


def run_once(print_only: bool = False) -> int:
    publisher = None if print_only else KafkaPublisher()
    with SessionLocal() as db:
        claim_due_work(db)
        jobs = list(
            db.scalars(
                select(Job)
                .where(
                    Job.status == JobStatus.QUEUED,
                    Job.published_at.is_(None),
                )
                .with_for_update(skip_locked=True)
            )
        )
        for job in jobs:
            if print_only:
                print(
                    f"[Scheduler] {job.type.value} due"
                    + (f" Task ID: {job.task_id}" if job.task_id else "")
                )
                job.published_at = datetime.now(timezone.utc)
                db.commit()
            else:
                publisher.publish(JOBS_TOPIC, payload(job), job.id)
                job.published_at = datetime.now(timezone.utc)
                db.commit()
        return len(jobs)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--print-only", action="store_true")
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()
    while True:
        run_once(args.print_only)
        if args.once:
            return
        clock.sleep(float(os.getenv("SCHEDULER_INTERVAL_SECONDS", "5")))


if __name__ == "__main__":
    main()
