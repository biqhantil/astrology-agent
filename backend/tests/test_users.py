"""Tests for the ``/v1/me`` user profile endpoints."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock
from uuid import uuid4

import jwt
from httpx import AsyncClient

from app.config import settings

# ── Helper ──────────────────────────────────────────────────────

def _auth_header(user_id) -> dict:
    """Return ``Authorization`` header dict with a valid JWT for *user_id*."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "type": "anonymous",
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(hours=24)).timestamp()),
    }
    token = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return {"Authorization": f"Bearer {token}"}


_USER_ROW = {
    "id": None,  # filled per test
    "email": None,
    "display_name": None,
    "locale": "en",
    "created_at": datetime.now(timezone.utc),
    "last_active_at": datetime.now(timezone.utc),
}


# ── GET /v1/me ──────────────────────────────────────────────────


class TestGetMyProfile:
    """Retrieve own user profile."""

    async def test_returns_profile(
        self, override_get_conn, mock_conn: AsyncMock, client: AsyncClient
    ):
        user_id = uuid4()
        row = dict(_USER_ROW, id=user_id)
        mock_conn.fetchrow.return_value = row

        resp = await client.get("/v1/me", headers=_auth_header(user_id))
        assert resp.status_code == 200
        body = resp.json()
        assert body["id"] == str(user_id)
        assert body["locale"] == "en"

    async def test_404_when_user_missing(
        self, override_get_conn, mock_conn: AsyncMock, client: AsyncClient
    ):
        user_id = uuid4()
        mock_conn.fetchrow.return_value = None

        resp = await client.get("/v1/me", headers=_auth_header(user_id))
        assert resp.status_code == 404

    async def test_requires_auth(self, client: AsyncClient):
        resp = await client.get("/v1/me")
        assert resp.status_code == 401


# ── PUT /v1/me ──────────────────────────────────────────────────


class TestUpdateMyProfile:
    """Update own user profile."""

    async def test_updates_display_name(
        self, override_get_conn, mock_conn: AsyncMock, client: AsyncClient
    ):
        user_id = uuid4()
        row = dict(_USER_ROW, id=user_id, display_name="Alice")
        mock_conn.fetchrow.return_value = row

        resp = await client.put(
            "/v1/me",
            json={"display_name": "Alice"},
            headers=_auth_header(user_id),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["display_name"] == "Alice"

    async def test_updates_locale(
        self, override_get_conn, mock_conn: AsyncMock, client: AsyncClient
    ):
        user_id = uuid4()
        row = dict(_USER_ROW, id=user_id, locale="fr")
        mock_conn.fetchrow.return_value = row

        resp = await client.put(
            "/v1/me",
            json={"locale": "fr"},
            headers=_auth_header(user_id),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["locale"] == "fr"

    async def test_noop_when_no_fields_provided(
        self, override_get_conn, mock_conn: AsyncMock, client: AsyncClient
    ):
        user_id = uuid4()
        row = dict(_USER_ROW, id=user_id, display_name="Bob", locale="de")
        mock_conn.fetchrow.return_value = row

        resp = await client.put(
            "/v1/me",
            json={},
            headers=_auth_header(user_id),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["display_name"] == "Bob"
        assert body["locale"] == "de"

    async def test_404_when_user_missing(
        self, override_get_conn, mock_conn: AsyncMock, client: AsyncClient
    ):
        user_id = uuid4()
        mock_conn.fetchrow.return_value = None

        resp = await client.put(
            "/v1/me",
            json={"display_name": "Ghost"},
            headers=_auth_header(user_id),
        )
        assert resp.status_code == 404

    async def test_requires_auth(self, client: AsyncClient):
        resp = await client.put("/v1/me", json={"display_name": "Nope"})
        assert resp.status_code == 401
