"""Request and response models.

Route-related schemas use camelCase on the wire to match the frontend contract
(`departureDate`, `returnDate`, ...), while staying snake_case in Python.
"""

from datetime import date
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


class HelloResponse(BaseModel):
    message: str


class HealthResponse(BaseModel):
    status: str
    database: str


class CamelModel(BaseModel):
    """Base for schemas exchanged with the frontend."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )


class AirportResponse(CamelModel):
    code: str
    name: str
    city: str
    country: str
    latitude: float
    longitude: float


class PageResponse[T](CamelModel):
    items: list[T]
    page: int
    page_size: int
    # Matching items across all pages.
    total: int


class FlightResponse(CamelModel):
    uuid: UUID
    price: float
    origin: str
    destination: str
    departure_date: date
    arrival_date: date


class RouteResponse(CamelModel):
    price: float
    connections: int
    # First departure and last arrival.
    departure_date: date
    arrival_date: date
    legs: list[FlightResponse] = Field(validation_alias="flights")


class RouteSearchResponse(CamelModel):
    # None when no route fits the search.
    route: RouteResponse | None


class RouteListResponse(CamelModel):
    # Cheapest first; empty when no route fits the search.
    routes: list[RouteResponse]
    # True when there were more routes than the search lists.
    truncated: bool


# --- Route trace: the search step by step, for the graph explorer.
# A node is "AIRPORT|YYYY-MM-DD"; prices are in whole cents, as the search
# compares them.


class TraceNodeResponse(CamelModel):
    key: str
    airport: str
    day: date


class TraceWaitResponse(CamelModel):
    # "from" is a Python keyword.
    from_: str = Field(alias="from")
    to: str


class TraceRelaxResponse(CamelModel):
    to: str
    # The uuid of the flight taken, or null for a wait at the same airport.
    flight: UUID | None
    cents: int
    flights: int
    improved: bool


class TraceStepResponse(CamelModel):
    node: str
    cents: int
    flights: int
    relaxed: list[TraceRelaxResponse]


class TraceResponse(CamelModel):
    origin: str
    destination: str
    nodes: list[TraceNodeResponse]
    flights: list[FlightResponse]
    waits: list[TraceWaitResponse]
    start: str | None
    steps: list[TraceStepResponse]
    path: list[str] | None


class RouteTraceResponse(CamelModel):
    route: RouteResponse | None
    trace: TraceResponse
