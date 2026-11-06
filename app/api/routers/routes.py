"""Route search endpoint."""

from fastapi import APIRouter

from app.api.dependencies import RouteServiceDep
from app.api.schemas import (
    RouteListResponse,
    RouteResponse,
    RouteSearchResponse,
    RouteTraceResponse,
    TraceResponse,
)
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


@router.post("/all", responses={404: {"description": "Airport not found"}})
async def find_all_routes(
    service: RouteServiceDep, search: RouteSearch
) -> RouteListResponse:
    """Every route that fits the same search as `POST /routes`, cheapest first.
    A route never passes through the same airport twice, and each flight
    departs on or after the day the previous one lands. The first route is the
    one `POST /routes` returns. Lists at most 5000 routes; `truncated` says
    whether there were more."""
    result = await service.find_all(search)
    return RouteListResponse(
        routes=[RouteResponse.model_validate(route) for route in result.routes],
        truncated=result.truncated,
    )


@router.post("/trace", responses={404: {"description": "Airport not found"}})
async def trace_cheapest_route(
    service: RouteServiceDep, search: RouteSearch
) -> RouteTraceResponse:
    """The same search as `POST /routes`, with every step Dijkstra took: the
    time-expanded graph (`nodes`, `flights` and `waits`), each node taken from
    the priority queue with the edges it relaxed (`steps`), and the nodes of
    the cheapest route (`path`). Used by the frontend's graph explorer."""
    result = await service.trace_cheapest(search)
    trace = TraceResponse.model_validate(
        {
            "origin": search.origin,
            "destination": search.destination,
            "nodes": result.trace.nodes,
            "flights": result.flights,
            "waits": [
                {"from": wait.from_, "to": wait.to} for wait in result.trace.waits
            ],
            "start": result.trace.start,
            "steps": result.trace.steps,
            "path": result.trace.path,
        }
    )
    return RouteTraceResponse(
        route=RouteResponse.model_validate(result.route) if result.route else None,
        trace=trace,
    )
