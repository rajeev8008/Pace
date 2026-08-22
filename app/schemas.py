from datetime import datetime, timezone
from typing import Annotated, Self

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator, model_validator

from app.models import TaskPriority, TaskStatus


Title = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]


def aware_utc(value: datetime | None) -> datetime | None:
    if value is not None and (value.tzinfo is None or value.utcoffset() is None):
        raise ValueError("timestamp must include a timezone offset")
    return value.astimezone(timezone.utc) if value is not None else None


class TaskCreate(BaseModel):
    title: Title
    description: str | None = None
    priority: TaskPriority = TaskPriority.MEDIUM
    due_at: datetime | None = None
    reminder_at: datetime | None = None

    _normalize_timestamps = field_validator("due_at", "reminder_at")(aware_utc)


class TaskUpdate(BaseModel):
    title: Title | None = None
    description: str | None = None
    status: TaskStatus | None = None
    priority: TaskPriority | None = None
    due_at: datetime | None = None
    reminder_at: datetime | None = None

    _normalize_timestamps = field_validator("due_at", "reminder_at")(aware_utc)

    @model_validator(mode="after")
    def reject_null_required_fields(self) -> Self:
        for field in ("title", "status", "priority"):
            if field in self.model_fields_set and getattr(self, field) is None:
                raise ValueError(f"{field} cannot be null")
        return self


class TaskRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str | None
    status: TaskStatus
    priority: TaskPriority
    due_at: datetime | None
    reminder_at: datetime | None
    created_at: datetime
    completed_at: datetime | None
