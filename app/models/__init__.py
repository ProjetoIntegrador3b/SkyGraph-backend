"""Domain models for the flight graph.

Airports are nodes and flights are relationships between them. These models are
what the service layer works with; the API shapes them through `app.api.schemas`.
"""

from app.models.airport import Airport, IataCode
from app.models.filters import AirportFilters, FlightFilters
from app.models.flight import Flight
from app.models.pagination import Page, PageParams
from app.models.route import MAX_FLIGHTS, Route, RouteSearch

__all__ = [
    "Airport",
    "AirportFilters",
    "Flight",
    "FlightFilters",
    "IataCode",
    "MAX_FLIGHTS",
    "Page",
    "PageParams",
    "Route",
    "RouteSearch",
]
