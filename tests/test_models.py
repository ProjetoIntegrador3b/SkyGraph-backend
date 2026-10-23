from datetime import date

import pytest
from pydantic import ValidationError

from app.models import Airport, Flight

FLIGHT_UUID = "815ef6d1-3b8f-4a18-b7f8-a88b17fc695a"


def _airport(**overrides: object) -> Airport:
    fields: dict[str, object] = {
        "code": "GRU",
        "name": "Aeroporto Internacional de Guarulhos",
        "city": "São Paulo",
        "country": "Brasil",
        "latitude": -23.4356,
        "longitude": -46.4731,
    }
    return Airport(**(fields | overrides))


def _flight(**overrides: object) -> Flight:
    fields: dict[str, object] = {
        "uuid": FLIGHT_UUID,
        "price": 682.94,
        "origin": "GRU",
        "destination": "FOR",
        "departure_date": "2027-01-11",
        "arrival_date": "2027-01-11",
    }
    return Flight(**(fields | overrides))


def test_airport_code_is_normalised_to_upper_case() -> None:
    assert _airport(code=" gru ").code == "GRU"


@pytest.mark.parametrize("code", ["GR", "GRUU", "G1U", ""])
def test_airport_rejects_invalid_iata_code(code: str) -> None:
    with pytest.raises(ValidationError):
        _airport(code=code)


@pytest.mark.parametrize(
    "coordinates", [{"latitude": 90.1}, {"latitude": -91}, {"longitude": 180.5}]
)
def test_airport_rejects_out_of_range_coordinates(
    coordinates: dict[str, float],
) -> None:
    with pytest.raises(ValidationError):
        _airport(**coordinates)


def test_airport_is_immutable() -> None:
    airport = _airport()

    with pytest.raises(ValidationError):
        airport.code = "JFK"  # type: ignore[misc]


def test_flight_parses_uuid() -> None:
    assert str(_flight().uuid) == FLIGHT_UUID


def test_flight_rejects_invalid_uuid() -> None:
    with pytest.raises(ValidationError):
        _flight(uuid="not-a-uuid")


def test_flight_normalises_airport_codes() -> None:
    flight = _flight(origin="gru", destination="for")

    assert (flight.origin, flight.destination) == ("GRU", "FOR")


def test_flight_rejects_same_origin_and_destination() -> None:
    with pytest.raises(ValidationError, match="must be different airports"):
        _flight(destination="GRU")


@pytest.mark.parametrize("price", [0, -10])
def test_flight_rejects_non_positive_price(price: float) -> None:
    with pytest.raises(ValidationError):
        _flight(price=price)


def test_flight_parses_the_dates() -> None:
    flight = _flight(arrival_date="2027-01-12")

    assert (flight.departure_date, flight.arrival_date) == (
        date(2027, 1, 11),
        date(2027, 1, 12),
    )


def test_flight_rejects_arrival_before_departure() -> None:
    with pytest.raises(ValidationError, match="must not be before departure_date"):
        _flight(arrival_date="2027-01-10")


def test_flight_requires_the_dates() -> None:
    with pytest.raises(ValidationError):
        Flight(uuid=FLIGHT_UUID, price=1, origin="GRU", destination="FOR")
