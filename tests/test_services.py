"""BaseService tests, through the concrete services, with a fake repository."""

from typing import Any

import pytest
from fastapi import FastAPI
from httpx import AsyncClient

from app.models import AirportFilters, Page
from app.services.airport import AirportService
from app.services.errors import (
    AirportNotFoundError,
    FlightNotFoundError,
    MissingReferenceError,
    NotFoundError,
)
from app.services.flight import FlightService
from tests.factories import GRU, GRU_FOR


class FakeRepository:
    """Answers every call with `item`; `found` controls update and delete."""

    def __init__(self, key: str, item: Any = None, found: bool = True) -> None:
        self.key = key
        self.item = item
        self.found = found
        self.filters: Any = None

    async def get(self, key: object) -> Any:
        return self.item

    async def get_all(self, filters: Any) -> Any:
        self.filters = filters
        return Page(
            items=[self.item], page=filters.page, page_size=filters.page_size, total=1
        )

    async def create(self, entity: Any) -> Any:
        return self.item

    async def update(self, entity: Any) -> Any:
        return entity if self.found else None

    async def delete(self, key: object) -> bool:
        return self.found


def _airports(item: Any = None, found: bool = True) -> AirportService:
    return AirportService(FakeRepository("code", item, found))  # type: ignore[arg-type]


def _flights(item: Any = None, found: bool = True) -> FlightService:
    return FlightService(FakeRepository("uuid", item, found))  # type: ignore[arg-type]


async def test_get_returns_the_entity() -> None:
    assert await _airports(GRU).get("GRU") == GRU
    assert await _flights(GRU_FOR).get(GRU_FOR.uuid) == GRU_FOR


async def test_get_raises_the_service_specific_not_found() -> None:
    with pytest.raises(AirportNotFoundError, match="Airport XXX not found"):
        await _airports().get("XXX")
    with pytest.raises(FlightNotFoundError, match=str(GRU_FOR.uuid)):
        await _flights().get(GRU_FOR.uuid)


async def test_get_all_passes_the_filters() -> None:
    service = _airports(GRU)
    filters = AirportFilters(country="Brasil")

    page = await service.get_all(filters)

    assert page.items == [GRU]
    assert service._repository.filters is filters  # type: ignore[attr-defined]


async def test_create_returns_the_created_entity() -> None:
    assert await _flights(GRU_FOR).create(GRU_FOR) == GRU_FOR


async def test_create_raises_when_a_reference_is_missing() -> None:
    with pytest.raises(MissingReferenceError, match=f"Flight {GRU_FOR.uuid} refers"):
        await _flights().create(GRU_FOR)


async def test_update_returns_the_updated_entity() -> None:
    assert await _airports().update(GRU) == GRU


async def test_update_raises_not_found_with_the_entity_key() -> None:
    with pytest.raises(AirportNotFoundError, match="Airport GRU not found"):
        await _airports(found=False).update(GRU)


async def test_delete() -> None:
    assert await _flights().delete(GRU_FOR.uuid) is None


async def test_delete_raises_not_found() -> None:
    with pytest.raises(FlightNotFoundError):
        await _flights(found=False).delete(GRU_FOR.uuid)


@pytest.mark.parametrize(
    ("error", "status_code"),
    [
        (NotFoundError("gone"), 404),
        (MissingReferenceError("dangling"), 422),
    ],
)
async def test_service_errors_become_responses(
    app: FastAPI, client: AsyncClient, error: Exception, status_code: int
) -> None:
    @app.get("/test-error")
    async def raise_error() -> None:
        raise error

    response = await client.get("/test-error")

    assert response.status_code == status_code
    assert response.json() == {"detail": str(error)}
