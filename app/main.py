import hmac
import os

from fastapi import Depends, FastAPI, Header, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.auth import require_auth, router as auth_router
from app.api.jobs import router as jobs_router
from app.api.daily_tasks import router as daily_tasks_router
from app.api.preferences import router as preferences_router
from app.api.tasks import router as tasks_router
from app.api.focus_sessions import router as focus_sessions_router
from app.api.activities import router as activities_router
from app.api.profiles import router as profiles_router
from scheduler.scheduler import run_inline_once


app = FastAPI(title="Pace")
if frontend_url := os.getenv("FRONTEND_URL", "").rstrip("/"):
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[frontend_url],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
app.include_router(auth_router)
protected = [Depends(require_auth)]
app.include_router(tasks_router, dependencies=protected)
app.include_router(preferences_router, dependencies=protected)
app.include_router(jobs_router, dependencies=protected)
app.include_router(daily_tasks_router, dependencies=protected)
app.include_router(focus_sessions_router, dependencies=protected)
app.include_router(activities_router, dependencies=protected)
app.include_router(profiles_router, dependencies=protected)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/internal/run-jobs")
def run_jobs(authorization: str | None = Header(default=None)) -> dict[str, int]:
    secret = os.getenv("CRON_SECRET", "")
    if not secret or not authorization or not hmac.compare_digest(authorization, f"Bearer {secret}"):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid cron credentials")
    return {"processed": run_inline_once()}


app.mount("/", StaticFiles(directory="app/static", html=True), name="frontend")
