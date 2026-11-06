"""Every route between two airports, for the frontend's "all routes" list.

A route follows the same rules as the cheapest one (app/services/dijkstra.py):
each flight departs on or after the day the previous one lands. It also never
passes through the same airport twice. A route that loops back is always
pricier than the same route waiting at that airport for free, so the cheapest
route is always in the list, first.

The routes are found by a depth-first search from the origin, one flight at a
time. On the seed data a pair of airports has up to about 2,200 routes (VCP to
EZE), found in a few milliseconds. Larger data could have far more, so the
search stops at `limit` routes; the routes it lists are then not all the
cheapest ones, and `truncated` says so.
"""

from collections import defaultdict
from dataclasses import dataclass
from datetime import date

from app.models import Flight

MAX_ROUTES = 5000


@dataclass
class AllRoutes:
    # Cheapest first; ties go to fewer flights, then the earliest arrival,
    # then the earliest departure.
    routes: list[list[Flight]]
    # True when the search stopped at the limit, so some routes are missing.
    truncated: bool


def all_routes(
    flights: list[Flight],
    origin: str,
    destination: str,
    limit: int = MAX_ROUTES,
) -> AllRoutes:
    departures: defaultdict[str, list[Flight]] = defaultdict(list)
    for flight in flights:
        departures[flight.origin].append(flight)

    found: list[list[Flight]] = []
    legs: list[Flight] = []
    visited = {origin}
    truncated = False

    def visit(airport: str, ready: date | None) -> None:
        nonlocal truncated
        for flight in departures[airport]:
            if truncated:
                return
            if ready is not None and flight.departure_date < ready:
                continue
            if flight.destination in visited:
                continue
            legs.append(flight)
            if flight.destination == destination:
                if len(found) == limit:
                    truncated = True
                else:
                    found.append(list(legs))
            else:
                visited.add(flight.destination)
                visit(flight.destination, flight.arrival_date)
                visited.remove(flight.destination)
            legs.pop()

    visit(origin, None)
    found.sort(key=_order)
    return AllRoutes(routes=found, truncated=truncated)


def _order(legs: list[Flight]) -> tuple[int, int, date, date]:
    # Whole cents, so sums compare exactly, as in Dijkstra.
    cents = sum(round(leg.price * 100) for leg in legs)
    return (cents, len(legs), legs[-1].arrival_date, legs[0].departure_date)
