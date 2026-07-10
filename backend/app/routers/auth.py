"""Authentication routes: anonymous login, magic-link, session info."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.auth import (
    AuthPayload,
    create_token,
    require_user,
    verify_token,
)
from app.core.deps import get_conn

# ── Domain schemas (colocated) ────────────────────────────────────
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

# ── Routes ──────────────────────────────────────────────────────────
router = APIRouter()


# ── POST /v1/auth/anonymous ─────────────────────────────────────

@router.post("/anonymous", response_model=AnonymousLoginResponse)
async def anonymous_login(
    body: AnonymousLoginRequest | None = None,
    conn=Depends(get_conn),
) -> AnonymousLoginResponse:
    """Create an anonymous user session and return a JWT.

    The created user has no email and defaults to ``locale="en"``.
    They can later upgrade to an authenticated account via the
    magic-link flow.
    """
    locale = (body or AnonymousLoginRequest()).locale or "en"

    user_id: UUID = await conn.fetchval(
        """
        INSERT INTO users (locale)
        VALUES ($1)
        RETURNING id
        """,
        locale,
    )

    token = create_token(user_id, token_type="anonymous")
    payload = verify_token(token)

    return AnonymousLoginResponse(
        access_token=token,
        token_type="bearer",
        user_id=user_id,
        expires_at=datetime.fromtimestamp(payload["exp"], tz=timezone.utc),
    )


# ── POST /v1/auth/magic-link ────────────────────────────────────

@router.post("/magic-link", response_model=MagicLinkResponse)
async def request_magic_link(
    body: MagicLinkRequest,
    conn=Depends(get_conn),
) -> MagicLinkResponse:
    """Associate an email with a user (create-or-link).

    **Note:** In a production system this would send an email.  For now
    the endpoint directly links the email to the user (or creates one)
    for development velocity.
    """
    user_id = body.user_id

    if user_id is not None:
        # Link email to existing user
        row = await conn.fetchrow(
            "UPDATE users SET email = $1 WHERE id = $2 RETURNING id",
            body.email,
            user_id,
        )
        if row is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )
        return MagicLinkResponse(
            message="Email linked to existing user.",
            user_id=user_id,
        )

    # Check if email already exists
    existing = await conn.fetchrow(
        "SELECT id FROM users WHERE email = $1",
        body.email,
    )
    if existing:
        return MagicLinkResponse(
            message="If an account with that email exists, a login link has been sent.",
            user_id=existing["id"],
        )

    # Create new user with email
    new_id: UUID = await conn.fetchval(
        """
        INSERT INTO users (email, display_name)
        VALUES ($1, $2)
        RETURNING id
        """,
        body.email,
        body.email.split("@")[0],  # derive display_name from email local-part
    )

    return MagicLinkResponse(
        message="Account created and email linked.",
        user_id=new_id,
    )


# ── GET /v1/auth/session ────────────────────────────────────────

@router.get("/session", response_model=SessionResponse)
async def get_session(
    auth: AuthPayload = Depends(require_user),
) -> SessionResponse:
    """Return the current token's metadata (no DB query)."""
    return SessionResponse(
        user_id=UUID(auth["sub"]),
        token_type=auth["type"],
        issued_at=datetime.fromtimestamp(auth["iat"], tz=timezone.utc),
        expires_at=datetime.fromtimestamp(auth["exp"], tz=timezone.utc),
    )
