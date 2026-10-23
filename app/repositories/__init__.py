"""Data access: the only layer that writes Cypher for the domain models."""

from app.repositories.airport import AirportRepository
from app.repositories.flight import FlightRepository

__all__ = ["AirportRepository", "FlightRepository"]
