"""Thin wrapper over the Neo4j driver.

Routes depend on this class rather than on the driver directly, so tests can
inject a fake without touching a real database.
"""

from neo4j import AsyncDriver


class GraphService:
    def __init__(self, driver: AsyncDriver, database: str) -> None:
        self._driver = driver
        self._database = database

    async def verify_connectivity(self) -> bool:
        """Return True when the database answers a trivial query."""
        records, _, _ = await self._driver.execute_query(
            "RETURN 1 AS ok",
            database_=self._database,
        )
        return bool(records) and records[0]["ok"] == 1
