from httpx import AsyncClient


async def test_hello_returns_greeting(client: AsyncClient) -> None:
    response = await client.get("/api/hello")

    assert response.status_code == 200
    assert response.json() == {"message": "Hello SkyGraphers"}


async def test_hello_content_type_is_json(client: AsyncClient) -> None:
    response = await client.get("/api/hello")

    assert response.headers["content-type"].startswith("application/json")
