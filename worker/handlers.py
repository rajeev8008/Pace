from collections import Counter
from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Job, Preference, Task, TaskPriority, TaskStatus
from app.services.email_service import send_email


def bounds(local_date, zone: ZoneInfo) -> tuple[datetime, datetime]:
    start = datetime.combine(local_date, time.min, zone).astimezone(timezone.utc)
    end = datetime.combine(local_date + timedelta(days=1), time.min, zone).astimezone(timezone.utc)
    return start, end


def preference(db: Session) -> Preference:
    value = db.get(Preference, 1)
    if value is None:
        raise ValueError("preferences are not configured")
    return value


def handle_task_reminder(db: Session, job: Job) -> None:
    task = db.get(Task, job.task_id)
    if task is None:
        raise ValueError(f"task {job.task_id} does not exist")
    settings = preference(db)
    body = f"{task.title}\nDue: {task.due_at or 'No due date'}\nPriority: {task.priority.value}"
    send_email(settings.email, f"Reminder: {task.title}", body)


def daily_digest(db: Session, now: datetime | None = None) -> str:
    now = now or datetime.now(timezone.utc)
    settings = preference(db)
    zone = ZoneInfo(settings.timezone)
    today_start, tomorrow_start = bounds(now.astimezone(zone).date(), zone)
    tomorrow_end = bounds(now.astimezone(zone).date() + timedelta(days=1), zone)[1]
    completed = list(db.scalars(select(Task).where(Task.completed_at >= today_start, Task.completed_at < tomorrow_start)))
    pending = list(db.scalars(select(Task).where(Task.status == TaskStatus.PENDING, Task.due_at >= today_start, Task.due_at < tomorrow_start)))
    overdue = list(db.scalars(select(Task).where(Task.status == TaskStatus.PENDING, Task.due_at < today_start)))
    tomorrow = list(db.scalars(select(Task).where(Task.status == TaskStatus.PENDING, Task.due_at >= tomorrow_start, Task.due_at < tomorrow_end)))

    def names(title: str, tasks: list[Task]) -> str:
        return f"\n{title}:\n" + ("\n".join(f"- {task.title}" for task in tasks) or "- None")

    return (
        f"Your Daily Digest\n\nCompleted today: {len(completed)}\n"
        f"Pending today: {len(pending)}\nOverdue: {len(overdue)}"
        + names("Completed", completed)
        + names("Pending", pending)
        + names("Due Tomorrow", tomorrow)
    )


def handle_daily_digest(db: Session, _: Job) -> None:
    settings = preference(db)
    send_email(settings.email, "Your Pace Daily Digest", daily_digest(db))


def weekly_summary(db: Session, now: datetime | None = None) -> str:
    now = now or datetime.now(timezone.utc)
    settings = preference(db)
    zone = ZoneInfo(settings.timezone)
    local_today = now.astimezone(zone).date()
    current_monday = local_today - timedelta(days=local_today.weekday())
    start = datetime.combine(current_monday - timedelta(days=7), time.min, zone).astimezone(timezone.utc)
    end = datetime.combine(current_monday, time.min, zone).astimezone(timezone.utc)
    created = list(db.scalars(select(Task).where(Task.created_at >= start, Task.created_at < end)))
    completed = list(db.scalars(select(Task).where(Task.completed_at >= start, Task.completed_at < end)))
    overdue = list(db.scalars(select(Task).where(Task.status == TaskStatus.PENDING, Task.due_at < end)))
    high = sum(task.priority == TaskPriority.HIGH for task in completed)
    days = Counter(task.completed_at.astimezone(zone).strftime("%A") for task in completed)
    productive = days.most_common(1)[0][0] if days else "None"
    rate = round(len(completed) / len(created) * 100) if created else 0
    return (
        "Your Pace Weekly Summary\n\n"
        f"Tasks created: {len(created)}\nTasks completed: {len(completed)}\n"
        f"Completion rate: {rate}%\nHigh-priority completed: {high}\n"
        f"Most productive day: {productive}\nOverdue: {len(overdue)}"
    )


def handle_weekly_summary(db: Session, _: Job) -> None:
    settings = preference(db)
    send_email(settings.email, "Your Pace Weekly Summary", weekly_summary(db))
