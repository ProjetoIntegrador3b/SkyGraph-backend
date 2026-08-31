from app.core.config import Settings


def test_cors_origin_list_splits_and_strips() -> None:
    settings = Settings(cors_origins="https://a.example , https://b.example,")

    assert settings.cors_origin_list == ["https://a.example", "https://b.example"]


def test_cors_origin_list_defaults_include_production_frontend() -> None:
    assert "https://sky-graph-frontend.vercel.app" in Settings().cors_origin_list
