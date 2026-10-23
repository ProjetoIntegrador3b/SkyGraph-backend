"""The shape every migration shares."""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from neo4j import AsyncDriver

from app.core.config import Settings


@dataclass(frozen=True)
class Migration:
    # Recorded in the database once applied; never rename an applied one.
    id: str
    apply: Callable[[AsyncDriver, Settings], Awaitable[None]]
