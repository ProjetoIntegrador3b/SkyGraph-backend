"""Reprice every flight from the distance it covers.

The first prices in `voos.csv` were made up. This sets each flight's price from
the great-circle distance between its airports, at rates in line with economy
one-way fares in reais. `voos.csv` now holds these same prices, so a fresh
database already gets them from 0002; this migration brings a database loaded
with the old prices to them. The rates:

    R$ 180 in taxes and fees, plus
    R$ 0,55/km for the first 1,000 km,
    R$ 0,30/km from 1,000 to 5,000 km,
    R$ 0,28/km beyond 5,000 km.

The rate falls with distance, as real fares do: GRU -> GIG (337 km) costs
about R$ 365, GRU -> JFK (7,664 km) about R$ 2.676.

Real fares also differ between flights on the same route (airline, demand,
how early it is bought). Each flight's price is therefore multiplied by a
factor between 0.8 and 1.2. The factor comes from the flight's uuid, so it
never changes between runs. It also keeps a cheaper connection possible: on
distance alone, a connection could never beat a direct flight, because a
detour is always longer.

The formula is kept here, not shared with the app, so this migration keeps
doing what it did when it was applied.
"""

import hashlib
import math
from uuid import UUID

from neo4j import AsyncDriver

from app.core.config import Settings
from app.migrations.base import Migration
from app.migrations.m0002_airports_and_flights import (
    AIRPORTS_FILE,
    FLIGHTS_FILE,
    read_airports,
    read_flights,
)
from app.models import Airport

EARTH_RADIUS_KM = 6371
BASE_FARE = 180
# (up to this distance in km, price per km within the band)
RATES = [(1_000, 0.55), (5_000, 0.30), (math.inf, 0.28)]
VARIATION = 0.2

SET_PRICES = """
UNWIND $flights AS flight
MATCH ()-[f:FLIGHT {uuid: flight.uuid}]->()
SET f.price = flight.price
"""


def distance_km(origin: Airport, destination: Airport) -> float:
    """Great-circle distance between two airports (haversine)."""
    lat1, lat2 = math.radians(origin.latitude), math.radians(destination.latitude)
    dlat = lat2 - lat1
    dlon = math.radians(destination.longitude - origin.longitude)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    )
    return 2 * EARTH_RADIUS_KM * math.asin(math.sqrt(a))


def base_price(km: float) -> float:
    """The fare for a distance, before the per-flight variation."""
    price, start = BASE_FARE, 0.0
    for end, rate in RATES:
        price += rate * max(0.0, min(km, end) - start)
        start = end
    return price


def variation(uuid: UUID) -> float:
    """A factor in [0.8, 1.2] that depends only on the flight's uuid."""
    digest = hashlib.sha256(str(uuid).encode()).digest()
    share = int.from_bytes(digest[:4]) / 0xFFFFFFFF
    return 1 - VARIATION + 2 * VARIATION * share


def realistic_price(origin: Airport, destination: Airport, uuid: UUID) -> float:
    return round(base_price(distance_km(origin, destination)) * variation(uuid), 2)


async def _apply(driver: AsyncDriver, settings: Settings) -> None:
    airports = {
        airport.code: airport
        for airport in read_airports(settings.seed_data_dir / AIRPORTS_FILE)
    }
    flights = read_flights(settings.seed_data_dir / FLIGHTS_FILE)
    await driver.execute_query(
        SET_PRICES,
        flights=[
            {
                "uuid": str(flight.uuid),
                "price": realistic_price(
                    airports[flight.origin], airports[flight.destination], flight.uuid
                ),
            }
            for flight in flights
        ],
        database_=settings.neo4j_database,
    )


migration = Migration(id="0004_realistic_prices", apply=_apply)
