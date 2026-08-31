"""Application factory and startup/shutdown wiring."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.core.config import Settings, get_settings
from app.core.neo4j import create_driver


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Own the Neo4j driver for the lifetime of the process.

    Creating the driver does not open a connection, so startup does not fail
    when the database is not up yet; /health reports that instead.
    """
    settings: Settings = app.state.settings
    app.state.neo4j_driver = create_driver(settings)
    try:
        yield
    finally:
        await app.state.neo4j_driver.close()


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()

    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        lifespan=lifespan,
    )
    app.state.settings = settings

    # The browser blocks cross-origin calls from the frontend unless the API
    # says which origins it trusts. allow_credentials stays off because the API
    # uses no cookies or auth headers yet; turn it on when authentication lands,
    # and keep the origin list exact if you do.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_origin_regex=settings.cors_origin_regex or None,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(router, prefix="/api")
    return app


app = create_app()
