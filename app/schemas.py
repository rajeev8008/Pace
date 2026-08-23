from datetime import date, datetime, time, timezone
from typing import Annotated, Self
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator, model_validator

from app.models import JobStatus, JobType, TaskPriority, TaskStatus, Weekday


Title = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
Email = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        max_length=320,
        pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$",
    ),
]


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


class PreferenceUpdate(BaseModel):
    email: Email | None = None
    timezone: str | None = Field(default=None, min_length=1, max_length=64)
    daily_digest_enabled: bool | None = None
    daily_digest_time: time | None = None
    weekly_summary_enabled: bool | None = None
    weekly_summary_day: Weekday | None = None
    weekly_summary_time: time | None = None

    @field_validator("timezone")
    @classmethod
    def timezone_must_exist(cls, value: str | None) -> str | None:
        if value is not None:
            try:
                ZoneInfo(value)
            except ZoneInfoNotFoundError as error:
                raise ValueError("unknown IANA timezone") from error
        return value

    @field_validator("daily_digest_time", "weekly_summary_time")
    @classmethod
    def schedule_times_are_local(cls, value: time | None) -> time | None:
        if value is not None and value.tzinfo is not None:
            raise ValueError("schedule time must not include a timezone offset")
        return value

    @model_validator(mode="after")
    def reject_null_required_fields(self) -> Self:
        for field in self.model_fields_set - {"email"}:
            if getattr(self, field) is None:
                raise ValueError(f"{field} cannot be null")
        return self


class PreferenceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    email: str | None
    timezone: str
    daily_digest_enabled: bool
    daily_digest_time: time
    weekly_summary_enabled: bool
    weekly_summary_day: Weekday
    weekly_summary_time: time


class JobRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    type: JobType
    status: JobStatus
    task_id: int | None
    attempts: int
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    error: str | None


class DailyTaskCreate(BaseModel):
    title: Title


class DailyTaskCompletionUpdate(BaseModel):
    completed: bool


class DailyTaskRead(BaseModel):
    id: int
    title: str
    completed_today: bool
    completions: list[date]


class FocusSessionStart(BaseModel):
    category: str | None = Field(default=None, max_length=100)
    task_id: int | None = Field(default=None, gt=0)
    notes: str | None = Field(default=None, max_length=2000)


class FocusSessionStop(BaseModel):
    notes: str | None = Field(default=None, max_length=2000)


class FocusSessionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    category: str | None
    task_id: int | None
    started_at: datetime
    ended_at: datetime | None
    duration_seconds: int | None
    notes: str | None

    @field_validator("started_at", "ended_at", mode="before")
    @classmethod
    def serialize_stored_utc(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        return (value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value).astimezone(timezone.utc)


class ActivityUpdate(BaseModel):
    title: Title | None = None
    detail: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def title_cannot_be_null(self) -> Self:
        if "title" in self.model_fields_set and self.title is None:
            raise ValueError("title cannot be null")
        return self


class ActivityRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    type: str
    title: str
    detail: str | None
    occurred_at: datetime


class ExternalProfileCreate(BaseModel):
    provider: str = Field(pattern=r"^(GITHUB|LEETCODE)$")
    profile_url: str = Field(min_length=10, max_length=500)


class ExternalProfileRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    provider: str
    username: str
    profile_url: str
    last_synced_at: datetime | None
