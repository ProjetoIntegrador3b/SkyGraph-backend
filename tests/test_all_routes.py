"""Every route between two airports: the rules, the order, the limit, and
agreement with Dijkstra on the seed data."""

from pathlib import Path

from app.migrations.m0002_airports_and_flights import read_flights
from app.services.all_routes import all_routes
from app.services.dijkstra import cheapest_route
from tests.test_dijkstra import codes, flight

CSV_DIR = Path(__file__).resolve().parents[1] / "initial_data_csv"


def test_lists_every_route_cheapest_first() -> None:
    direct = flight("GRU", "JFK", 3000, 5)
    via_mia = [flight("GRU", "MIA", 900, 5), flight("MIA", "JFK", 400, 6)]
    via_bog = [flight("GRU", "BOG", 1500, 5), flight("BOG", "JFK", 700, 7)]

    result = all_routes([direct, *via_mia, *via_bog], "GRU", "JFK")

    assert [codes(legs) for legs in result.routes] == [
        ["GRU", "MIA", "JFK"],
        ["GRU", "BOG", "JFK"],
        ["GRU", "JFK"],
    ]
    assert not result.truncated


def test_a_connection_must_depart_on_or_after_the_landing() -> None:
    on_time = [flight("GRU", "MIA", 900, 5, lands=1), flight("MIA", "JFK", 400, 6)]
    too_early = flight("MIA", "JFK", 100, 5)

    result = all_routes([*on_time, too_early], "GRU", "JFK")

    assert result.routes == [on_time]


def test_never_passes_through_an_airport_twice() -> None:
    there = flight("GRU", "MIA", 900, 5)
    back = flight("MIA", "GRU", 800, 6)
    on = flight("GRU", "JFK", 3000, 7)

    assert all_routes([there, back, on], "GRU", "JFK").routes == [[on]]


def test_ties_go_to_fewer_flights_then_the_earliest_arrival() -> None:
    late = flight("GRU", "JFK", 1000, 9)
    early = flight("GRU", "JFK", 1000, 4)
    two_legs = [flight("GRU", "MIA", 600, 1), flight("MIA", "JFK", 400, 2)]

    result = all_routes([late, *two_legs, early], "GRU", "JFK")

    assert result.routes == [[early], [late], two_legs]


def test_empty_without_a_route() -> None:
    result = all_routes([flight("GRU", "MIA", 900, 5)], "GRU", "JFK")

    assert (result.routes, result.truncated) == ([], False)


def test_stops_at_the_limit() -> None:
    flights = [flight("GRU", "JFK", 1000 + day, day) for day in range(1, 6)]

    result = all_routes(flights, "GRU", "JFK", limit=3)

    assert len(result.routes) == 3
    assert result.truncated


def test_the_first_route_is_the_cheapest_on_the_seed_data() -> None:
    flights = read_flights(CSV_DIR / "voos.csv")
    airports = sorted({f.origin for f in flights} | {f.destination for f in flights})

    for origin in airports:
        for destination in airports:
            if origin == destination:
                continue
            result = all_routes(flights, origin, destination)
            assert not result.truncated, (origin, destination)
            routes = result.routes
            cheapest = cheapest_route(flights, origin, destination)
            assert (routes[0] if routes else None) == cheapest, (origin, destination)
