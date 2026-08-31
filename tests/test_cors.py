"""CORS behaviour.

These assert what the browser actually enforces: the presence and value of the
`access-control-allow-origin` header on both preflight and real requests.
"""

import pytest
from httpx import AsyncClient

VERCEL_ORIGIN = "https://sky-graph-frontend.vercel.app"
PREVIEW_ORIGIN = "https://sky-graph-frontend-git-feat-abc123.vercel.app"
DEV_ORIGIN = "http://localhost:5173"


@pytest.mark.parametrize("origin", [VERCEL_ORIGIN, PREVIEW_ORIGIN, DEV_ORIGIN])
async def test_allowed_origin_gets_cors_header(
    client: AsyncClient, origin: str
) -> None:
    response = await client.get("/api/hello", headers={"Origin": origin})

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == origin


@pytest.mark.parametrize("origin", [VERCEL_ORIGIN, PREVIEW_ORIGIN])
async def test_preflight_is_accepted(client: AsyncClient, origin: str) -> None:
    response = await client.options(
        "/api/hello",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == origin


async def test_unknown_origin_gets_no_cors_header(client: AsyncClient) -> None:
    response = await client.get(
        "/api/hello", headers={"Origin": "https://not-skygraph.example.com"}
    )

    # The request still succeeds server-side; the browser is what blocks it.
    assert response.status_code == 200
    assert "access-control-allow-origin" not in response.headers


async def test_look_alike_domain_is_rejected(client: AsyncClient) -> None:
    """The preview regex must not match an attacker-controlled suffix."""
    response = await client.get(
        "/api/hello",
        headers={"Origin": "https://sky-graph-frontend-evil.attacker.com"},
    )

    assert "access-control-allow-origin" not in response.headers
