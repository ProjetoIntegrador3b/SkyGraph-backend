"""Airport endpoints."""

from typing import Annotated

from fastapi import APIRouter, Query

from app.api.dependencies import AirportServiceDep
from app.api.schemas import AirportResponse
from app.models import AirportFilters, IataCode

router = APIRouter(prefix="/airports", tags=["airports"])


@router.get("")
async def list_airports(
    service: AirportServiceDep,
    filters: Annotated[AirportFilters, Query()],
) -> list[AirportResponse]:
    """All airports, by code. Filters match exactly, ignoring case."""
    airports = await service.get_all(filters)
    return [AirportResponse.model_validate(airport) for airport in airports]


@router.get("/{code}", responses={404: {"description": "Airport not found"}})
async def get_airport(service: AirportServiceDep, code: IataCode) -> AirportResponse:
    return AirportResponse.model_validate(await service.get(code))
