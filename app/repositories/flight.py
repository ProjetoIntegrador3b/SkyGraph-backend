"""FLIGHT relationships, read together with the airports they connect."""

from typing import Any

from app.models import Flight, FlightFilters
from app.repositories.base import BaseRepository


class FlightRepository(BaseRepository[Flight, FlightFilters]):
    model = Flight
    pattern = "(origin:Airport)-[n:FLIGHT]->(destination:Airport)"
    key = "uuid"
    projection = (
        "{uuid: n.uuid, price: n.price, "
        "origin: origin.code, destination: destination.code}"
    )
    # Cheapest first, since price is the weight routes are chosen by.
    order_by = "n.price, n.uuid"
    # The airports are the relationship's ends, not properties: moving a flight
    # means deleting it and creating another.
    updatable = frozenset({"price"})
    create_query = (
        "MATCH (origin:Airport {code: $props.origin}) "
        "MATCH (destination:Airport {code: $props.destination}) "
        "CREATE (origin)-[n:FLIGHT {uuid: $props.uuid, price: $props.price}]"
        "->(destination)"
    )

    def _conditions(self, filters: FlightFilters) -> tuple[list[str], dict[str, Any]]:
        # Price bounds are inclusive.
        return self._set_filters(
            ("n.price >= $min_price", "min_price", filters.min_price),
            ("n.price <= $max_price", "max_price", filters.max_price),
            ("origin.code = $origin", "origin", filters.origin),
            ("destination.code = $destination", "destination", filters.destination),
        )
