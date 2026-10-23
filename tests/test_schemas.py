from app.api.schemas import AirportResponse, FlightResponse
from app.models import Airport, Flight


def test_airport_response_is_built_from_the_model() -> None:
    airport = Airport(
        code="GRU",
        name="Aeroporto Internacional de Guarulhos",
        city="São Paulo",
        country="Brasil",
        latitude=-23.4356,
        longitude=-46.4731,
    )

    body = AirportResponse.model_validate(airport).model_dump(mode="json")

    assert body == {
        "code": "GRU",
        "name": "Aeroporto Internacional de Guarulhos",
        "city": "São Paulo",
        "country": "Brasil",
        "latitude": -23.4356,
        "longitude": -46.4731,
    }


def test_flight_response_is_built_from_the_model() -> None:
    flight = Flight(
        uuid="815ef6d1-3b8f-4a18-b7f8-a88b17fc695a",
        price=682.94,
        origin="GRU",
        destination="FOR",
        departure_date="2027-01-11",
        arrival_date="2027-01-12",
    )

    body = FlightResponse.model_validate(flight).model_dump(mode="json", by_alias=True)

    assert body == {
        "uuid": "815ef6d1-3b8f-4a18-b7f8-a88b17fc695a",
        "price": 682.94,
        "origin": "GRU",
        "destination": "FOR",
        "departureDate": "2027-01-11",
        "arrivalDate": "2027-01-12",
    }
