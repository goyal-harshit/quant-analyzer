"""
migrate.py — safe Alembic bootstrap for startup/deploy.

Applies migrations idempotently, handling all three DB states so adopting Alembic
on an already-running (create_all-built) database never errors:

  * fresh DB         → ``alembic upgrade head`` creates everything.
  * legacy DB        → tables exist but no ``alembic_version`` (built by the old
                       create_all path) → ``stamp head`` adopts the baseline
                       without re-creating, then ``upgrade head`` applies any newer
                       migrations.
  * versioned DB     → ``alembic_version`` present → ``upgrade head`` applies pending.

Run from the backend dir:  ``python scripts/migrate.py``
"""

import asyncio
import os
import sys

# Allow `python scripts/migrate.py` to import the app packages (backend on path).
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from sqlalchemy import inspect  # noqa: E402


async def _db_state() -> str:
    from models.database import engine
    try:
        async with engine.connect() as conn:
            names = await conn.run_sync(lambda c: set(inspect(c).get_table_names()))
    finally:
        await engine.dispose()
    if "alembic_version" in names:
        return "versioned"
    if "users" in names:  # core table built by the old create_all path
        return "legacy"
    return "fresh"


def main() -> None:
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    cfg = Config(os.path.join(here, "alembic.ini"))

    state = asyncio.run(_db_state())
    print(f"[migrate] database state: {state}")

    if state == "legacy":
        print("[migrate] stamping existing schema at baseline (head)…")
        command.stamp(cfg, "head")

    print("[migrate] alembic upgrade head…")
    command.upgrade(cfg, "head")
    print("[migrate] done.")


if __name__ == "__main__":
    main()
