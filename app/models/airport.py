"""Airport — a node in the flight graph."""

from typing import Annotated

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, StringConstraints


def _check_iata(code: str) -> str:
    if len(code) != 3 or not (code.isascii() and code.isalpha()):
        raise ValueError(f"{code!r} is not a three-letter IATA code")
    return code


# Three-letter IATA code, e.g. "GRU". Normalised to upper case so "gru" and
# "GRU" identify the same node. The check runs after upper-casing, which a
# StringConstraints pattern would not do.
IataCode = Annotated[
    str,
    StringConstraints(strip_whitespace=True, to_upper=True),
    AfterValidator(_check_iata),
]


class Airport(BaseModel):
    model_config = ConfigDict(frozen=True)

    code: IataCode
    name: str
    city: str
    country: str
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
