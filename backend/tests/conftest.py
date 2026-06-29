import pytest
import asyncio
from typing import AsyncGenerator

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
