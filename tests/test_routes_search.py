"""Route search tests: the model rules, the repository against a fake driver,
the service against fake repositories, and the endpoint against a fake
service. Dijkstra itself is tested in test_dijkstra.py.
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
from app.models import Flight, Route, RouteSearch
from app.repositories import RouteRepository
from app.services.dijkstra import DijkstraTrace, cheapest_route
from app.services.errors import AirportNotFoundError
from app.services.route import RouteService, RouteTrace
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


def test_route_search_dates_are_optional() -> None:
    search = RouteSearch(origin="GRU", destination="GIG")

    assert (search.departure_date, search.return_date) == (None, None)


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


async def test_repository_reads_the_flights_in_the_period() -> None:
    driver = FakeDriver([{"flight": f.model_dump(mode="json")} for f in ROUTE.flights])

    flights = await RouteRepository(driver, "neo4j").flights_in_period(SEARCH)  # type: ignore[arg-type]

    assert flights == ROUTE.flights
    # Dates go as native dates, so they compare with the stored Neo4j dates.
    assert driver.params == {
        "departure_date": date(2027, 1, 10),
        "return_date": date(2027, 1, 20),
    }
    assert driver.config["routing_"] == RoutingControl.READ


async def test_repository_sends_null_for_an_open_end() -> None:
    driver = FakeDriver([])
    search = RouteSearch(
        origin="GRU", destination="GIG", departure_date=date(2027, 1, 10)
    )

    await RouteRepository(driver, "neo4j").flights_in_period(search)  # type: ignore[arg-type]

    assert driver.params["departure_date"] == date(2027, 1, 10)
    assert driver.params["return_date"] is None


# --- service


class FakeRoutes:
    """Hands the service a fixed set of flights, as Neo4j would."""

    def __init__(self, flights: list[Flight]) -> None:
        self.flights = flights
        self.search: RouteSearch | None = None

    async def flights_in_period(self, search: RouteSearch) -> list[Flight]:
        self.search = search
        return self.flights


class FakeAirports:
    def __init__(self, missing: str | None = None) -> None:
        self.missing = missing

    async def get(self, code: str) -> Any:
        return None if code == self.missing else GRU


async def test_service_returns_the_cheapest_route_over_the_flights() -> None:
    routes = FakeRoutes(ROUTE.flights)
    service = RouteService(routes, FakeAirports())  # type: ignore[arg-type]

    assert await service.find_cheapest(SEARCH) == ROUTE
    assert routes.search is SEARCH


async def test_service_returns_none_without_a_route() -> None:
    # Only the first leg: nothing reaches GIG.
    service = RouteService(FakeRoutes([GRU_FOR]), FakeAirports())  # type: ignore[arg-type]

    assert await service.find_cheapest(SEARCH) is None


async def test_service_traces_the_same_search() -> None:
    routes = FakeRoutes(ROUTE.flights)
    service = RouteService(routes, FakeAirports())  # type: ignore[arg-type]

    result = await service.trace_cheapest(SEARCH)

    assert result.route == ROUTE
    assert result.flights == ROUTE.flights
    assert result.trace.path == [
        "GRU|2027-01-11",
        "FOR|2027-01-11",
        "FOR|2027-01-12",
        "GIG|2027-01-13",
    ]
    assert routes.search is SEARCH


async def test_service_trace_rejects_unknown_airports() -> None:
    service = RouteService(FakeRoutes(ROUTE.flights), FakeAirports("GIG"))  # type: ignore[arg-type]

    with pytest.raises(AirportNotFoundError):
        await service.trace_cheapest(SEARCH)


@pytest.mark.parametrize("missing", ["GRU", "GIG"])
async def test_service_rejects_unknown_airports(missing: str) -> None:
    routes = FakeRoutes(ROUTE.flights)
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

    async def trace_cheapest(self, search: RouteSearch) -> RouteTrace:
        self.search = search
        if search.origin == "XXX":
            raise AirportNotFoundError("XXX")
        trace = DijkstraTrace()
        legs = cheapest_route(ROUTE.flights, search.origin, search.destination, trace)
        return RouteTrace(
            search=search,
            route=Route(flights=legs) if legs else None,
            flights=ROUTE.flights,
            trace=trace,
        )


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


@pytest.mark.parametrize("missing", ["origin", "destination"])
async def test_endpoint_requires_both_airports(
    client: AsyncClient, service: FakeRouteService, missing: str
) -> None:
    body = {key: value for key, value in BODY.items() if key != missing}

    response = await client.post("/api/routes", json=body)

    assert response.status_code == 422


@pytest.mark.parametrize(
    ("body", "departure", "arrival"),
    [
        ({"departureDate": "2027-01-10"}, date(2027, 1, 10), None),
        ({"returnDate": "2027-01-20"}, None, date(2027, 1, 20)),
        ({"departureDate": None, "returnDate": None}, None, None),
        ({}, None, None),
    ],
)
async def test_endpoint_accepts_open_periods(
    client: AsyncClient,
    service: FakeRouteService,
    body: dict[str, Any],
    departure: date | None,
    arrival: date | None,
) -> None:
    airports = {"origin": "GRU", "destination": "GIG"}

    response = await client.post("/api/routes", json=airports | body)

    assert response.status_code == 200
    assert service.search is not None
    assert (service.search.departure_date, service.search.return_date) == (
        departure,
        arrival,
    )


# --- trace endpoint


async def test_trace_endpoint_returns_the_route_and_its_steps(
    client: AsyncClient, service: FakeRouteService
) -> None:
    response = await client.post("/api/routes/trace", json=BODY)

    assert response.status_code == 200
    body = response.json()
    assert body["route"]["price"] == 984.95
    trace = body["trace"]
    assert (trace["origin"], trace["destination"]) == ("GRU", "GIG")
    assert trace["start"] == "GRU|2027-01-11"
    assert trace["nodes"][0] == {
        "key": "GRU|2027-01-11",
        "airport": "GRU",
        "day": "2027-01-11",
    }
    assert trace["waits"] == [{"from": "FOR|2027-01-11", "to": "FOR|2027-01-12"}]
    assert [flight["uuid"] for flight in trace["flights"]] == [
        str(GRU_FOR.uuid),
        str(FOR_GIG.uuid),
    ]
    assert trace["steps"][0] == {
        "node": "GRU|2027-01-11",
        "cents": 0,
        "flights": 0,
        "relaxed": [
            {
                "to": "FOR|2027-01-11",
                "flight": str(GRU_FOR.uuid),
                "cents": 68294,
                "flights": 1,
                "improved": True,
            }
        ],
    }
    assert trace["path"][-1] == "GIG|2027-01-13"
    assert service.search == SEARCH


async def test_trace_endpoint_unknown_airport(
    client: AsyncClient, service: FakeRouteService
) -> None:
    response = await client.post("/api/routes/trace", json=BODY | {"origin": "XXX"})

    assert response.status_code == 404
    assert response.json() == {"detail": "Airport XXX not found"}


async def test_trace_endpoint_rejects_invalid_searches(
    client: AsyncClient, service: FakeRouteService
) -> None:
    response = await client.post(
        "/api/routes/trace", json=BODY | {"destination": "GRU"}
    )

    assert response.status_code == 422


async def test_large_responses_are_compressed(
    client: AsyncClient, service: FakeRouteService
) -> None:
    response = await client.post(
        "/api/routes/trace", json=BODY, headers={"Accept-Encoding": "gzip"}
    )

    assert response.headers["content-encoding"] == "gzip"
    assert response.json()["trace"]["start"] == "GRU|2027-01-11"
