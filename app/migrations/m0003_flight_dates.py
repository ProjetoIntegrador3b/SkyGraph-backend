"""Set each flight's departure and arrival day from `voos.csv`.

Runs after 0002 on a fresh database, and adds the dates to the flights an
existing database already has. Dates are stored as Neo4j dates, so they compare
as dates in queries.
"""

from neo4j import AsyncDriver

from app.core.config import Settings
from app.migrations.base import Migration
from app.migrations.m0002_airports_and_flights import FLIGHTS_FILE, read_flights

SET_DATES = """
UNWIND $flights AS flight
MATCH ()-[f:FLIGHT {uuid: flight.uuid}]->()
SET f.departure_date = date(flight.departure_date),
    f.arrival_date = date(flight.arrival_date)
"""


async def _apply(driver: AsyncDriver, settings: Settings) -> None:
    flights = read_flights(settings.seed_data_dir / FLIGHTS_FILE)
    await driver.execute_query(
        SET_DATES,
        flights=[
            {
                "uuid": str(flight.uuid),
                "departure_date": flight.departure_date.isoformat(),
                "arrival_date": flight.arrival_date.isoformat(),
            }
            for flight in flights
        ],
        database_=settings.neo4j_database,
    )


migration = Migration(id="0003_flight_dates", apply=_apply)
