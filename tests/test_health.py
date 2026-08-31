"""Health route tests.

Each case swaps the injected GraphService, which is the point of the
dependency-injection layer: the route is tested without a database.
"""

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.api.dependencies import get_graph_service
from tests.conftest import FakeGraphService


async def _get_health(app: FastAPI) -> tuple[int, dict]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/health")
    return response.status_code, response.json()


async def test_health_ok_when_database_reachable(client: AsyncClient) -> None:
    response = await client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "up"}


async def test_health_degraded_when_database_unreachable(app: FastAPI) -> None:
    app.dependency_overrides[get_graph_service] = lambda: FakeGraphService(
        connected=False
    )

    status_code, body = await _get_health(app)

    assert status_code == 503
    assert body == {"status": "degraded", "database": "down"}


async def test_health_degraded_when_driver_raises(app: FastAPI) -> None:
    app.dependency_overrides[get_graph_service] = lambda: FakeGraphService(raises=True)

    status_code, body = await _get_health(app)

    assert status_code == 503
    assert body["database"] == "down"
