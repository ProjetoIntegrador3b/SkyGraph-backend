"""Airport endpoints."""

from typing import Annotated

from fastapi import APIRouter, Query

from app.api.dependencies import AirportServiceDep
from app.api.schemas import AirportResponse, PageResponse
from app.models import AirportFilters, IataCode

router = APIRouter(prefix="/airports", tags=["airports"])


@router.get("")
async def list_airports(
    service: AirportServiceDep,
    filters: Annotated[AirportFilters, Query()],
) -> PageResponse[AirportResponse]:
    """A page of airports, by code. Filters match exactly, ignoring case."""
    page = await service.get_all(filters)
    return PageResponse[AirportResponse].model_validate(page)


@router.get("/{code}", responses={404: {"description": "Airport not found"}})
async def get_airport(service: AirportServiceDep, code: IataCode) -> AirportResponse:
    return AirportResponse.model_validate(await service.get(code))
