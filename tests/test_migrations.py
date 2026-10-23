"""Migration tests.

A fake driver records every query, so the runner and the data load are tested
without a database. The real-Neo4j check lives in the CI Docker job.
"""

from pathlib import Path
from typing import Any

import pytest
from asgi_lifespan import LifespanManager

from app import main
from app.core.config import Settings
from app.main import create_app
from app.migrations import MIGRATIONS, Migration, run_migrations
from app.migrations.m0002_airports_and_flights import read_airports, read_flights

CSV_DIR = Path(__file__).resolve().parents[1] / "initial_data_csv"


class FakeDriver:
    """Records queries; reports `applied` as the already-recorded migrations."""

    def __init__(self, applied: tuple[str, ...] = ()) -> None:
        self.applied = applied
        self.queries: list[tuple[str, dict[str, Any]]] = []

    async def execute_query(self, query: str, **params: Any) -> tuple:
        self.queries.append((query, params))
        if query.startswith("MATCH (m:SchemaMigration)"):
            return [{"id": migration_id} for migration_id in self.applied], None, None
        return [], None, None

    def recorded(self) -> list[str]:
        return [
            params["id"]
            for query, params in self.queries
            if query.startswith("MERGE (m:SchemaMigration")
        ]


def _migration(migration_id: str, calls: list[str], fail: bool = False) -> Migration:
    async def apply(driver: Any, settings: Settings) -> None:
        calls.append(migration_id)
        if fail:
            raise RuntimeError("boom")

    return Migration(id=migration_id, apply=apply)


@pytest.fixture
def settings() -> Settings:
    return Settings(seed_data_dir=CSV_DIR)


async def test_runs_pending_migrations_in_order(settings: Settings) -> None:
    driver, calls = FakeDriver(), []
    migrations = [_migration("0001", calls), _migration("0002", calls)]

    applied = await run_migrations(driver, settings, migrations)  # type: ignore[arg-type]

    assert applied == calls == ["0001", "0002"]
    assert driver.recorded() == ["0001", "0002"]


async def test_skips_already_applied_migrations(settings: Settings) -> None:
    driver, calls = FakeDriver(applied=("0001",)), []
    migrations = [_migration("0001", calls), _migration("0002", calls)]

    applied = await run_migrations(driver, settings, migrations)  # type: ignore[arg-type]

    assert applied == calls == ["0002"]


async def test_failed_migration_is_not_recorded_and_stops_the_run(
    settings: Settings,
) -> None:
    driver, calls = FakeDriver(), []
    migrations = [_migration("0001", calls, fail=True), _migration("0002", calls)]

    with pytest.raises(RuntimeError):
        await run_migrations(driver, settings, migrations)  # type: ignore[arg-type]

    assert calls == ["0001"]
    assert driver.recorded() == []


def test_migration_ids_are_unique() -> None:
    ids = [migration.id for migration in MIGRATIONS]

    assert len(ids) == len(set(ids))


def test_seed_csvs_are_valid_and_consistent() -> None:
    airports = read_airports(CSV_DIR / "aeroportos.csv")
    flights = read_flights(CSV_DIR / "voos.csv")

    codes = {airport.code for airport in airports}
    assert len(airports) == len(codes) == 40
    assert len(flights) == len({flight.uuid for flight in flights}) == 400
    # A flight to an unknown airport would be silently skipped by the MATCH.
    assert {flight.origin for flight in flights} <= codes
    assert {flight.destination for flight in flights} <= codes


async def test_all_migrations_send_the_seed_data(settings: Settings) -> None:
    driver = FakeDriver()

    await run_migrations(driver, settings)  # type: ignore[arg-type]

    airports = next(p["airports"] for _, p in driver.queries if "airports" in p)
    loaded, dated = (p["flights"] for _, p in driver.queries if "flights" in p)
    assert len(airports) == 40
    assert len(loaded) == len(dated) == 400
    assert loaded[0]["uuid"] == "815ef6d1-3b8f-4a18-b7f8-a88b17fc695a"
    assert loaded[0]["price"] == 682.94
    assert dated[0] == {
        "uuid": "815ef6d1-3b8f-4a18-b7f8-a88b17fc695a",
        "departure_date": "2027-01-11",
        "arrival_date": "2027-01-11",
    }
    assert driver.recorded() == [migration.id for migration in MIGRATIONS]


async def test_startup_runs_migrations(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = []

    async def fake_run(driver: Any, settings: Settings) -> list[str]:
        calls.append(settings)
        return []

    monkeypatch.setattr(main, "run_migrations", fake_run)

    async with LifespanManager(create_app(Settings())):
        pass

    assert len(calls) == 1


async def test_startup_survives_failed_migrations(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def failing_run(driver: Any, settings: Settings) -> list[str]:
        raise ConnectionError("neo4j unreachable")

    monkeypatch.setattr(main, "run_migrations", failing_run)

    async with LifespanManager(create_app(Settings())) as manager:
        assert manager.app is not None
