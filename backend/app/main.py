"""FastAPI application factory and entrypoint.

Run with:  uvicorn app.main:app --reload --port 8000
"""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .ai.summarizer import Summarizer
from .api.routes import router
from .config import get_settings


def _init_state(app: FastAPI) -> None:
    """Attach shared, process-wide state.

    Done here (rather than only in ``lifespan``) so the state is present even if
    a caller skips the lifespan, e.g. ``TestClient(app)`` used without a ``with``
    block. Safe to call more than once.
    """
    settings = get_settings()
    if not hasattr(app.state, "analyzed_roots"):
        app.state.analyzed_roots = set()
    if not hasattr(app.state, "summarizer"):
        app.state.summarizer = Summarizer(settings)
    if settings.repo_root_path:
        app.state.analyzed_roots.add(str(settings.repo_root_path))


@asynccontextmanager
async def lifespan(app: FastAPI):
    _init_state(app)
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="Repository Structure Analysis & Visualisation API",
        version="1.0.0",
        description=(
            "Parses a local Git repository into a dependency graph (nodes + "
            "edges), reports per-file metrics, and produces cached, plain-"
            "English explanations of individual files."
        ),
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(router)
    _init_state(app)

    @app.get("/")
    def index() -> dict:
        return {"name": "repo-visualizer-api", "docs": "/docs", "health": "/api/health"}

    return app


app = create_app()
