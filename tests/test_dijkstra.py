"""Dijkstra on the time-expanded flight graph.

Checked separately against an exhaustive search on every airport pair of the
seed data; these cases pin the rules one by one.
"""

from datetime import date
from uuid import uuid4

from app.models import Flight
from app.services.dijkstra import DijkstraTrace, cheapest_route


def flight(
    origin: str, destination: str, price: float, day: int, lands: int = 0
) -> Flight:
    """A flight departing on 2027-01-<day> and landing `lands` days later."""
    return Flight(
        uuid=uuid4(),
        price=price,
        origin=origin,
        destination=destination,
        departure_date=date(2027, 1, day),
        arrival_date=date(2027, 1, day + lands),
    )


def codes(legs: list[Flight] | None) -> list[str] | None:
    if legs is None:
        return None
    return [legs[0].origin, *(leg.destination for leg in legs)]


def test_picks_the_cheapest_route_over_the_direct_flight() -> None:
    direct = flight("GRU", "JFK", 3000, 5)
    via_mia = [flight("GRU", "MIA", 900, 5), flight("MIA", "JFK", 400, 6)]

    assert codes(cheapest_route([direct, *via_mia], "GRU", "JFK")) == [
        "GRU",
        "MIA",
        "JFK",
    ]


def test_a_connection_must_depart_on_or_after_the_landing() -> None:
    # The cheap second leg leaves before the first one lands.
    first = flight("GRU", "MIA", 900, 5, lands=1)
    too_early = flight("MIA", "JFK", 100, 5)
    on_time = flight("MIA", "JFK", 700, 6)

    legs = cheapest_route([first, too_early, on_time], "GRU", "JFK")

    assert legs == [first, on_time]


def test_connects_on_the_landing_day() -> None:
    legs = cheapest_route(
        [flight("GRU", "MIA", 900, 5), flight("MIA", "JFK", 400, 5)], "GRU", "JFK"
    )

    assert codes(legs) == ["GRU", "MIA", "JFK"]


def test_waits_at_an_airport_for_a_later_flight() -> None:
    legs = cheapest_route(
        [flight("GRU", "MIA", 900, 5), flight("MIA", "JFK", 400, 20)], "GRU", "JFK"
    )

    assert codes(legs) == ["GRU", "MIA", "JFK"]


def test_keeps_a_pricier_arrival_when_only_it_makes_the_connection() -> None:
    # Plain Dijkstra over airports would keep only the R$ 100 way into MIA,
    # which lands after the only flight onwards has left.
    cheap_late = flight("GRU", "MIA", 100, 9)
    pricier_early = flight("GRU", "MIA", 500, 3)
    onwards = flight("MIA", "JFK", 400, 5)

    legs = cheapest_route([cheap_late, pricier_early, onwards], "GRU", "JFK")

    assert legs == [pricier_early, onwards]


def test_has_no_limit_on_connections() -> None:
    chain = [
        flight(a, b, 100, day)
        for day, (a, b) in enumerate(
            [
                ("GRU", "BSB"),
                ("BSB", "BEL"),
                ("BEL", "BOG"),
                ("BOG", "MEX"),
                ("MEX", "MIA"),
                ("MIA", "JFK"),
            ],
            start=1,
        )
    ]
    direct = flight("GRU", "JFK", 5000, 1)

    legs = cheapest_route([*chain, direct], "GRU", "JFK")

    assert legs is not None and len(legs) == 6


def test_ties_go_to_fewer_flights() -> None:
    direct = flight("GRU", "JFK", 1000, 5)
    via_mia = [flight("GRU", "MIA", 600, 5), flight("MIA", "JFK", 400, 6)]

    assert cheapest_route([*via_mia, direct], "GRU", "JFK") == [direct]


def test_then_to_the_earliest_arrival() -> None:
    late = flight("GRU", "JFK", 1000, 9)
    early = flight("GRU", "JFK", 1000, 4)

    assert cheapest_route([late, early], "GRU", "JFK") == [early]


def test_prices_compare_exactly() -> None:
    # In floats 0.7 + 0.1 = 0.7999999999999999, which would beat the direct 0.8;
    # in cents the two routes tie, and the one with fewer flights wins.
    two_legs = [flight("GRU", "MIA", 0.7, 5), flight("MIA", "JFK", 0.1, 5)]
    direct = flight("GRU", "JFK", 0.8, 5)

    assert cheapest_route([*two_legs, direct], "GRU", "JFK") == [direct]


def test_none_without_a_route() -> None:
    assert cheapest_route([flight("GRU", "MIA", 900, 5)], "GRU", "JFK") is None
    assert cheapest_route([flight("MIA", "JFK", 900, 5)], "GRU", "JFK") is None
    assert cheapest_route([], "GRU", "JFK") is None


# --- trace


def test_tracing_does_not_change_the_route() -> None:
    flights = [
        flight("GRU", "JFK", 3000, 5),
        flight("GRU", "MIA", 900, 5),
        flight("MIA", "JFK", 400, 7),
    ]
    trace = DijkstraTrace()

    assert cheapest_route(flights, "GRU", "JFK", trace) == cheapest_route(
        flights, "GRU", "JFK"
    )


def test_trace_records_the_graph_and_every_step() -> None:
    to_mia = flight("GRU", "MIA", 900, 5)
    to_jfk = flight("MIA", "JFK", 400, 7)
    trace = DijkstraTrace()

    cheapest_route([to_mia, to_jfk], "GRU", "JFK", trace)

    assert {node.key for node in trace.nodes} == {
        "GRU|2027-01-05",
        "MIA|2027-01-05",
        "MIA|2027-01-07",
        "JFK|2027-01-07",
    }
    # Waiting at MIA from the landing day to the next departure.
    assert [(w.from_, w.to) for w in trace.waits] == [
        ("MIA|2027-01-05", "MIA|2027-01-07")
    ]
    assert trace.start == "GRU|2027-01-05"
    assert [(s.node, s.cents, s.flights) for s in trace.steps] == [
        ("GRU|2027-01-05", 0, 0),
        ("MIA|2027-01-05", 90000, 1),
        ("MIA|2027-01-07", 90000, 1),
        ("JFK|2027-01-07", 130000, 2),
    ]
    first = trace.steps[0].relaxed[0]
    assert (first.to, first.flight, first.cents, first.improved) == (
        "MIA|2027-01-05",
        to_mia.uuid,
        90000,
        True,
    )
    # The wait is an edge without a flight.
    assert trace.steps[1].relaxed[0].flight is None
    assert trace.path == [
        "GRU|2027-01-05",
        "MIA|2027-01-05",
        "MIA|2027-01-07",
        "JFK|2027-01-07",
    ]


def test_trace_marks_edges_that_do_not_improve() -> None:
    # The direct flight reaches JFK first; the connection is dearer.
    trace = DijkstraTrace()

    cheapest_route(
        [
            flight("GRU", "JFK", 500, 5),
            flight("GRU", "MIA", 100, 5),
            flight("MIA", "JFK", 900, 5),
        ],
        "GRU",
        "JFK",
        trace,
    )

    mia = next(step for step in trace.steps if step.node == "MIA|2027-01-05")
    assert [(edge.to, edge.improved) for edge in mia.relaxed] == [
        ("JFK|2027-01-05", False)
    ]


def test_trace_of_a_search_without_a_route() -> None:
    trace = DijkstraTrace()

    assert cheapest_route([flight("GRU", "MIA", 900, 5)], "GRU", "JFK", trace) is None
    assert trace.path is None
    assert len(trace.steps) == 2


def test_trace_when_the_origin_has_no_flights() -> None:
    trace = DijkstraTrace()

    cheapest_route([flight("MIA", "JFK", 400, 5)], "GRU", "JFK", trace)

    assert trace.start is None
    assert trace.steps == []
