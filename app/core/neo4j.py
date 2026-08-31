"""Neo4j driver lifecycle.

The driver is a long-lived, connection-pooled object: exactly one is created
per process on startup and closed on shutdown.
"""

from collections.abc import AsyncIterator

from neo4j import AsyncDriver, AsyncGraphDatabase

from app.core.config import Settings


def create_driver(settings: Settings) -> AsyncDriver:
    return AsyncGraphDatabase.driver(
        settings.neo4j_uri,
        auth=(settings.neo4j_user, settings.neo4j_password),
    )


async def driver_lifespan(settings: Settings) -> AsyncIterator[AsyncDriver]:
    driver = create_driver(settings)
    try:
        yield driver
    finally:
        await driver.close()
