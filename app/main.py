from fastapi import Depends, FastAPI
from fastapi.staticfiles import StaticFiles

from app.auth import require_auth, router as auth_router
from app.api.jobs import router as jobs_router
from app.api.daily_tasks import router as daily_tasks_router
from app.api.preferences import router as preferences_router
from app.api.tasks import router as tasks_router
from app.api.focus_sessions import router as focus_sessions_router
from app.api.activities import router as activities_router
from app.api.profiles import router as profiles_router
app = FastAPI(title="Pace")
app.include_router(auth_router)
protected = [Depends(require_auth)]
app.include_router(tasks_router, dependencies=protected)
app.include_router(preferences_router, dependencies=protected)
app.include_router(jobs_router, dependencies=protected)
app.include_router(daily_tasks_router, dependencies=protected)
app.include_router(focus_sessions_router, dependencies=protected)
app.include_router(activities_router, dependencies=protected)
app.include_router(profiles_router, dependencies=protected)
app.mount("/", StaticFiles(directory="app/static", html=True), name="frontend")
