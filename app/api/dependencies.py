"""Dependency providers.

Every provider here is overridable via `app.dependency_overrides`, which is how
the test suite swaps the real Neo4j driver for a fake one.
"""

from typing import Annotated

from fastapi import Depends, Request
from neo4j import AsyncDriver

from app.core.config import Settings, get_settings
from app.services.graph import GraphService
from app.services.hello import HelloService

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
