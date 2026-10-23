"""Flight — a relationship from one airport to another.

Price is the only weight used to choose a route.
"""

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

    @model_validator(mode="after")
    def _check_different_airports(self) -> Self:
        if self.origin == self.destination:
            raise ValueError("origin and destination must be different airports")
        return self
