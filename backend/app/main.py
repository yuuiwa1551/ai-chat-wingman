from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
import sys

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api import demo, history, importers, jobs, memories, multimodal, privacy, reply, settings, style_test, targets
from app.api import onboarding
from app.db.database import initialize_database
from app.services.onboarding_service import seed_style_presets


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    initialize_database()
    seed_style_presets()
    yield


def create_app() -> FastAPI:
    app = FastAPI(title="AI Chat Wingman", version="0.1.0", lifespan=lifespan)

    @app.get("/healthz")
    def healthz() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(demo.router)
    app.include_router(history.router)
    app.include_router(importers.router)
    app.include_router(jobs.router)
    app.include_router(memories.router)
    app.include_router(multimodal.router)
    app.include_router(onboarding.router)
    app.include_router(privacy.router)
    app.include_router(reply.router)
    app.include_router(settings.router)
    app.include_router(style_test.router)
    app.include_router(targets.router)

    frontend_dist = frontend_dist_path()
    if frontend_dist.exists():
        app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="frontend")
    return app


def frontend_dist_path() -> Path:
    bundle_root = getattr(sys, "_MEIPASS", None)
    if bundle_root:
        return Path(bundle_root) / "frontend" / "dist"
    return Path(__file__).resolve().parents[2] / "frontend" / "dist"


app = create_app()
