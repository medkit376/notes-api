from fastapi import FastAPI

from app.api import auth, notes
from app.core.config import settings

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="A REST API for managing personal notes, with JWT auth, "
    "pagination, and tag-based filtering.",
    version="1.0.0",
)

app.include_router(auth.router, prefix=settings.API_V1_PREFIX)
app.include_router(notes.router, prefix=settings.API_V1_PREFIX)


@app.get("/health", tags=["health"])
async def health_check():
    return {"status": "ok"}
