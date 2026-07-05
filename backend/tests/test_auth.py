"""Tests for authentication endpoints: anonymous login, magic-link, session."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock
from uuid import uuid4

import jwt
from httpx import AsyncClient

from app.config import settings

# ── POST /v1/auth/anonymous ─────────────────────────────────────


class TestAnonymousLogin:
    """Create-anonymous-user flow."""

    async def test_creates_user_and_returns_token(
        self, override_get_conn, mock_conn: AsyncMock, client: AsyncClient
    ):
        """A valid anonymous login returns a JWT and a user_id."""
        fake_user_id = uuid4()
        mock_conn.fetchval.return_value = fake_user_id

        resp = await client.post("/v1/auth/anonymous", json={})
        assert resp.status_code == 200
        body = resp.json()

        assert body["token_type"] == "bearer"
        assert body["user_id"] == str(fake_user_id)
        assert "access_token" in body
        assert "expires_at" in body

        # Decode the token and verify claims
        payload = jwt.decode(
            body["access_token"],
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        assert payload["sub"] == str(fake_user_id)
        assert payload["type"] == "anonymous"

    async def test_passes_locale(
        self, override_get_conn, mock_conn: AsyncMock, client: AsyncClient
    ):
        """When a locale is provided, it is stored."""
        mock_conn.fetchval.return_value = uuid4()

        resp = await client.post("/v1/auth/anonymous", json={"locale": "de"})
        assert resp.status_code == 200

        # Verify locale was passed to the INSERT
        call_args = mock_conn.fetchval.call_args
        assert call_args is not None
        assert call_args[0][1] == "de"

    async def test_defaults_to_en_locale(
        self, override_get_conn, mock_conn: AsyncMock, client: AsyncClient
    ):
        """Without a locale, the default 'en' is used."""
        mock_conn.fetchval.return_value = uuid4()

        await client.post("/v1/auth/anonymous", json={})

        call_args = mock_conn.fetchval.call_args
        assert call_args is not None
        assert call_args[0][1] == "en"


# ── POST /v1/auth/magic-link ────────────────────────────────────


class TestMagicLink:
    """Email association flow."""

    async def test_links_email_to_existing_user(
        self, override_get_conn, mock_conn: AsyncMock, client: AsyncClient
    ):
        """When user_id is provided, the email is linked to that user."""
        existing_user_id = uuid4()
        mock_conn.fetchrow.return_value = {"id": existing_user_id}

        resp = await client.post(
            "/v1/auth/magic-link",
            json={"email": "alice@example.com", "user_id": str(existing_user_id)},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["user_id"] == str(existing_user_id)

        # Verify the UPDATE was executed
        mock_conn.fetchrow.assert_called_once()

    async def test_returns_404_for_nonexistent_user(
        self, override_get_conn, mock_conn: AsyncMock, client: AsyncClient
    ):
        """Linking to a non-existent user returns 404."""
        mock_conn.fetchrow.return_value = None  # UPDATE matched 0 rows

        resp = await client.post(
            "/v1/auth/magic-link",
            json={
                "email": "alice@example.com",
                "user_id": str(uuid4()),
            },
        )
        assert resp.status_code == 404

    async def test_creates_new_user_when_no_user_id(
        self, override_get_conn, mock_conn: AsyncMock, client: AsyncClient
    ):
        """Without user_id, a new user is created with the given email."""
        new_user_id = uuid4()
        mock_conn.fetchrow.return_value = None  # SELECT existing email → None
        mock_conn.fetchval.return_value = new_user_id

        resp = await client.post(
            "/v1/auth/magic-link",
            json={"email": "bob@example.com"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["user_id"] == str(new_user_id)

    async def test_returns_existing_user_for_duplicate_email(
        self, override_get_conn, mock_conn: AsyncMock, client: AsyncClient
    ):
        """If the email already exists, the existing user_id is returned."""
        existing_user_id = uuid4()
        mock_conn.fetchrow.return_value = {"id": existing_user_id}

        resp = await client.post(
            "/v1/auth/magic-link",
            json={"email": "alice@example.com"},
        )
        assert resp.status_code == 200
        body = resp.json()
        # Should return the existing user's id
        assert body["user_id"] == str(existing_user_id)


# ── GET /v1/auth/session ────────────────────────────────────────


class TestSession:
    """Token introspection."""

    async def test_returns_token_metadata(self, client: AsyncClient):
        """A valid JWT returns sub, type, iat, exp."""
        user_id = uuid4()
        token = _make_token(str(user_id), "anonymous")

        resp = await client.get(
            "/v1/auth/session",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["user_id"] == str(user_id)
        assert body["token_type"] == "anonymous"
        assert "issued_at" in body
        assert "expires_at" in body

    async def test_requires_auth(self, client: AsyncClient):
        """Missing Authorization header returns 401."""
        resp = await client.get("/v1/auth/session")
        assert resp.status_code == 401

    async def test_rejects_expired_token(self, client: AsyncClient):
        """An expired token returns 401."""
        token = _make_token(str(uuid4()), "anonymous", expires_in_hours=-1)
        resp = await client.get(
            "/v1/auth/session",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 401
        assert "expired" in resp.json()["detail"].lower()

    async def test_rejects_bad_token(self, client: AsyncClient):
        """A malformed token returns 401."""
        resp = await client.get(
            "/v1/auth/session",
            headers={"Authorization": "Bearer not.a.token"},
        )
        assert resp.status_code == 401


# ── Helpers ─────────────────────────────────────────────────────


def _make_token(
    sub: str,
    token_type: str = "anonymous",
    expires_in_hours: int = 24,
) -> str:
    """Create a test JWT without hitting the auth module."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": sub,
        "type": token_type,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(hours=expires_in_hours)).timestamp()),
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
