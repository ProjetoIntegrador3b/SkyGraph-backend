"""Flight endpoint tests, with the service replaced by a fake."""

from collections.abc import Iterator
from uuid import UUID

import pytest
from fastapi import FastAPI
from httpx import AsyncClient

from app.api.dependencies import get_flight_service
from app.models import Flight, FlightFilters
from app.services.errors import FlightNotFoundError
from tests.factories import GRU_FOR

MISSING_UUID = "00000000-0000-0000-0000-000000000000"


class FakeFlightService:
    def __init__(self) -> None:
        self.filters: FlightFilters | None = None

    async def get(self, uuid: UUID) -> Flight:
        if uuid != GRU_FOR.uuid:
            raise FlightNotFoundError(uuid)
        return GRU_FOR

    async def get_all(self, filters: FlightFilters) -> list[Flight]:
        self.filters = filters
        return [GRU_FOR]


@pytest.fixture
def service(app: FastAPI) -> Iterator[FakeFlightService]:
    fake = FakeFlightService()
    app.dependency_overrides[get_flight_service] = lambda: fake
    yield fake


GRU_FOR_BODY = {
    "uuid": "815ef6d1-3b8f-4a18-b7f8-a88b17fc695a",
    "price": 682.94,
    "origin": "GRU",
    "destination": "FOR",
}


async def test_get_flight(client: AsyncClient, service: FakeFlightService) -> None:
    response = await client.get(f"/api/flights/{GRU_FOR.uuid}")

    assert response.status_code == 200
    assert response.json() == GRU_FOR_BODY


async def test_get_flight_not_found(
    client: AsyncClient, service: FakeFlightService
) -> None:
    response = await client.get(f"/api/flights/{MISSING_UUID}")

    assert response.status_code == 404
    assert response.json() == {"detail": f"Flight {MISSING_UUID} not found"}


async def test_get_flight_rejects_invalid_uuid(
    client: AsyncClient, service: FakeFlightService
) -> None:
    response = await client.get("/api/flights/not-a-uuid")

    assert response.status_code == 422


async def test_list_flights(client: AsyncClient, service: FakeFlightService) -> None:
    response = await client.get("/api/flights")

    assert response.status_code == 200
    assert response.json() == [GRU_FOR_BODY]
    assert service.filters == FlightFilters()


async def test_list_flights_passes_the_filters(
    client: AsyncClient, service: FakeFlightService
) -> None:
    response = await client.get(
        "/api/flights",
        params={
            "minPrice": 100,
            "maxPrice": 700,
            "origin": "gru",
            "destination": "FOR",
        },
    )

    assert response.status_code == 200
    assert service.filters == FlightFilters(
        min_price=100, max_price=700, origin="GRU", destination="FOR"
    )


@pytest.mark.parametrize(
    "params",
    [
        {"minPrice": 700, "maxPrice": 100},
        {"minPrice": -1},
        {"origin": "GR"},
        {"airline": "LATAM"},
    ],
)
async def test_list_flights_rejects_invalid_filters(
    client: AsyncClient, service: FakeFlightService, params: dict[str, object]
) -> None:
    response = await client.get("/api/flights", params=params)

    assert response.status_code == 422
