"""Sample domain objects shared by the tests."""

from datetime import date

from app.models import Airport, Flight

GRU = Airport(
    code="GRU",
    name="Aeroporto Internacional de Guarulhos",
    city="São Paulo",
    country="Brasil",
    latitude=-23.4356,
    longitude=-46.4731,
)

GRU_FOR = Flight(
    uuid="815ef6d1-3b8f-4a18-b7f8-a88b17fc695a",
    price=682.94,
    origin="GRU",
    destination="FOR",
    departure_date=date(2027, 1, 11),
    arrival_date=date(2027, 1, 11),
)

FOR_GIG = Flight(
    uuid="0f3c2a1e-5b7d-4c9e-8a6f-1d2e3c4b5a69",
    price=302.01,
    origin="FOR",
    destination="GIG",
    departure_date=date(2027, 1, 12),
    arrival_date=date(2027, 1, 13),
)
