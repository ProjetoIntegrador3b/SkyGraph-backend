"""Response models."""

from pydantic import BaseModel


class HelloResponse(BaseModel):
    message: str


class HealthResponse(BaseModel):
    status: str
    database: str
