from fastapi import FastAPI

from app.api.preferences import router as preferences_router
from app.api.tasks import router as tasks_router


app = FastAPI(title="Dayflow")
app.include_router(tasks_router)
app.include_router(preferences_router)
