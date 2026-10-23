"""Flight endpoints."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query

from app.api.dependencies import FlightServiceDep
from app.api.schemas import FlightResponse
from app.models import FlightFilters

router = APIRouter(prefix="/flights", tags=["flights"])


@router.get("")
async def list_flights(
    service: FlightServiceDep,
    filters: Annotated[FlightFilters, Query()],
) -> list[FlightResponse]:
    """All flights, cheapest first. Price bounds are inclusive."""
    flights = await service.get_all(filters)
    return [FlightResponse.model_validate(flight) for flight in flights]


@router.get("/{uuid}", responses={404: {"description": "Flight not found"}})
async def get_flight(service: FlightServiceDep, uuid: UUID) -> FlightResponse:
    return FlightResponse.model_validate(await service.get(uuid))
