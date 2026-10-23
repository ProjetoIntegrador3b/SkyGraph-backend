"""Apply pending migrations: `python -m app.migrations`."""

import asyncio

from app.core.config import get_settings
from app.core.neo4j import create_driver
from app.migrations.runner import run_migrations


async def main() -> None:
    settings = get_settings()
    driver = create_driver(settings)
    try:
        applied = await run_migrations(driver, settings)
    finally:
        await driver.close()
    print(f"applied: {', '.join(applied)}" if applied else "nothing to apply")


if __name__ == "__main__":
    asyncio.run(main())
