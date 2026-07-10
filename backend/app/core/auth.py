"""JWT-based authentication: token creation, verification, and FastAPI dependency."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Literal
from uuid import UUID

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import settings

# ── Bearer token scheme ─────────────────────────────────────────

bearer_scheme = HTTPBearer(auto_error=False)


# ── Token Types ─────────────────────────────────────────────────

TokenType = Literal["anonymous", "authenticated"]
AuthProvider = Literal["anonymous", "google", "dev"]

AuthPayload = dict[str, Any]
"""Expected JWT claims:
{
    "sub": str(uuid),       # user_id
    "type": "anonymous" | "authenticated",
    "auth_provider": "anonymous" | "google" | "dev",
    "iat": int,
    "exp": int,
}
"""


# ── Token creation ──────────────────────────────────────────────

def create_token(
    user_id: UUID,
    *,
    token_type: TokenType = "anonymous",
    auth_provider: AuthProvider = "anonymous",
    expires_in_hours: int | None = None,
) -> str:
    """Create a signed JWT for the given user.

    If *expires_in_hours* is ``None``, the expiry is determined by
    *token_type* (anonymous → short-lived, authenticated → 7 days).
    """
    if expires_in_hours is None:
        expires_in_hours = (
            settings.JWT_ANONYMOUS_EXPIRY_HOURS
            if token_type == "anonymous"
            else settings.JWT_AUTHENTICATED_EXPIRY_HOURS
        )

    now = datetime.now(timezone.utc)
    payload: AuthPayload = {
        "sub": str(user_id),
        "type": token_type,
        "auth_provider": auth_provider,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(hours=expires_in_hours)).timestamp()),
    }
    return jwt.encode(
        payload,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )


# ── Token verification ──────────────────────────────────────────

def verify_token(token: str) -> AuthPayload:
    """Decode and validate a JWT.  Raises ``HTTPException`` on failure."""
    try:
        payload: AuthPayload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )

    # Validate required claims
    if "sub" not in payload or "type" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing required claims",
        )

    return payload


# ── FastAPI dependency ──────────────────────────────────────────

async def require_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> AuthPayload:
    """Dependency that extracts and validates the JWT from the Authorization header.

    Returns the decoded JWT payload with at least ``sub`` (user UUID) and ``type``.
    Raises ``401`` if the token is missing or invalid.
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return verify_token(credentials.credentials)


async def optional_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> AuthPayload | None:
    """Dependency that returns the JWT payload if present, or ``None`` otherwise.

    Does **not** raise on missing token — useful for endpoints that work
    both authenticated and anonymously.
    """
    if credentials is None:
        return None
    try:
        return verify_token(credentials.credentials)
    except HTTPException:
        return None
