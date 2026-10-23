"""Filters for the list endpoints.

Every field is optional; an unset field does not filter. Each filter model also
carries the page to return. Query parameters are camelCase on the wire
(`minPrice`, `pageSize`), like the rest of the API.
"""

from typing import Self

from pydantic import Field, model_validator

from app.models.airport import IataCode
from app.models.pagination import PageParams


class AirportFilters(PageParams):
    # Matched exactly, ignoring case.
    city: str | None = None
    country: str | None = None


class FlightFilters(PageParams):
    # Both bounds are inclusive.
    min_price: float | None = Field(default=None, ge=0)
    max_price: float | None = Field(default=None, ge=0)
    origin: IataCode | None = None
    destination: IataCode | None = None

    @model_validator(mode="after")
    def _check_price_range(self) -> Self:
        if (
            self.min_price is not None
            and self.max_price is not None
            and self.min_price > self.max_price
        ):
            raise ValueError("minPrice must not be greater than maxPrice")
        return self
