"""Application settings, loaded from the environment."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "SkyGraph API"
    debug: bool = False

    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "skygraph"
    neo4j_database: str = "neo4j"

    # Comma-separated so the value can be edited in a hosting dashboard.
    # Covers the Vite dev server, the dockerised frontend, and production.
    cors_origins: str = (
        "http://localhost:5173,"
        "http://localhost:3000,"
        "https://sky-graph-frontend.vercel.app"
    )
    # Vercel gives every branch and pull request its own preview URL; this
    # matches those without having to list them one by one.
    cors_origin_regex: str = r"https://sky-graph-frontend-[a-z0-9-]+\.vercel\.app"

    @property
    def cors_origin_list(self) -> list[str]:
        """Allowed origins, parsed from the comma-separated setting."""
        return [
            origin.strip() for origin in self.cors_origins.split(",") if origin.strip()
        ]


@lru_cache
def get_settings() -> Settings:
    """Cached so the environment is parsed once per process."""
    return Settings()
