import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app import relationships
from app.assessment import routes as assessment_routes
from app.assessment.gemini import GeminiAssessmentProvider
from app.assessment.provider import AssessmentProvider
from app.db import make_engine, missing_tables
from app.settings import Settings

log = logging.getLogger(__name__)

SEED_COMMAND = "python -m app.seed"


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    engine = make_engine(app.state.settings.database_url)
    try:
        # Refuse to start on a missing schema instead of serving empty or broken data.
        # Only the seed command creates tables and rows.
        missing = missing_tables(engine)
        if missing:
            raise RuntimeError(
                f"Database tables missing: {', '.join(missing)}. "
                f"Run `{SEED_COMMAND}` from backend/ first."
            )
        # One provider for the whole app, never one per request. Without an injected
        # one, the Gemini provider refuses to start when GEMINI_API_KEY is missing.
        gemini = None
        provider = app.state.injected_provider
        if provider is None:
            gemini = GeminiAssessmentProvider(app.state.settings)
            provider = gemini
        app.state.engine = engine
        app.state.provider = provider
        try:
            yield
        finally:
            if gemini is not None:
                await gemini.aclose()
    finally:
        engine.dispose()


def _internal_error(request: Request, exc: Exception) -> JSONResponse:
    log.exception("unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content={"detail": "Internal error"})


def create_app(
    settings: Settings | None = None, provider: AssessmentProvider | None = None
) -> FastAPI:
    """Build the app. Tests pass their own settings to point at a temporary database,
    and a fake provider so no test needs a key or calls a real model."""
    app = FastAPI(lifespan=lifespan)
    app.state.settings = settings or Settings()
    app.state.injected_provider = provider
    app.add_middleware(
        CORSMiddleware,
        allow_origins=app.state.settings.cors_origin_list(),
        allow_methods=["GET"],
    )
    app.add_exception_handler(Exception, _internal_error)
    app.include_router(relationships.router)
    app.include_router(assessment_routes.router)

    @app.get("/")
    def read_root():
        return {"status": "ok"}

    return app


app = create_app()
