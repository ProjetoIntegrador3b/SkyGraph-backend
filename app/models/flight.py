"""Flight — a relationship from one airport to another.

Price is the only weight used to choose a route. The departure and arrival days
are calendar dates in local time; a flight lands on its departure day or later.
"""

from datetime import date
from typing import Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.airport import IataCode


class Flight(BaseModel):
    model_config = ConfigDict(frozen=True)

    uuid: UUID
    price: float = Field(gt=0)
    origin: IataCode
    destination: IataCode
    departure_date: date
    arrival_date: date

    @model_validator(mode="after")
    def _check_consistency(self) -> Self:
        if self.origin == self.destination:
            raise ValueError("origin and destination must be different airports")
        if self.arrival_date < self.departure_date:
            raise ValueError("arrival_date must not be before departure_date")
        return self
