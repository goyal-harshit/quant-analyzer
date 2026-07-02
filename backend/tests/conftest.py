import os
import pathlib
import tempfile

# Make `pytest` work with zero external services. CI sets DATABASE_URL to an
# ephemeral SQLite file (see .github/workflows/ci.yml); mirror that default here so
# a bare local `pytest` doesn't fall through to the Postgres default in
# models.database and fail every DB-backed test with a connection error. File-based
# (not :memory:) so every async connection shares one schema. This MUST run before
# any `models.database` import — hence at conftest module top-level, above the
# heavy imports below.
if not os.environ.get("DATABASE_URL"):
    _test_db = pathlib.Path(tempfile.gettempdir()) / "quantai_pytest.db"
    try:
        _test_db.unlink()  # start each session from a clean schema
    except FileNotFoundError:
        pass
    os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_test_db.as_posix()}"

import asyncio  # noqa: E402
from typing import AsyncGenerator  # noqa: E402

import pytest  # noqa: E402

# NOTE: heavy imports (FastAPI app, SQLAlchemy engine) are deferred into the
# fixtures that need them. This keeps pure-unit suites (factor engine, quant
# metrics, reliability primitives) collectable without the full web/DB stack
# installed — important for fast, dependency-light local and CI unit runs.


@pytest.fixture(scope="session", autouse=True)
def _disable_rate_limiting():
    # The auth tests fire many register/login calls; the shared slowapi limiter
    # is keyed on client IP and would 429 across tests. Disable it for the suite
    # (rate-limit behaviour itself isn't what these tests exercise).
    try:
        from services.rate_limit import limiter
        if hasattr(limiter, "enabled"):
            limiter.enabled = False
    except Exception:
        pass
    yield


@pytest.fixture(scope="session")
def event_loop():
    # Always create a fresh loop for the test session — asyncio.get_event_loop()
    # is deprecated outside a running loop and warns/breaks on 3.12+.
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session")
async def db_engine():
    from models.database import Base, engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()

@pytest.fixture
async def db_session(db_engine) -> AsyncGenerator:
    from models.database import AsyncSessionLocal
    async with AsyncSessionLocal() as session:
        yield session

@pytest.fixture
async def client(db_engine) -> AsyncGenerator:
    # Depend on db_engine so tables exist before any HTTP call hits the DB
    # (ASGITransport does not run the app's lifespan, which is where init_db lives).
    from httpx import AsyncClient, ASGITransport
    from main import app
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as ac:
        yield ac
