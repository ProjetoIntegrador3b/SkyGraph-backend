"""Dependency providers.

Every provider here is overridable via `app.dependency_overrides`, which is how
the test suite swaps the real Neo4j driver for a fake one.
"""

from typing import Annotated

from fastapi import Depends, Request
from neo4j import AsyncDriver

from app.core.config import Settings, get_settings
from app.repositories import AirportRepository, FlightRepository, RouteRepository
from app.services.airport import AirportService
from app.services.flight import FlightService
from app.services.graph import GraphService
from app.services.hello import HelloService
from app.services.route import RouteService

SettingsDep = Annotated[Settings, Depends(get_settings)]


def get_driver(request: Request) -> AsyncDriver:
    """The driver created during app startup and stored on the app state."""
    return request.app.state.neo4j_driver


DriverDep = Annotated[AsyncDriver, Depends(get_driver)]


def get_hello_service(settings: SettingsDep) -> HelloService:
    return HelloService(app_name=settings.app_name)


HelloServiceDep = Annotated[HelloService, Depends(get_hello_service)]


def get_graph_service(driver: DriverDep, settings: SettingsDep) -> GraphService:
    return GraphService(driver=driver, database=settings.neo4j_database)


GraphServiceDep = Annotated[GraphService, Depends(get_graph_service)]


def get_airport_repository(
    driver: DriverDep, settings: SettingsDep
) -> AirportRepository:
    return AirportRepository(driver=driver, database=settings.neo4j_database)


def get_airport_service(
    repository: Annotated[AirportRepository, Depends(get_airport_repository)],
) -> AirportService:
    return AirportService(repository=repository)


AirportServiceDep = Annotated[AirportService, Depends(get_airport_service)]


def get_flight_repository(driver: DriverDep, settings: SettingsDep) -> FlightRepository:
    return FlightRepository(driver=driver, database=settings.neo4j_database)


def get_flight_service(
    repository: Annotated[FlightRepository, Depends(get_flight_repository)],
) -> FlightService:
    return FlightService(repository=repository)


FlightServiceDep = Annotated[FlightService, Depends(get_flight_service)]


def get_route_repository(driver: DriverDep, settings: SettingsDep) -> RouteRepository:
    return RouteRepository(driver=driver, database=settings.neo4j_database)


def get_route_service(
    routes: Annotated[RouteRepository, Depends(get_route_repository)],
    airports: Annotated[AirportRepository, Depends(get_airport_repository)],
) -> RouteService:
    return RouteService(routes=routes, airports=airports)


RouteServiceDep = Annotated[RouteService, Depends(get_route_service)]
