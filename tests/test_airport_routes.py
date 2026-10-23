"""Airport endpoint tests, with the service replaced by a fake."""

from collections.abc import Iterator

import pytest
from fastapi import FastAPI
from httpx import AsyncClient

from app.api.dependencies import get_airport_service
from app.models import Airport, AirportFilters
from app.services.errors import AirportNotFoundError
from tests.factories import GRU


class FakeAirportService:
    def __init__(self) -> None:
        self.filters: AirportFilters | None = None

    async def get(self, code: str) -> Airport:
        if code != GRU.code:
            raise AirportNotFoundError(code)
        return GRU

    async def get_all(self, filters: AirportFilters) -> list[Airport]:
        self.filters = filters
        return [GRU]


@pytest.fixture
def service(app: FastAPI) -> Iterator[FakeAirportService]:
    fake = FakeAirportService()
    app.dependency_overrides[get_airport_service] = lambda: fake
    yield fake


GRU_BODY = {
    "code": "GRU",
    "name": "Aeroporto Internacional de Guarulhos",
    "city": "São Paulo",
    "country": "Brasil",
    "latitude": -23.4356,
    "longitude": -46.4731,
}


async def test_get_airport(client: AsyncClient, service: FakeAirportService) -> None:
    response = await client.get("/api/airports/GRU")

    assert response.status_code == 200
    assert response.json() == GRU_BODY


async def test_get_airport_normalises_the_code(
    client: AsyncClient, service: FakeAirportService
) -> None:
    response = await client.get("/api/airports/gru")

    assert response.status_code == 200


async def test_get_airport_not_found(
    client: AsyncClient, service: FakeAirportService
) -> None:
    response = await client.get("/api/airports/XXX")

    assert response.status_code == 404
    assert response.json() == {"detail": "Airport XXX not found"}


async def test_get_airport_rejects_invalid_code(
    client: AsyncClient, service: FakeAirportService
) -> None:
    response = await client.get("/api/airports/GR")

    assert response.status_code == 422


async def test_list_airports(client: AsyncClient, service: FakeAirportService) -> None:
    response = await client.get("/api/airports")

    assert response.status_code == 200
    assert response.json() == [GRU_BODY]
    assert service.filters == AirportFilters()


async def test_list_airports_passes_the_filters(
    client: AsyncClient, service: FakeAirportService
) -> None:
    response = await client.get(
        "/api/airports", params={"city": "São Paulo", "country": "Brasil"}
    )

    assert response.status_code == 200
    assert service.filters == AirportFilters(city="São Paulo", country="Brasil")


async def test_list_airports_rejects_unknown_filters(
    client: AsyncClient, service: FakeAirportService
) -> None:
    response = await client.get("/api/airports", params={"state": "SP"})

    assert response.status_code == 422
