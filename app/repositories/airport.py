"""Airport nodes."""

from typing import Any

from app.models import Airport, AirportFilters
from app.repositories.base import BaseRepository


class AirportRepository(BaseRepository[Airport, AirportFilters]):
    model = Airport
    pattern = "(n:Airport)"
    key = "code"
    projection = "n {.*}"
    order_by = "n.code"  # unique, so a total order for paging
    updatable = frozenset({"name", "city", "country", "latitude", "longitude"})
    create_query = "CREATE (n:Airport) SET n = $props"

    def _conditions(self, filters: AirportFilters) -> tuple[list[str], dict[str, Any]]:
        # Exact match, ignoring case.
        return self._set_filters(
            ("toLower(n.city) = toLower($city)", "city", filters.city),
            ("toLower(n.country) = toLower($country)", "country", filters.country),
        )
