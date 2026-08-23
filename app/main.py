from fastapi import Depends, FastAPI
from fastapi.staticfiles import StaticFiles

from app.auth import require_auth, router as auth_router
from app.api.jobs import router as jobs_router
from app.api.daily_tasks import router as daily_tasks_router
from app.api.preferences import router as preferences_router
from app.api.tasks import router as tasks_router


app = FastAPI(title="Dayflow")
app.include_router(auth_router)
protected = [Depends(require_auth)]
app.include_router(tasks_router, dependencies=protected)
app.include_router(preferences_router, dependencies=protected)
app.include_router(jobs_router, dependencies=protected)
app.include_router(daily_tasks_router, dependencies=protected)
app.mount("/", StaticFiles(directory="app/static", html=True), name="frontend")
