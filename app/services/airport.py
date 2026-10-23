"""Airport use cases."""

from app.models import Airport, AirportFilters
from app.services.base import BaseService
from app.services.errors import AirportNotFoundError


class AirportService(BaseService[Airport, AirportFilters]):
    not_found = AirportNotFoundError
