"""Generic CRUD over one kind of graph entity.

An entity is either a node (Airport) or a relationship (Flight), so the base
class cannot assume a shape. Each subclass describes its entity through the
class attributes below, binding it as `n` in `pattern`, and the base class
builds every query from them. They are fixed strings, never user input; all
values travel as query parameters.
"""

from typing import Any

from neo4j import AsyncDriver, Record, RoutingControl
from pydantic import BaseModel

from app.models import Page, PageParams


class BaseRepository[M: BaseModel, F: PageParams]:
    model: type[M]
    # MATCH pattern that binds the entity as `n`.
    pattern: str
    # Property that identifies one entity.
    key: str
    # Map expression turned into `model` for each row.
    projection: str
    order_by: str
    # Properties `update` may change; the key is never one of them.
    updatable: frozenset[str]
    # Creates the entity from `$props` and binds it as `n`.
    create_query: str

    def __init__(self, driver: AsyncDriver, database: str) -> None:
        self._driver = driver
        self._database = database

    async def get(self, key: object) -> M | None:
        records = await self._run(
            f"MATCH {self.pattern} WHERE n.{self.key} = $key "
            f"RETURN {self.projection} AS item",
            routing=RoutingControl.READ,
            key=str(key),
        )
        return self._first(records)

    async def get_all(self, filters: F) -> Page[M]:
        """The page of entities that `filters` asks for. `order_by` must be a
        total order, so pages neither overlap nor skip entities."""
        conditions, params = self._conditions(filters)
        match = f"MATCH {self.pattern} "
        if conditions:
            match += f"WHERE {' AND '.join(conditions)} "

        totals = await self._run(
            f"{match}RETURN count(*) AS total",
            routing=RoutingControl.READ,
            **params,
        )
        records = await self._run(
            f"{match}RETURN {self.projection} AS item ORDER BY {self.order_by} "
            "SKIP $skip LIMIT $limit",
            routing=RoutingControl.READ,
            skip=filters.skip,
            limit=filters.page_size,
            **params,
        )
        return Page[M](
            items=[self.model(**record["item"]) for record in records],
            page=filters.page,
            page_size=filters.page_size,
            total=totals[0]["total"],
        )

    async def create(self, entity: M) -> M | None:
        """Return the created entity, or None when the query matched nothing to
        attach it to (e.g. a flight whose airport does not exist)."""
        records = await self._run(
            f"{self.create_query} RETURN {self.projection} AS item",
            props=entity.model_dump(mode="json"),
        )
        return self._first(records)

    async def update(self, entity: M) -> M | None:
        """Write the `updatable` properties of `entity`; None if it does not exist."""
        props = {
            name: value
            for name, value in entity.model_dump(mode="json").items()
            if name in self.updatable
        }
        records = await self._run(
            f"MATCH {self.pattern} WHERE n.{self.key} = $key SET n += $props "
            f"RETURN {self.projection} AS item",
            key=str(getattr(entity, self.key)),
            props=props,
        )
        return self._first(records)

    async def delete(self, key: object) -> bool:
        """Return whether something was deleted. Deleting a node also deletes
        its relationships, so removing an airport removes its flights."""
        records = await self._run(
            f"MATCH {self.pattern} WHERE n.{self.key} = $key "
            "DETACH DELETE n RETURN count(*) AS deleted",
            key=str(key),
        )
        return records[0]["deleted"] > 0

    def _conditions(self, filters: F) -> tuple[list[str], dict[str, Any]]:
        """WHERE conditions and their parameters for `get_all`; none by default."""
        return [], {}

    @staticmethod
    def _set_filters(
        *candidates: tuple[str, str, object],
    ) -> tuple[list[str], dict[str, Any]]:
        """Keep the `(condition, parameter, value)` triples whose value is set."""
        conditions, params = [], {}
        for condition, name, value in candidates:
            if value is not None:
                conditions.append(condition)
                params[name] = value
        return conditions, params

    async def _run(
        self,
        query: str,
        routing: RoutingControl = RoutingControl.WRITE,
        **params: Any,
    ) -> list[Record]:
        records, _, _ = await self._driver.execute_query(
            query, params, database_=self._database, routing_=routing
        )
        return records

    def _first(self, records: list[Record]) -> M | None:
        return self.model(**records[0]["item"]) if records else None
