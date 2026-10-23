"""Flight use cases."""

from app.models import Flight, FlightFilters
from app.services.base import BaseService
from app.services.errors import FlightNotFoundError


class FlightService(BaseService[Flight, FlightFilters]):
    not_found = FlightNotFoundError
