"""Flight endpoint tests, with the service replaced by a fake."""

from collections.abc import Iterator
from uuid import UUID

import pytest
from fastapi import FastAPI
from httpx import AsyncClient

from app.api.dependencies import get_flight_service
from app.models import Flight, FlightFilters, Page
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

    async def get_all(self, filters: FlightFilters) -> Page[Flight]:
        self.filters = filters
        return Page[Flight](
            items=[GRU_FOR], page=filters.page, page_size=filters.page_size, total=1
        )


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
    "departureDate": "2027-01-11",
    "arrivalDate": "2027-01-11",
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
    assert response.json() == {
        "items": [GRU_FOR_BODY],
        "page": 1,
        "pageSize": 50,
        "total": 1,
    }
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


async def test_list_flights_passes_the_page(
    client: AsyncClient, service: FakeFlightService
) -> None:
    response = await client.get("/api/flights", params={"page": 3, "pageSize": 20})

    assert response.status_code == 200
    assert (response.json()["page"], response.json()["pageSize"]) == (3, 20)
    assert service.filters == FlightFilters(page=3, page_size=20)


@pytest.mark.parametrize(
    "params", [{"page": 0}, {"pageSize": 0}, {"pageSize": 201}, {"page": "x"}]
)
async def test_list_flights_rejects_invalid_pages(
    client: AsyncClient, service: FakeFlightService, params: dict[str, object]
) -> None:
    response = await client.get("/api/flights", params=params)

    assert response.status_code == 422
