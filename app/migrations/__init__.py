"""Versioned Neo4j migrations.

Each migration runs once: applied ones are recorded as `SchemaMigration` nodes
in the database itself. They run on API startup, so every deploy brings the
graph up to date, and can also be run by hand with `python -m app.migrations`.
"""

from app.migrations.runner import MIGRATIONS, Migration, run_migrations

__all__ = ["MIGRATIONS", "Migration", "run_migrations"]
