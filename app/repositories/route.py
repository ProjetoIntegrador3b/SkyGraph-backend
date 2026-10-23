"""Finds the cheapest route through the FLIGHT relationships.

Not a BaseRepository: a route is a path through the graph, not a stored entity.
"""

from neo4j import AsyncDriver, RoutingControl

from app.models import MAX_FLIGHTS, Flight, Route, RouteSearch

# The quantified path pattern only walks flights inside the period, so the
# search never expands past one that could not be used. Connections are checked
# on the whole path: each flight departs on or after the previous one arrives
# (remove that WHERE to allow any order). Prices are positive, so the cheapest
# path never visits an airport twice. Ties go to the fewest flights, then the
# earliest arrival.
CHEAPEST = f"""
MATCH (:Airport {{code: $origin}})
      (()-[f:FLIGHT WHERE f.departure_date >= $departure_date
                      AND f.arrival_date <= $return_date]->()){{1,{MAX_FLIGHTS}}}
      (:Airport {{code: $destination}})
WHERE all(i IN range(0, size(f) - 2)
          WHERE f[i + 1].departure_date >= f[i].arrival_date)
WITH f, reduce(total = 0.0, flight IN f | total + flight.price) AS price
ORDER BY price, size(f), f[-1].arrival_date
LIMIT 1
RETURN [flight IN f | {{
  uuid: flight.uuid,
  price: flight.price,
  origin: startNode(flight).code,
  destination: endNode(flight).code,
  departure_date: toString(flight.departure_date),
  arrival_date: toString(flight.arrival_date)
}}] AS flights
"""


class RouteRepository:
    def __init__(self, driver: AsyncDriver, database: str) -> None:
        self._driver = driver
        self._database = database

    async def find_cheapest(self, search: RouteSearch) -> Route | None:
        records, _, _ = await self._driver.execute_query(
            CHEAPEST,
            {
                "origin": search.origin,
                "destination": search.destination,
                "departure_date": search.departure_date,
                "return_date": search.return_date,
            },
            database_=self._database,
            routing_=RoutingControl.READ,
        )
        if not records:
            return None
        return Route(flights=[Flight(**flight) for flight in records[0]["flights"]])
