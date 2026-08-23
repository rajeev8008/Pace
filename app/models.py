from datetime import date, datetime, time
from enum import Enum

from sqlalchemy import Boolean, CheckConstraint, Date, DateTime, Enum as SAEnum, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class TaskStatus(str, Enum):
    PENDING = "PENDING"
    COMPLETED = "COMPLETED"


class TaskPriority(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class User(Base):
    __tablename__ = "users"
    __table_args__ = (CheckConstraint("id = 1", name="single_user_account"),)

    id: Mapped[int] = mapped_column(primary_key=True, default=1)
    username: Mapped[str] = mapped_column(String(64), unique=True)
    email: Mapped[str | None] = mapped_column(String(320), unique=True)
    display_name: Mapped[str] = mapped_column(String(100))
    password_hash: Mapped[str | None] = mapped_column(String(256))
    github_id: Mapped[str | None] = mapped_column(String(64), unique=True)
    google_id: Mapped[str | None] = mapped_column(String(255), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


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


class FocusSession(Base):
    __tablename__ = "focus_sessions"
    __table_args__ = (
        CheckConstraint("duration_seconds IS NULL OR duration_seconds >= 0", name="focus_duration_nonnegative"),
        CheckConstraint("ended_at IS NULL OR ended_at >= started_at", name="focus_time_order"),
        CheckConstraint("(ended_at IS NULL) = (duration_seconds IS NULL)", name="focus_completion_state"),
        CheckConstraint("active_slot IS NULL OR active_slot = true", name="focus_active_slot_value"),
        UniqueConstraint("active_slot", name="one_active_focus_session"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    category: Mapped[str | None] = mapped_column(String(100))
    task_id: Mapped[int | None] = mapped_column(ForeignKey("tasks.id", ondelete="SET NULL"), index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    duration_seconds: Mapped[int | None] = mapped_column(Integer)
    notes: Mapped[str | None] = mapped_column(Text)
    active_slot: Mapped[bool | None] = mapped_column(Boolean, default=True, server_default="true")


class Activity(Base):
    __tablename__ = "activities"
    __table_args__ = (
        CheckConstraint("type IN ('TASK', 'ROUTINE', 'FOCUS', 'GITHUB')", name="activity_type"),
        UniqueConstraint("source_type", "source_id", name="activity_source_once"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    type: Mapped[str] = mapped_column(String(20), index=True)
    source_type: Mapped[str | None] = mapped_column(String(30))
    source_id: Mapped[int | None] = mapped_column(Integer)
    title: Mapped[str] = mapped_column(String(200))
    detail: Mapped[str | None] = mapped_column(Text)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
