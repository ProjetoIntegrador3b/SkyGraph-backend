"""Domain errors raised by the service layer.

The app turns every `ServiceError` into a response with its `status_code`, so
handlers need no error handling.
"""


class ServiceError(Exception):
    status_code: int = 400


class NotFoundError(ServiceError):
    """A requested resource does not exist."""

    status_code = 404


class MissingReferenceError(ServiceError):
    """A resource refers to another one that does not exist, e.g. a flight to an
    unknown airport."""

    status_code = 422


class AirportNotFoundError(NotFoundError):
    def __init__(self, code: object) -> None:
        super().__init__(f"Airport {code} not found")


class FlightNotFoundError(NotFoundError):
    def __init__(self, uuid: object) -> None:
        super().__init__(f"Flight {uuid} not found")
