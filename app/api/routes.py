"""HTTP routes.

Handlers stay thin: they receive collaborators through dependency injection
and do no work of their own.
"""

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

from app.api.dependencies import GraphServiceDep, HelloServiceDep
from app.api.schemas import HealthResponse, HelloResponse

router = APIRouter()


@router.get("/hello", response_model=HelloResponse, tags=["hello"])
async def hello(service: HelloServiceDep) -> HelloResponse:
    return HelloResponse(message=service.greet())


@router.get("/health", response_model=HealthResponse, tags=["health"])
async def health(service: GraphServiceDep) -> JSONResponse:
    """Report whether the API can reach Neo4j.

    Returns 503 when the graph is unreachable so orchestrators can act on it.
    """
    try:
        connected = await service.verify_connectivity()
    except Exception:
        connected = False

    body = HealthResponse(
        status="ok" if connected else "degraded",
        database="up" if connected else "down",
    )
    code = status.HTTP_200_OK if connected else status.HTTP_503_SERVICE_UNAVAILABLE
    return JSONResponse(status_code=code, content=body.model_dump())
