"""Reads the flights a route search can use.

Not a BaseRepository: a route is a path through the graph, not a stored entity.
Neo4j hands over the flights inside the search period; the cheapest route over
them is found by Dijkstra in `app.services.dijkstra`.
"""

from neo4j import AsyncDriver, RoutingControl

from app.models import Flight, RouteSearch

# A null date leaves that end of the period open.
FLIGHTS_IN_PERIOD = """
MATCH (origin:Airport)-[f:FLIGHT]->(destination:Airport)
WHERE ($departure_date IS NULL OR f.departure_date >= $departure_date)
  AND ($return_date IS NULL OR f.arrival_date <= $return_date)
RETURN {
  uuid: f.uuid,
  price: f.price,
  origin: origin.code,
  destination: destination.code,
  departure_date: toString(f.departure_date),
  arrival_date: toString(f.arrival_date)
} AS flight
"""


class RouteRepository:
    def __init__(self, driver: AsyncDriver, database: str) -> None:
        self._driver = driver
        self._database = database

    async def flights_in_period(self, search: RouteSearch) -> list[Flight]:
        records, _, _ = await self._driver.execute_query(
            FLIGHTS_IN_PERIOD,
            {
                "departure_date": search.departure_date,
                "return_date": search.return_date,
            },
            database_=self._database,
            routing_=RoutingControl.READ,
        )
        return [Flight(**record["flight"]) for record in records]
