from datetime import datetime, timezone

from sqlalchemy import select

from app.database import SessionLocal
from app.models import Job, JobStatus, JobType
from worker.handlers import handle_daily_digest, handle_task_reminder, handle_weekly_summary


HANDLERS = {
    JobType.TASK_REMINDER: handle_task_reminder,
    JobType.DAILY_DIGEST: handle_daily_digest,
    JobType.WEEKLY_SUMMARY: handle_weekly_summary,
}


def process_job(job_id: str) -> None:
    with SessionLocal() as db:
        job = db.scalar(select(Job).where(Job.id == job_id).with_for_update())
        if job is None:
            raise ValueError(f"job {job_id} does not exist")
        if job.status == JobStatus.SUCCESS or (
            job.status == JobStatus.FAILED and job.attempts >= 3
        ):
            return
        job.status = JobStatus.RUNNING
        job.started_at = datetime.now(timezone.utc)
        db.flush()
        try:
            HANDLERS[job.type](db, job)
        except Exception as error:
            job.attempts += 1
            job.error = str(error)
            job.completed_at = datetime.now(timezone.utc)
            if job.attempts < 3:
                job.status = JobStatus.QUEUED
            else:
                job.status = JobStatus.FAILED
            db.commit()
            return
        job.status = JobStatus.SUCCESS
        job.error = None
        job.completed_at = datetime.now(timezone.utc)
        db.commit()
