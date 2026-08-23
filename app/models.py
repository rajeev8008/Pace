from datetime import datetime, time
from enum import Enum

from sqlalchemy import CheckConstraint, DateTime, Enum as SAEnum, String, Text
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
