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
