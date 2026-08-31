"""The DI wiring itself: providers must build the right collaborators."""

from types import SimpleNamespace

from app.api.dependencies import get_driver, get_graph_service, get_hello_service
from app.core.config import Settings
from app.services.graph import GraphService
from app.services.hello import HelloService


def test_get_hello_service_uses_settings() -> None:
    service = get_hello_service(Settings(app_name="SkyGraph API"))

    assert isinstance(service, HelloService)
    assert service.app_name == "SkyGraph API"


def test_get_driver_reads_from_app_state() -> None:
    sentinel = object()
    request = SimpleNamespace(
        app=SimpleNamespace(state=SimpleNamespace(neo4j_driver=sentinel))
    )

    assert get_driver(request) is sentinel


def test_get_graph_service_receives_driver_and_database() -> None:
    driver = object()
    settings = Settings(neo4j_database="skygraph")

    service = get_graph_service(driver, settings)

    assert isinstance(service, GraphService)
    assert service._database == "skygraph"
