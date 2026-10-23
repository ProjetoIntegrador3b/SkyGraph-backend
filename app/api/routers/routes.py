"""Route search endpoint."""

from fastapi import APIRouter

from app.api.dependencies import RouteServiceDep
from app.api.schemas import RouteResponse, RouteSearchResponse
from app.models import RouteSearch

router = APIRouter(prefix="/routes", tags=["routes"])


@router.post("", responses={404: {"description": "Airport not found"}})
async def find_cheapest_route(
    service: RouteServiceDep, search: RouteSearch
) -> RouteSearchResponse:
    """The cheapest route between two airports, using only flights that depart
    and arrive within the period. Either date may be left out to keep that end
    of the period open. `route` is null when none exists."""
    route = await service.find_cheapest(search)
    return RouteSearchResponse(
        route=RouteResponse.model_validate(route) if route else None
    )
