from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.config import get_settings
from app.db import Base, engine
from app.logging import configure_logging
from app.routes import api, pages

configure_logging()
settings = get_settings()

@asynccontextmanager
async def lifespan(_app: FastAPI):
    settings.reports_path.mkdir(parents=True, exist_ok=True)
    if settings.allow_auto_create_tables:
        Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title=settings.app_name, debug=settings.debug, lifespan=lifespan)
app.include_router(pages.router)
app.include_router(api.router)

static_dir = Path(__file__).resolve().parent / "static"
app.mount("/static", StaticFiles(directory=static_dir), name="static")
