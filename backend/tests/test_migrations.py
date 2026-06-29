"""
Guards the Alembic baseline against model drift: every table defined on the models
must be produced by `alembic upgrade head`. If someone adds a model without a
migration, this fails — keeping migrations the source of truth (audit/plan bug #1).
"""

import sqlite3

from alembic import command
from alembic.config import Config

# Import every module that defines tables so Base.metadata is complete.
import models.market_store  # noqa: F401
from models.database import Base
from modules.ipo import models as _ipo  # noqa: F401
from modules.mutual_funds import models as _mf  # noqa: F401
from modules.simulator import models as _sim  # noqa: F401


def test_migrations_cover_all_model_tables(tmp_path, monkeypatch):
    db = tmp_path / "drift.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite+aiosqlite:///{db.as_posix()}")

    cfg = Config("alembic.ini")
    command.upgrade(cfg, "head")

    con = sqlite3.connect(db)
    created = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    con.close()

    model_tables = set(Base.metadata.tables.keys())
    missing = model_tables - created
    assert not missing, f"model tables missing from migrations (drift detected): {sorted(missing)}"
    assert "alembic_version" in created
