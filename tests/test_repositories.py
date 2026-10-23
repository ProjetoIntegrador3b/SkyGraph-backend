"""Repository tests against a fake driver: the queries built by BaseRepository,
the parameters sent, and the mapping of records back to models. The Cypher is
checked against a real Neo4j by hand and in the CI Docker job.
"""

from datetime import date
from typing import Any

import pytest
from neo4j import RoutingControl

from app.models import Airport, AirportFilters, FlightFilters, Page
from app.repositories import AirportRepository, FlightRepository
from tests.factories import GRU, GRU_FOR


class FakeDriver:
    """Answers with `records`, or with their count for a `get_all` total query.
    The last query is kept in `query`/`params`/`routing`, every one in `calls`."""

    def __init__(self, records: list[dict[str, Any]] | None = None) -> None:
        self.records = records or []
        self.calls: list[tuple[str, dict[str, Any]]] = []
        self.query = ""
        self.params: dict[str, Any] = {}
        self.routing: RoutingControl | None = None

    async def execute_query(
        self, query: str, params: dict[str, Any], **config: Any
    ) -> tuple:
        self.calls.append((query, params))
        self.query, self.params, self.routing = query, params, config["routing_"]
        if "AS total" in query:
            return [{"total": len(self.records)}], None, None
        return self.records, None, None


def _airports(*records: dict[str, Any]) -> tuple[AirportRepository, FakeDriver]:
    driver = FakeDriver(list(records))
    return AirportRepository(driver, "neo4j"), driver  # type: ignore[arg-type]


def _flights(*records: dict[str, Any]) -> tuple[FlightRepository, FakeDriver]:
    driver = FakeDriver(list(records))
    return FlightRepository(driver, "neo4j"), driver  # type: ignore[arg-type]


AIRPORT_ROW = {"item": GRU.model_dump()}
FLIGHT_ROW = {"item": GRU_FOR.model_dump(mode="json")}


async def test_get_reads_by_key_and_maps_the_record() -> None:
    repository, driver = _flights(FLIGHT_ROW)

    flight = await repository.get(GRU_FOR.uuid)

    assert flight == GRU_FOR
    assert "WHERE n.uuid = $key" in driver.query
    assert driver.params == {"key": str(GRU_FOR.uuid)}
    assert driver.routing == RoutingControl.READ


async def test_get_returns_none_when_missing() -> None:
    repository, _ = _airports()

    assert await repository.get("XXX") is None


async def test_get_all_returns_a_page_with_the_total() -> None:
    repository, driver = _airports(AIRPORT_ROW)

    page = await repository.get_all(AirportFilters())

    assert page == Page[Airport](items=[GRU], page=1, page_size=50, total=1)
    (count_query, count_params), (items_query, items_params) = driver.calls
    assert count_query == "MATCH (n:Airport) RETURN count(*) AS total"
    assert items_query.endswith("ORDER BY n.code SKIP $skip LIMIT $limit")
    assert count_params == {}
    assert items_params == {"skip": 0, "limit": 50}
    assert driver.routing == RoutingControl.READ


async def test_get_all_skips_to_the_requested_page() -> None:
    repository, driver = _flights(FLIGHT_ROW)

    page = await repository.get_all(FlightFilters(page=3, page_size=20))

    assert (page.page, page.page_size) == (3, 20)
    assert (driver.params["skip"], driver.params["limit"]) == (40, 20)


async def test_get_all_only_sends_the_airport_filters_that_are_set() -> None:
    repository, driver = _airports(AIRPORT_ROW)

    await repository.get_all(AirportFilters(country="Brasil"))

    for query, params in driver.calls:
        assert "toLower(n.country) = toLower($country)" in query
        assert "$city" not in query
        assert params["country"] == "Brasil"
        assert "city" not in params


async def test_get_all_combines_the_flight_filters_in_both_queries() -> None:
    repository, driver = _flights(FLIGHT_ROW)
    filters = FlightFilters(min_price=100, max_price=700, origin="gru")

    page = await repository.get_all(filters)

    assert page.items == [GRU_FOR]
    for query, params in driver.calls:
        assert (
            "WHERE n.price >= $min_price AND n.price <= $max_price "
            "AND origin.code = $origin" in query
        )
        assert {k: params[k] for k in ("min_price", "max_price", "origin")} == {
            "min_price": 100,
            "max_price": 700,
            "origin": "GRU",
        }


async def test_create_sends_the_entity_and_returns_it() -> None:
    repository, driver = _flights(FLIGHT_ROW)

    assert await repository.create(GRU_FOR) == GRU_FOR
    assert driver.query.startswith(FlightRepository.create_query)
    # Dates stay native, so the driver stores them as Neo4j dates.
    assert driver.params == {
        "props": {
            "uuid": str(GRU_FOR.uuid),
            "price": GRU_FOR.price,
            "origin": "GRU",
            "destination": "FOR",
            "departure_date": date(2027, 1, 11),
            "arrival_date": date(2027, 1, 11),
        }
    }
    assert driver.routing == RoutingControl.WRITE


async def test_create_returns_none_when_nothing_was_created() -> None:
    repository, _ = _flights()

    assert await repository.create(GRU_FOR) is None


@pytest.mark.parametrize(
    ("repository", "entity", "key", "props"),
    [
        (
            AirportRepository,
            GRU,
            "GRU",
            GRU.model_dump(exclude={"code"}),
        ),
        (
            FlightRepository,
            GRU_FOR,
            str(GRU_FOR.uuid),
            {
                "price": GRU_FOR.price,
                "departure_date": GRU_FOR.departure_date,
                "arrival_date": GRU_FOR.arrival_date,
            },
        ),
    ],
)
async def test_update_only_writes_the_updatable_properties(
    repository: type, entity: Any, key: str, props: dict[str, Any]
) -> None:
    driver = FakeDriver([{"item": entity.model_dump(mode="json")}])

    assert await repository(driver, "neo4j").update(entity) == entity
    assert "SET n += $props" in driver.query
    assert driver.params == {"key": key, "props": props}
    assert driver.routing == RoutingControl.WRITE


async def test_update_returns_none_when_missing() -> None:
    repository, _ = _airports()

    assert await repository.update(GRU) is None


@pytest.mark.parametrize(("deleted", "expected"), [(1, True), (0, False)])
async def test_delete_reports_whether_something_was_deleted(
    deleted: int, expected: bool
) -> None:
    repository, driver = _airports({"deleted": deleted})

    assert await repository.delete("GRU") is expected
    assert "DETACH DELETE n" in driver.query
    assert driver.params == {"key": "GRU"}
