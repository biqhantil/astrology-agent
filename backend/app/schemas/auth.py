"""Pydantic schemas for authentication endpoints."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr

# ── POST /v1/auth/anonymous ─────────────────────────────────────

class AnonymousLoginRequest(BaseModel):
    """Optional metadata for anonymous user creation."""

    locale: str | None = None


class AnonymousLoginResponse(BaseModel):
    """Returned after creating an anonymous session."""

    access_token: str
    token_type: str = "bearer"
    user_id: UUID
    expires_at: datetime


# ── POST /v1/auth/magic-link ────────────────────────────────────

class MagicLinkRequest(BaseModel):
    """Request a magic link to associate an email with an existing user."""

    email: EmailStr
    user_id: UUID | None = None
    """If provided, link this email to the given user.  Otherwise create a new user."""


class MagicLinkResponse(BaseModel):
    """Confirmation that a magic link was sent (or would have been sent)."""

    message: str = "If an account with that email exists, a login link has been sent."
    user_id: UUID | None = None
    """Present only when a new user was created alongside the request."""


# ── GET /v1/auth/session ────────────────────────────────────────

class SessionResponse(BaseModel):
    """Return the current session's token info (no full user data)."""

    user_id: UUID
    token_type: str
    issued_at: datetime
    expires_at: datetime
