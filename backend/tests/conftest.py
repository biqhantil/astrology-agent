"""pytest fixtures for the Astrology Agent test suite.

Uses a lightweight approach: each test function that needs database access
gets an ``AsyncMock`` connection injected via dependency override.

For endpoints that need real DB integration, use the ``db_session`` fixture
(uses SQLite via app.database when enabled).
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.main import app

# ── Test client ─────────────────────────────────────────────────

@pytest_asyncio.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    """Provide an httpx AsyncClient bound to the FastAPI app."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


# ── Mock database connection ────────────────────────────────────

@pytest_asyncio.fixture
async def mock_conn() -> AsyncMock:
    """Return an ``AsyncMock`` standing in for a database connection.

    Assign return values in tests::

        mock_conn.fetchrow.return_value = {"id": "…", "email": None, …}
        mock_conn.fetchval.return_value = some_uuid
    """
    return AsyncMock()


@pytest.fixture
def override_get_conn(mock_conn: AsyncMock) -> None:
    """Install ``mock_conn`` as the ``get_conn`` dependency override.

    Apply this fixture **before** the test client fixture in your test
    function signature::

        async def test_something(override_get_conn, mock_conn, client):
            mock_conn.fetchrow.return_value = {...}
            resp = await client.get("/v1/me")
    """
    from app.core import deps

    app.dependency_overrides[deps.get_conn] = lambda: mock_conn


# ── Clean up overrides after each test ──────────────────────────

@pytest.fixture(autouse=True)
def _clean_dependency_overrides():
    """Reset dependency overrides after every test, ensuring isolation."""
    yield
    app.dependency_overrides = {}
