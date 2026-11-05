"""Dijkstra's algorithm for the cheapest route, on a time-expanded flight graph.

A route must respect time: each flight departs on or after the day the
previous one lands. Plain Dijkstra over airports would keep only the cheapest
way to reach each airport, which may land too late for the next flight. So the
graph is expanded in time:

- a node is an airport on a day when a flight departs from or lands at it;
- a flight is an edge from (origin, departure day) to (destination, arrival
  day), weighted by its price;
- waiting is a free edge from (airport, day) to (same airport, its next day).

Every path in this graph is a valid itinerary, and every edge weight is
non-negative, so Dijkstra finds the cheapest route exactly, with any number of
connections. Ties go to fewer flights, then the earliest arrival.
"""

import heapq
from collections import defaultdict
from datetime import date

from app.models import Flight

Node = tuple[str, date]


def _cents(price: float) -> int:
    # Whole cents, so sums compare exactly and float noise can't break ties.
    return round(price * 100)


def cheapest_route(
    flights: list[Flight], origin: str, destination: str
) -> list[Flight] | None:
    """The legs of the cheapest route from origin to destination using only
    `flights` (already limited to the search period), or None if none exists."""
    days: dict[str, set[date]] = defaultdict(set)
    departures: dict[Node, list[Flight]] = defaultdict(list)
    for flight in flights:
        days[flight.origin].add(flight.departure_date)
        days[flight.destination].add(flight.arrival_date)
        departures[(flight.origin, flight.departure_date)].append(flight)
    if origin not in days:
        return None

    # The free "wait" edge out of each node: same airport, next day it is used.
    next_day: dict[Node, Node] = {}
    for airport, airport_days in days.items():
        ordered = sorted(airport_days)
        for today, later in zip(ordered, ordered[1:], strict=False):
            next_day[(airport, today)] = (airport, later)

    start: Node = (origin, min(days[origin]))
    # Best known (price in cents, flights) for each node, and how it was reached.
    best: dict[Node, tuple[int, int]] = {start: (0, 0)}
    came_from: dict[Node, tuple[Node, Flight | None]] = {}
    settled: set[Node] = set()
    # The queue is ordered by price, then flights, then day: the first
    # destination node taken out is the cheapest route, ties to fewer flights
    # and then to the earliest arrival.
    queue: list[tuple[int, int, date, Node]] = [(0, 0, start[1], start)]

    while queue:
        price, count, _, node = heapq.heappop(queue)
        if node in settled:
            continue
        settled.add(node)
        if node[0] == destination:
            return _legs(came_from, node)

        edges: list[tuple[Node, int, Flight | None]] = [
            ((f.destination, f.arrival_date), _cents(f.price), f)
            for f in departures.get(node, [])
        ]
        if node in next_day:
            edges.append((next_day[node], 0, None))

        for neighbour, cost, flight in edges:
            if neighbour in settled:
                continue
            candidate = (price + cost, count + (flight is not None))
            if neighbour not in best or candidate < best[neighbour]:
                best[neighbour] = candidate
                came_from[neighbour] = (node, flight)
                heapq.heappush(queue, (*candidate, neighbour[1], neighbour))

    return None


def _legs(
    came_from: dict[Node, tuple[Node, Flight | None]], node: Node
) -> list[Flight]:
    """Walk back from the destination, keeping the flights (not the waits)."""
    legs: list[Flight] = []
    while node in came_from:
        node, flight = came_from[node]
        if flight is not None:
            legs.append(flight)
    return legs[::-1]
