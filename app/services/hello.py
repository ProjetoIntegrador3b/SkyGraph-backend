"""Greeting logic, kept out of the route handler so it can be unit tested
and swapped through dependency injection.
"""


class HelloService:
    def __init__(self, app_name: str) -> None:
        self._app_name = app_name

    def greet(self) -> str:
        return "Hello SkyGraphers"

    @property
    def app_name(self) -> str:
        return self._app_name
