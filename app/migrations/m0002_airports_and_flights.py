"""Load airports and flights from the CSV files in `settings.seed_data_dir`.

Every row is validated through the domain models before it reaches the
database. MERGE keeps the load idempotent, so a re-run after a partial failure
does not create duplicates.
"""

import csv
from pathlib import Path

from neo4j import AsyncDriver

from app.core.config import Settings
from app.migrations.base import Migration
from app.models import Airport, Flight

AIRPORTS_FILE = "aeroportos.csv"
FLIGHTS_FILE = "voos.csv"

MERGE_AIRPORTS = """
UNWIND $airports AS airport
MERGE (a:Airport {code: airport.code})
SET a += airport
"""

MERGE_FLIGHTS = """
UNWIND $flights AS flight
MATCH (origin:Airport {code: flight.origin})
MATCH (destination:Airport {code: flight.destination})
MERGE (origin)-[f:FLIGHT {uuid: flight.uuid}]->(destination)
SET f.price = flight.price
"""


def read_airports(path: Path) -> list[Airport]:
    with path.open(encoding="utf-8", newline="") as file:
        return [Airport(**row) for row in csv.DictReader(file)]


def read_flights(path: Path) -> list[Flight]:
    # Columns beyond the model's fields are ignored.
    with path.open(encoding="utf-8", newline="") as file:
        return [Flight(**row) for row in csv.DictReader(file)]


async def _apply(driver: AsyncDriver, settings: Settings) -> None:
    airports = read_airports(settings.seed_data_dir / AIRPORTS_FILE)
    flights = read_flights(settings.seed_data_dir / FLIGHTS_FILE)

    await driver.execute_query(
        MERGE_AIRPORTS,
        airports=[airport.model_dump(mode="json") for airport in airports],
        database_=settings.neo4j_database,
    )
    await driver.execute_query(
        MERGE_FLIGHTS,
        flights=[flight.model_dump(mode="json") for flight in flights],
        database_=settings.neo4j_database,
    )


migration = Migration(id="0002_airports_and_flights", apply=_apply)
