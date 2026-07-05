"""Tests for the health check endpoint."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_health_endpoint(client: AsyncClient) -> None:
    """GET /v1/health should return 200 with status info."""
    resp = await client.get("/v1/health")
    assert resp.status_code == 200
    data = resp.json()
    assert "status" in data
    assert data["status"] in ("ok", "degraded")
    assert "version" in data
    assert "database" in data


@pytest.mark.asyncio
async def test_health_response_shape(client: AsyncClient) -> None:
    """Health response must have the expected keys."""
    resp = await client.get("/v1/health")
    body = resp.json()
    assert set(body.keys()) == {"status", "version", "database"}
