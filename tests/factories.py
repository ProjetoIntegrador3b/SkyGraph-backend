"""Sample domain objects shared by the tests."""

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
)
