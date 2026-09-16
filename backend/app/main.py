import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app import relationships
from app.db import make_engine, missing_tables
from app.settings import Settings

log = logging.getLogger(__name__)

SEED_COMMAND = "python -m app.seed"


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    # Refuse to start on a missing schema instead of serving empty or broken data.
    # Only the seed command creates tables and rows.
    engine = make_engine(app.state.settings.database_url)
    missing = missing_tables(engine)
    if missing:
        engine.dispose()
        raise RuntimeError(
            f"Database tables missing: {', '.join(missing)}. "
            f"Run `{SEED_COMMAND}` from backend/ first."
        )
    app.state.engine = engine
    try:
        yield
    finally:
        engine.dispose()


def _internal_error(request: Request, exc: Exception) -> JSONResponse:
    log.exception("unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content={"detail": "Internal error"})


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build the app. Tests pass their own settings to point at a temporary database."""
    app = FastAPI(lifespan=lifespan)
    app.state.settings = settings or Settings()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=app.state.settings.cors_origin_list(),
        allow_methods=["GET"],
    )
    app.add_exception_handler(Exception, _internal_error)
    app.include_router(relationships.router)

    @app.get("/")
    def read_root():
        return {"status": "ok"}

    return app


app = create_app()
