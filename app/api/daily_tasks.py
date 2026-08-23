from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.api.preferences import get_preferences
from app.database import get_db
from app.models import DailyTask, DailyTaskCompletion
from app.schemas import DailyTaskCompletionUpdate, DailyTaskCreate, DailyTaskRead


router = APIRouter(prefix="/daily-tasks", tags=["daily tasks"])


def today(db: Session):
    return datetime.now(timezone.utc).astimezone(ZoneInfo(get_preferences(db).timezone)).date()


def read(task: DailyTask, db: Session) -> DailyTaskRead:
    dates = list(db.scalars(select(DailyTaskCompletion.completed_on).where(DailyTaskCompletion.daily_task_id == task.id).order_by(DailyTaskCompletion.completed_on)))
    return DailyTaskRead(id=task.id, title=task.title, completed_today=today(db) in dates, completions=dates)


def task_or_404(task_id: int, db: Session) -> DailyTask:
    task = db.get(DailyTask, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Daily task not found")
    return task


@router.get("", response_model=list[DailyTaskRead])
def list_daily_tasks(db: Session = Depends(get_db)) -> list[DailyTaskRead]:
    return [read(task, db) for task in db.scalars(select(DailyTask).order_by(DailyTask.id))]


@router.post("", response_model=DailyTaskRead, status_code=status.HTTP_201_CREATED)
def create_daily_task(payload: DailyTaskCreate, db: Session = Depends(get_db)) -> DailyTaskRead:
    task = DailyTask(title=payload.title, created_at=datetime.now(timezone.utc))
    db.add(task); db.commit(); db.refresh(task)
    return read(task, db)


@router.put("/{task_id}/today", response_model=DailyTaskRead)
def set_today(task_id: int, payload: DailyTaskCompletionUpdate, db: Session = Depends(get_db)) -> DailyTaskRead:
    task = task_or_404(task_id, db); local_today = today(db)
    completion = db.scalar(select(DailyTaskCompletion).where(DailyTaskCompletion.daily_task_id == task_id, DailyTaskCompletion.completed_on == local_today))
    if payload.completed and completion is None:
        db.add(DailyTaskCompletion(daily_task_id=task_id, completed_on=local_today, completed_at=datetime.now(timezone.utc)))
    elif not payload.completed and completion is not None:
        db.delete(completion)
    db.commit()
    return read(task, db)


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_daily_task(task_id: int, db: Session = Depends(get_db)) -> Response:
    task = task_or_404(task_id, db)
    db.execute(delete(DailyTaskCompletion).where(DailyTaskCompletion.daily_task_id == task_id))
    db.delete(task); db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
