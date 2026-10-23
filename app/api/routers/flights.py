"""Flight endpoints."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query

from app.api.dependencies import FlightServiceDep
from app.api.schemas import FlightResponse, PageResponse
from app.models import FlightFilters

router = APIRouter(prefix="/flights", tags=["flights"])


@router.get("")
async def list_flights(
    service: FlightServiceDep,
    filters: Annotated[FlightFilters, Query()],
) -> PageResponse[FlightResponse]:
    """A page of flights, cheapest first. Price bounds are inclusive."""
    page = await service.get_all(filters)
    return PageResponse[FlightResponse].model_validate(page)


@router.get("/{uuid}", responses={404: {"description": "Flight not found"}})
async def get_flight(service: FlightServiceDep, uuid: UUID) -> FlightResponse:
    return FlightResponse.model_validate(await service.get(uuid))
