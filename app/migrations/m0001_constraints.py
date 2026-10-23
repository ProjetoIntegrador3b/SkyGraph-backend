"""Uniqueness constraints for airports and flights.

They also back the lookups that MERGE does, so loading data stays fast.
"""

from neo4j import AsyncDriver

from app.core.config import Settings
from app.migrations.base import Migration

STATEMENTS = [
    "CREATE CONSTRAINT airport_code IF NOT EXISTS "
    "FOR (a:Airport) REQUIRE a.code IS UNIQUE",
    "CREATE CONSTRAINT flight_uuid IF NOT EXISTS "
    "FOR ()-[f:FLIGHT]-() REQUIRE f.uuid IS UNIQUE",
]


async def _apply(driver: AsyncDriver, settings: Settings) -> None:
    for statement in STATEMENTS:
        await driver.execute_query(statement, database_=settings.neo4j_database)


migration = Migration(id="0001_constraints", apply=_apply)
