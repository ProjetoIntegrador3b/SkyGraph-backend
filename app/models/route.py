"""Route search — the cheapest way from one airport to another in a period.

A route is a chain of flights. Only flights that depart and arrive within the
period are used, and each flight must depart on or after the day the previous
one arrives. Price is the only weight.
"""

from datetime import date
from typing import Self

from pydantic import BaseModel, ConfigDict, model_validator
from pydantic.alias_generators import to_camel

from app.models.airport import IataCode
from app.models.flight import Flight

# Longest route considered: 4 flights, 3 connections. Bounds the graph search.
MAX_FLIGHTS = 4


class RouteSearch(BaseModel):
    # camelCase on the wire, matching the frontend's request.
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        extra="forbid",
        frozen=True,
    )

    origin: IataCode
    destination: IataCode
    # The period: every flight departs on or after departure_date and arrives
    # on or before return_date.
    departure_date: date
    return_date: date

    @model_validator(mode="after")
    def _check_consistency(self) -> Self:
        if self.origin == self.destination:
            raise ValueError("origin and destination must be different airports")
        if self.return_date < self.departure_date:
            raise ValueError("returnDate must not be before departureDate")
        return self


class Route(BaseModel):
    model_config = ConfigDict(frozen=True)

    flights: list[Flight]

    @property
    def price(self) -> float:
        return round(sum(flight.price for flight in self.flights), 2)

    @property
    def connections(self) -> int:
        return len(self.flights) - 1

    @property
    def departure_date(self) -> date:
        return self.flights[0].departure_date

    @property
    def arrival_date(self) -> date:
        return self.flights[-1].arrival_date
