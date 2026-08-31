# SkyGraph backend

FastAPI service backed by a Neo4j graph database.

## Endpoints

| Method | Path          | Description                          |
| ------ | ------------- | ------------------------------------ |
| GET    | `/api/hello`  | Hello world                          |
| GET    | `/api/health` | Reports Neo4j connectivity           |

Interactive docs are served at `/docs`.

## Local development

```bash
uv venv --python 3.13
uv pip install -e ".[dev]"

.venv/bin/pytest              # tests
.venv/bin/ruff check .        # lint
.venv/bin/ruff format .       # format
.venv/bin/uvicorn app.main:app --reload
```

## Docker

```bash
docker network create skygraph-network   # once, shared with the frontend
docker compose up -d --build
```

Set `API_PORT` (or `NEO4J_HTTP_PORT` / `NEO4J_BOLT_PORT`) if a default port is
already taken on your machine:

```bash
API_PORT=8010 docker compose up -d
```

Runs the API on http://localhost:8000 and Neo4j Browser on http://localhost:7474,
both attached to the `skygraph-network` shared with the frontend.
