from datetime import date, datetime, time
from enum import Enum

from sqlalchemy import CheckConstraint, Date, DateTime, Enum as SAEnum, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class TaskStatus(str, Enum):
    PENDING = "PENDING"
    COMPLETED = "COMPLETED"


class TaskPriority(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class Task(Base):
    __tablename__ = "tasks"
    __table_args__ = (
        CheckConstraint("status IN ('PENDING', 'COMPLETED')", name="task_status"),
        CheckConstraint("priority IN ('LOW', 'MEDIUM', 'HIGH')", name="task_priority"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[TaskStatus] = mapped_column(
        SAEnum(TaskStatus, native_enum=False),
        default=TaskStatus.PENDING,
        server_default=TaskStatus.PENDING.value,
    )
    priority: Mapped[TaskPriority] = mapped_column(
        SAEnum(TaskPriority, native_enum=False),
        default=TaskPriority.MEDIUM,
        server_default=TaskPriority.MEDIUM.value,
    )
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reminder_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reminder_processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Weekday(str, Enum):
    MONDAY = "MONDAY"
    TUESDAY = "TUESDAY"
    WEDNESDAY = "WEDNESDAY"
    THURSDAY = "THURSDAY"
    FRIDAY = "FRIDAY"
    SATURDAY = "SATURDAY"
    SUNDAY = "SUNDAY"


class Preference(Base):
    __tablename__ = "preferences"
    __table_args__ = (
        CheckConstraint("id = 1", name="single_preferences_row"),
        CheckConstraint(
            "weekly_summary_day IN ('MONDAY', 'TUESDAY', 'WEDNESDAY', 'THURSDAY', 'FRIDAY', 'SATURDAY', 'SUNDAY')",
            name="weekday",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, default=1)
    email: Mapped[str | None] = mapped_column(String(320))
    timezone: Mapped[str] = mapped_column(
        String(64), default="Asia/Kolkata", server_default="Asia/Kolkata"
    )
    daily_digest_enabled: Mapped[bool] = mapped_column(default=False, server_default="false")
    daily_digest_time: Mapped[time] = mapped_column(default=time(20), server_default="20:00:00")
    weekly_summary_enabled: Mapped[bool] = mapped_column(default=False, server_default="false")
    weekly_summary_day: Mapped[Weekday] = mapped_column(
        SAEnum(Weekday, native_enum=False),
        default=Weekday.SUNDAY,
        server_default=Weekday.SUNDAY.value,
    )
    weekly_summary_time: Mapped[time] = mapped_column(default=time(20), server_default="20:00:00")
    next_daily_digest_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    next_weekly_summary_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class JobType(str, Enum):
    TASK_REMINDER = "TASK_REMINDER"
    DAILY_DIGEST = "DAILY_DIGEST"
    WEEKLY_SUMMARY = "WEEKLY_SUMMARY"


class JobStatus(str, Enum):
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


class Job(Base):
    __tablename__ = "jobs"
    __table_args__ = (
        CheckConstraint(
            "type IN ('TASK_REMINDER', 'DAILY_DIGEST', 'WEEKLY_SUMMARY')",
            name="job_type",
        ),
        CheckConstraint(
            "status IN ('QUEUED', 'RUNNING', 'SUCCESS', 'FAILED')",
            name="job_status",
        ),
        CheckConstraint("attempts BETWEEN 0 AND 3", name="job_attempts"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    type: Mapped[JobType] = mapped_column(SAEnum(JobType, native_enum=False))
    status: Mapped[JobStatus] = mapped_column(
        SAEnum(JobStatus, native_enum=False),
        default=JobStatus.QUEUED,
        server_default=JobStatus.QUEUED.value,
    )
    occurrence_key: Mapped[str] = mapped_column(String(200), unique=True)
    task_id: Mapped[int | None] = mapped_column(Integer)
    attempts: Mapped[int] = mapped_column(default=0, server_default="0")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error: Mapped[str | None] = mapped_column(Text)


class DailyTask(Base):
    __tablename__ = "daily_tasks"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class DailyTaskCompletion(Base):
    __tablename__ = "daily_task_completions"
    __table_args__ = (UniqueConstraint("daily_task_id", "completed_on", name="daily_task_once_per_day"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    daily_task_id: Mapped[int] = mapped_column(ForeignKey("daily_tasks.id", ondelete="CASCADE"))
    completed_on: Mapped[date] = mapped_column(Date)
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
