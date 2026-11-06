"""Route search use case."""

from dataclasses import dataclass

from app.models import Flight, Route, RouteSearch
from app.repositories import AirportRepository, RouteRepository
from app.services.all_routes import all_routes
from app.services.dijkstra import DijkstraTrace, cheapest_route
from app.services.errors import AirportNotFoundError


@dataclass
class RouteTrace:
    """A search with every step it took, for the graph explorer."""

    search: RouteSearch
    route: Route | None
    # The flights the search ran on: those inside the period.
    flights: list[Flight]
    trace: DijkstraTrace


@dataclass
class RouteList:
    """Every route of a search, cheapest first."""

    routes: list[Route]
    # True when the search stopped at its limit, so some routes are missing.
    truncated: bool


class RouteService:
    def __init__(self, routes: RouteRepository, airports: AirportRepository) -> None:
        self._routes = routes
        self._airports = airports

    async def find_cheapest(self, search: RouteSearch) -> Route | None:
        """The cheapest route, or None when no flights in the period connect the
        airports. An unknown airport is an error rather than "no route"."""
        flights = await self._flights_for(search)
        legs = cheapest_route(flights, search.origin, search.destination)
        return Route(flights=legs) if legs else None

    async def trace_cheapest(self, search: RouteSearch) -> RouteTrace:
        """The same search as `find_cheapest`, recording every step."""
        flights = await self._flights_for(search)
        trace = DijkstraTrace()
        legs = cheapest_route(flights, search.origin, search.destination, trace)
        return RouteTrace(
            search=search,
            route=Route(flights=legs) if legs else None,
            flights=flights,
            trace=trace,
        )

    async def find_all(self, search: RouteSearch) -> RouteList:
        """Every route that fits the search, cheapest first. The first one is
        the route `find_cheapest` returns."""
        flights = await self._flights_for(search)
        result = all_routes(flights, search.origin, search.destination)
        return RouteList(
            routes=[Route(flights=legs) for legs in result.routes],
            truncated=result.truncated,
        )

    async def _flights_for(self, search: RouteSearch) -> list[Flight]:
        for code in (search.origin, search.destination):
            if await self._airports.get(code) is None:
                raise AirportNotFoundError(code)
        return await self._routes.flights_in_period(search)
