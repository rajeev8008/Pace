from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api.jobs import router as jobs_router
from app.api.daily_tasks import router as daily_tasks_router
from app.api.preferences import router as preferences_router
from app.api.tasks import router as tasks_router


app = FastAPI(title="Dayflow")
app.include_router(tasks_router)
app.include_router(preferences_router)
app.include_router(jobs_router)
app.include_router(daily_tasks_router)
app.mount("/", StaticFiles(directory="app/static", html=True), name="frontend")
