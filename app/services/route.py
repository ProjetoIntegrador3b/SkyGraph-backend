"""Route search use case."""

from app.models import Route, RouteSearch
from app.repositories import AirportRepository, RouteRepository
from app.services.errors import AirportNotFoundError


class RouteService:
    def __init__(self, routes: RouteRepository, airports: AirportRepository) -> None:
        self._routes = routes
        self._airports = airports

    async def find_cheapest(self, search: RouteSearch) -> Route | None:
        """The cheapest route, or None when no flights in the period connect the
        airports. An unknown airport is an error rather than "no route"."""
        for code in (search.origin, search.destination):
            if await self._airports.get(code) is None:
                raise AirportNotFoundError(code)
        return await self._routes.find_cheapest(search)
