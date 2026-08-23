import json
import os
from datetime import datetime, timezone

from confluent_kafka import Consumer
from sqlalchemy import select

from app.database import SessionLocal
from app.models import Job, JobStatus, JobType
from messaging.kafka import DEAD_TOPIC, JOBS_TOPIC, RETRY_TOPIC, KafkaPublisher
from scheduler.scheduler import payload
from worker.handlers import handle_daily_digest, handle_task_reminder, handle_weekly_summary


HANDLERS = {
    JobType.TASK_REMINDER: handle_task_reminder,
    JobType.DAILY_DIGEST: handle_daily_digest,
    JobType.WEEKLY_SUMMARY: handle_weekly_summary,
}


def process_job(job_id: str, publisher: KafkaPublisher) -> None:
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
                job.published_at = None
                topic = RETRY_TOPIC
            else:
                job.status = JobStatus.FAILED
                topic = DEAD_TOPIC
            db.commit()
            publisher.publish(topic, payload(job), job.id)
            if job.status == JobStatus.QUEUED:
                job.published_at = datetime.now(timezone.utc)
                db.commit()
            return
        job.status = JobStatus.SUCCESS
        job.error = None
        job.completed_at = datetime.now(timezone.utc)
        db.commit()


def main() -> None:
    consumer = Consumer(
        {
            "bootstrap.servers": os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092"),
            "group.id": "dayflow-workers",
            "auto.offset.reset": "earliest",
            "enable.auto.commit": False,
        }
    )
    publisher = KafkaPublisher()
    consumer.subscribe([JOBS_TOPIC, RETRY_TOPIC])
    try:
        while True:
            message = consumer.poll(1)
            if message is None:
                continue
            if message.error():
                raise RuntimeError(message.error())
            data = json.loads(message.value())
            process_job(data["job_id"], publisher)
            consumer.commit(message=message, asynchronous=False)
    finally:
        consumer.close()


if __name__ == "__main__":
    main()
