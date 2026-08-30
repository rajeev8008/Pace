from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth import require_auth
from app.models import Job
from app.schemas import JobRead


router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("", response_model=list[JobRead])
def list_jobs(user_id: int = Depends(require_auth), db: Session = Depends(get_db)) -> list[Job]:
    return list(db.scalars(select(Job).where(Job.user_id == user_id).order_by(Job.created_at.desc())))


@router.get("/{job_id}", response_model=JobRead)
def get_job(job_id: str, user_id: int = Depends(require_auth), db: Session = Depends(get_db)) -> Job:
    job = db.scalar(select(Job).where(Job.id == job_id, Job.user_id == user_id))
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return job
