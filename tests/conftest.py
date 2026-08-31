"""Test fixtures.

The app is built through `create_app` and its Neo4j collaborators are replaced
via `dependency_overrides`, so no test needs a running database.
"""

from collections.abc import AsyncIterator, Iterator

import pytest
from asgi_lifespan import LifespanManager
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.api.dependencies import get_driver, get_graph_service
from app.core.config import Settings
from app.main import create_app


class FakeGraphService:
    """Stand-in for GraphService with controllable connectivity."""

    def __init__(self, *, connected: bool = True, raises: bool = False) -> None:
        self._connected = connected
        self._raises = raises

    async def verify_connectivity(self) -> bool:
        if self._raises:
            raise ConnectionError("neo4j unreachable")
        return self._connected


@pytest.fixture
def settings() -> Settings:
    return Settings(
        neo4j_uri="bolt://test:7687",
        neo4j_user="neo4j",
        neo4j_password="test",
    )


@pytest.fixture
def app(settings: Settings) -> Iterator[FastAPI]:
    application = create_app(settings)
    # Never build a real driver during tests.
    application.dependency_overrides[get_driver] = lambda: object()
    application.dependency_overrides[get_graph_service] = lambda: FakeGraphService()
    yield application
    application.dependency_overrides.clear()


@pytest.fixture
async def client(app: FastAPI) -> AsyncIterator[AsyncClient]:
    async with LifespanManager(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac
