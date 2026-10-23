"""Request and response models.

Route-related schemas use camelCase on the wire to match the frontend contract
(`departureDate`, `returnDate`, ...), while staying snake_case in Python.
"""

from uuid import UUID

from pydantic import BaseModel, ConfigDict
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


class FlightResponse(CamelModel):
    uuid: UUID
    price: float
    origin: str
    destination: str
