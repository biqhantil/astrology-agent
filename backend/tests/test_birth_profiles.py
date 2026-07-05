"""Tests for the ``/v1/me/profile`` birth profile CRUD endpoints."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
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


_PROFILE_ROW = {
    "id": None,
    "user_id": None,
    "birth_date": None,
    "birth_time": None,
    "time_zone": "America/New_York",
    "utc_offset": "-05:00:00",
    "latitude": Decimal("40.712800"),
    "longitude": Decimal("-74.006000"),
    "location_name": "New York, NY",
    "house_system": "P",
    "has_unknown_time": False,
    "sun_sign": "taurus",
    "moon_sign": "leo",
    "rising_sign": "scorpio",
    "updated_at": datetime.now(timezone.utc),
}


# ── GET /v1/me/profile ──────────────────────────────────────────


class TestGetBirthProfile:
    """Retrieve own birth profile."""

    async def test_returns_profile(
        self, override_get_conn, mock_conn: AsyncMock, client: AsyncClient
    ):
        user_id = uuid4()
        profile_id = uuid4()
        row = dict(_PROFILE_ROW, id=profile_id, user_id=user_id,
                   birth_date=datetime.now(timezone.utc).date(),
                   birth_time=datetime.now(timezone.utc).timetz())
        # fetchrow is called via _fetch_profile inside the handler
        mock_conn.fetchrow.return_value = row

        resp = await client.get("/v1/me/profile", headers=_auth_header(user_id))
        assert resp.status_code == 200
        body = resp.json()
        assert body["id"] == str(profile_id)
        assert body["house_system"] == "P"
        assert body["sun_sign"] == "taurus"

    async def test_404_when_no_profile(
        self, override_get_conn, mock_conn: AsyncMock, client: AsyncClient
    ):
        user_id = uuid4()
        mock_conn.fetchrow.return_value = None

        resp = await client.get("/v1/me/profile", headers=_auth_header(user_id))
        assert resp.status_code == 404

    async def test_requires_auth(self, client: AsyncClient):
        resp = await client.get("/v1/me/profile")
        assert resp.status_code == 401


# ── POST /v1/me/profile ─────────────────────────────────────────


class TestCreateBirthProfile:
    """Create a new birth profile."""

    CREATE_BODY = {
        "birth_date": "1990-04-20",
        "birth_time": "14:30:00",
        "time_zone": "America/New_York",
        "latitude": 40.7128,
        "longitude": -74.006,
        "location_name": "New York, NY",
        "house_system": "P",
    }

    async def test_creates_profile(
        self, override_get_conn, mock_conn: AsyncMock, client: AsyncClient
    ):
        user_id = uuid4()
        profile_id = uuid4()
        row = dict(_PROFILE_ROW, id=profile_id, user_id=user_id,
                   birth_date=datetime(1990, 4, 20, tzinfo=timezone.utc).date(),
                   birth_time=datetime(1990, 4, 20, 14, 30, tzinfo=timezone.utc).timetz())

        # First fetchval (check existing) returns None → no conflict
        # Second fetchrow (INSERT) returns the row
        mock_conn.fetchval.return_value = None
        mock_conn.fetchrow.return_value = row

        resp = await client.post(
            "/v1/me/profile",
            json=self.CREATE_BODY,
            headers=_auth_header(user_id),
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["id"] == str(profile_id)
        assert body["sun_sign"] == "taurus"

    async def test_409_when_already_exists(
        self, override_get_conn, mock_conn: AsyncMock, client: AsyncClient
    ):
        user_id = uuid4()
        existing_id = uuid4()
        mock_conn.fetchval.return_value = existing_id  # profile exists

        resp = await client.post(
            "/v1/me/profile",
            json=self.CREATE_BODY,
            headers=_auth_header(user_id),
        )
        assert resp.status_code == 409
        assert "already exists" in resp.json()["detail"].lower()

    async def test_requires_auth(self, client: AsyncClient):
        resp = await client.post("/v1/me/profile", json=self.CREATE_BODY)
        assert resp.status_code == 401


# ── PUT /v1/me/profile ─────────────────────────────────────────


class TestUpdateBirthProfile:
    """Partial update of an existing birth profile."""

    async def test_updates_single_field(
        self, override_get_conn, mock_conn: AsyncMock, client: AsyncClient
    ):
        user_id = uuid4()
        profile_id = uuid4()
        row = dict(_PROFILE_ROW, id=profile_id, user_id=user_id,
                   birth_date=datetime.now(timezone.utc).date(),
                   birth_time=datetime.now(timezone.utc).timetz(),
                   location_name="Brooklyn, NY")

        mock_conn.fetchrow.return_value = row

        resp = await client.put(
            "/v1/me/profile",
            json={"location_name": "Brooklyn, NY"},
            headers=_auth_header(user_id),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["location_name"] == "Brooklyn, NY"

    async def test_404_when_no_profile(
        self, override_get_conn, mock_conn: AsyncMock, client: AsyncClient
    ):
        user_id = uuid4()
        mock_conn.fetchrow.return_value = None

        resp = await client.put(
            "/v1/me/profile",
            json={"location_name": "Nowhere"},
            headers=_auth_header(user_id),
        )
        assert resp.status_code == 404

    async def test_noop_when_no_fields(
        self, override_get_conn, mock_conn: AsyncMock, client: AsyncClient
    ):
        user_id = uuid4()
        profile_id = uuid4()
        row = dict(_PROFILE_ROW, id=profile_id, user_id=user_id,
                   birth_date=datetime.now(timezone.utc).date(),
                   birth_time=datetime.now(timezone.utc).timetz())
        mock_conn.fetchrow.return_value = row

        resp = await client.put(
            "/v1/me/profile",
            json={},
            headers=_auth_header(user_id),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["id"] == str(profile_id)

    async def test_requires_auth(self, client: AsyncClient):
        resp = await client.put("/v1/me/profile", json={"location_name": "Nope"})
        assert resp.status_code == 401


# ── DELETE /v1/me/profile ───────────────────────────────────────


class TestDeleteBirthProfile:
    """Delete the birth profile."""

    async def test_deletes_profile(
        self, override_get_conn, mock_conn: AsyncMock, client: AsyncClient
    ):
        user_id = uuid4()
        mock_conn.execute.return_value = "DELETE 1"

        resp = await client.delete("/v1/me/profile", headers=_auth_header(user_id))
        assert resp.status_code == 204

    async def test_404_when_no_profile(
        self, override_get_conn, mock_conn: AsyncMock, client: AsyncClient
    ):
        user_id = uuid4()
        mock_conn.execute.return_value = "DELETE 0"

        resp = await client.delete("/v1/me/profile", headers=_auth_header(user_id))
        assert resp.status_code == 404

    async def test_requires_auth(self, client: AsyncClient):
        resp = await client.delete("/v1/me/profile")
        assert resp.status_code == 401
