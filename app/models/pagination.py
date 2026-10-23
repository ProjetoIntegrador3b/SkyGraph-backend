"""Pagination for the list endpoints."""

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

DEFAULT_PAGE_SIZE = 50
MAX_PAGE_SIZE = 200


class PageParams(BaseModel):
    """The page to return. Base class of every list endpoint's filters, because
    FastAPI accepts a single model for an endpoint's query parameters."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        extra="forbid",
        frozen=True,
    )

    # 1-based.
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE)

    @property
    def skip(self) -> int:
        return (self.page - 1) * self.page_size


class Page[M](BaseModel):
    """One page of results, with the total across all pages."""

    items: list[M]
    page: int
    page_size: int
    total: int
