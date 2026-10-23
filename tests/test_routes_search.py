"""Route search tests: the model rules, the repository against a fake driver,
the service against fake repositories, and the endpoint against a fake
service. The Cypher search itself was checked against a brute-force search on
a real Neo4j.
"""

from collections.abc import Iterator
from datetime import date
from typing import Any

import pytest
from fastapi import FastAPI
from httpx import AsyncClient
from neo4j import RoutingControl
from pydantic import ValidationError

from app.api.dependencies import get_route_service
from app.models import Route, RouteSearch
from app.repositories import RouteRepository
from app.services.errors import AirportNotFoundError
from app.services.route import RouteService
from tests.factories import FOR_GIG, GRU, GRU_FOR

SEARCH = RouteSearch(
    origin="GRU",
    destination="GIG",
    departure_date=date(2027, 1, 10),
    return_date=date(2027, 1, 20),
)
BODY = {
    "origin": "GRU",
    "destination": "GIG",
    "departureDate": "2027-01-10",
    "returnDate": "2027-01-20",
}
ROUTE = Route(flights=[GRU_FOR, FOR_GIG])


# --- model


def test_route_search_reads_the_frontend_request() -> None:
    assert RouteSearch.model_validate(BODY) == SEARCH


def test_route_search_normalises_codes() -> None:
    search = RouteSearch.model_validate(BODY | {"origin": "gru"})

    assert search.origin == "GRU"


def test_route_search_allows_a_single_day() -> None:
    RouteSearch.model_validate(BODY | {"returnDate": "2027-01-10"})


@pytest.mark.parametrize(
    ("change", "message"),
    [
        ({"destination": "GRU"}, "must be different airports"),
        ({"returnDate": "2027-01-09"}, "must not be before departureDate"),
        ({"stops": 1}, "Extra inputs"),
    ],
)
def test_route_search_rejects_invalid_searches(
    change: dict[str, Any], message: str
) -> None:
    with pytest.raises(ValidationError, match=message):
        RouteSearch.model_validate(BODY | change)


def test_route_totals() -> None:
    assert ROUTE.price == 984.95
    assert ROUTE.connections == 1
    assert (ROUTE.departure_date, ROUTE.arrival_date) == (
        date(2027, 1, 11),
        date(2027, 1, 13),
    )


def test_direct_route_has_no_connections() -> None:
    assert Route(flights=[GRU_FOR]).connections == 0


# --- repository


class FakeDriver:
    def __init__(self, records: list[dict[str, Any]]) -> None:
        self.records = records
        self.params: dict[str, Any] = {}
        self.config: dict[str, Any] = {}

    async def execute_query(
        self, query: str, params: dict[str, Any], **config: Any
    ) -> tuple:
        self.params, self.config = params, config
        return self.records, None, None


async def test_repository_sends_the_search_and_maps_the_flights() -> None:
    flights = [flight.model_dump(mode="json") for flight in ROUTE.flights]
    driver = FakeDriver([{"flights": flights}])

    route = await RouteRepository(driver, "neo4j").find_cheapest(SEARCH)  # type: ignore[arg-type]

    assert route == ROUTE
    # Dates go as native dates, so they compare with the stored Neo4j dates.
    assert driver.params == {
        "origin": "GRU",
        "destination": "GIG",
        "departure_date": date(2027, 1, 10),
        "return_date": date(2027, 1, 20),
    }
    assert driver.config["routing_"] == RoutingControl.READ


async def test_repository_returns_none_without_a_route() -> None:
    repository = RouteRepository(FakeDriver([]), "neo4j")  # type: ignore[arg-type]

    assert await repository.find_cheapest(SEARCH) is None


# --- service


class FakeRoutes:
    def __init__(self, route: Route | None) -> None:
        self.route = route
        self.search: RouteSearch | None = None

    async def find_cheapest(self, search: RouteSearch) -> Route | None:
        self.search = search
        return self.route


class FakeAirports:
    def __init__(self, missing: str | None = None) -> None:
        self.missing = missing

    async def get(self, code: str) -> Any:
        return None if code == self.missing else GRU


async def test_service_returns_the_route() -> None:
    routes = FakeRoutes(ROUTE)
    service = RouteService(routes, FakeAirports())  # type: ignore[arg-type]

    assert await service.find_cheapest(SEARCH) == ROUTE
    assert routes.search is SEARCH


async def test_service_returns_none_without_a_route() -> None:
    service = RouteService(FakeRoutes(None), FakeAirports())  # type: ignore[arg-type]

    assert await service.find_cheapest(SEARCH) is None


@pytest.mark.parametrize("missing", ["GRU", "GIG"])
async def test_service_rejects_unknown_airports(missing: str) -> None:
    routes = FakeRoutes(ROUTE)
    service = RouteService(routes, FakeAirports(missing))  # type: ignore[arg-type]

    with pytest.raises(AirportNotFoundError, match=f"Airport {missing} not found"):
        await service.find_cheapest(SEARCH)
    assert routes.search is None


# --- endpoint


class FakeRouteService:
    def __init__(self) -> None:
        self.route: Route | None = ROUTE
        self.search: RouteSearch | None = None

    async def find_cheapest(self, search: RouteSearch) -> Route | None:
        self.search = search
        if search.origin == "XXX":
            raise AirportNotFoundError("XXX")
        return self.route


@pytest.fixture
def service(app: FastAPI) -> Iterator[FakeRouteService]:
    fake = FakeRouteService()
    app.dependency_overrides[get_route_service] = lambda: fake
    yield fake


async def test_endpoint_returns_the_route(
    client: AsyncClient, service: FakeRouteService
) -> None:
    response = await client.post("/api/routes", json=BODY)

    assert response.status_code == 200
    assert response.json() == {
        "route": {
            "price": 984.95,
            "connections": 1,
            "departureDate": "2027-01-11",
            "arrivalDate": "2027-01-13",
            "legs": [
                {
                    "uuid": "815ef6d1-3b8f-4a18-b7f8-a88b17fc695a",
                    "price": 682.94,
                    "origin": "GRU",
                    "destination": "FOR",
                    "departureDate": "2027-01-11",
                    "arrivalDate": "2027-01-11",
                },
                {
                    "uuid": "0f3c2a1e-5b7d-4c9e-8a6f-1d2e3c4b5a69",
                    "price": 302.01,
                    "origin": "FOR",
                    "destination": "GIG",
                    "departureDate": "2027-01-12",
                    "arrivalDate": "2027-01-13",
                },
            ],
        }
    }
    assert service.search == SEARCH


async def test_endpoint_returns_null_without_a_route(
    client: AsyncClient, service: FakeRouteService
) -> None:
    service.route = None

    response = await client.post("/api/routes", json=BODY)

    assert response.status_code == 200
    assert response.json() == {"route": None}


async def test_endpoint_unknown_airport(
    client: AsyncClient, service: FakeRouteService
) -> None:
    response = await client.post("/api/routes", json=BODY | {"origin": "XXX"})

    assert response.status_code == 404
    assert response.json() == {"detail": "Airport XXX not found"}


@pytest.mark.parametrize(
    "change",
    [
        {"destination": "GRU"},
        {"returnDate": "2027-01-01"},
        {"departureDate": "not-a-date"},
        {"origin": "GR"},
    ],
)
async def test_endpoint_rejects_invalid_searches(
    client: AsyncClient, service: FakeRouteService, change: dict[str, Any]
) -> None:
    response = await client.post("/api/routes", json=BODY | change)

    assert response.status_code == 422
    assert service.search is None


async def test_endpoint_requires_every_field(
    client: AsyncClient, service: FakeRouteService
) -> None:
    body = {key: value for key, value in BODY.items() if key != "returnDate"}

    response = await client.post("/api/routes", json=body)

    assert response.status_code == 422
