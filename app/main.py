"""Application factory and startup/shutdown wiring."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

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
    app.include_router(router, prefix="/api")
    return app


app = create_app()
