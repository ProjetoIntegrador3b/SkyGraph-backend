from app.services.hello import HelloService


def test_greet_returns_expected_message() -> None:
    service = HelloService(app_name="SkyGraph API")

    assert service.greet() == "Hello SkyGraphers"


def test_app_name_is_exposed() -> None:
    service = HelloService(app_name="Custom Name")

    assert service.app_name == "Custom Name"
