"""Apply pending migrations in order."""

from neo4j import AsyncDriver

from app.core.config import Settings
from app.migrations import (
    m0001_constraints,
    m0002_airports_and_flights,
    m0003_flight_dates,
)
from app.migrations.base import Migration

# Append new migrations at the end; the order here is the order they run in.
MIGRATIONS: list[Migration] = [
    m0001_constraints.migration,
    m0002_airports_and_flights.migration,
    m0003_flight_dates.migration,
]


async def run_migrations(
    driver: AsyncDriver,
    settings: Settings,
    migrations: list[Migration] = MIGRATIONS,
) -> list[str]:
    """Apply every migration not yet recorded, and return the ids applied.

    A migration is recorded only after it succeeds, so a failed one stops the
    run and is retried next time. Migrations must therefore be safe to re-run.
    """
    database = settings.neo4j_database
    await driver.execute_query(
        "CREATE CONSTRAINT schema_migration_id IF NOT EXISTS "
        "FOR (m:SchemaMigration) REQUIRE m.id IS UNIQUE",
        database_=database,
    )
    records, _, _ = await driver.execute_query(
        "MATCH (m:SchemaMigration) RETURN m.id AS id",
        database_=database,
    )
    already_applied = {record["id"] for record in records}

    applied = []
    for migration in migrations:
        if migration.id in already_applied:
            continue
        await migration.apply(driver, settings)
        await driver.execute_query(
            "MERGE (m:SchemaMigration {id: $id}) "
            "ON CREATE SET m.applied_at = datetime()",
            id=migration.id,
            database_=database,
        )
        applied.append(migration.id)
    return applied
