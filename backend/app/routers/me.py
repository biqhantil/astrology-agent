"""User profile management — GET/PUT /v1/me."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.auth import AuthPayload, require_user
from app.core.deps import get_conn

# ── Domain schemas (colocated) ────────────────────────────────────
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

# ── GET /v1/me → response ───────────────────────────────────────

class UserPublic(BaseModel):
    """Public view of a user returned to the client."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str | None = None
    display_name: str | None = None
    locale: str = "en"
    created_at: datetime
    last_active_at: datetime


class UserUpdate(BaseModel):
    """Fields a user may update about themselves."""

    display_name: str | None = None
    locale: str | None = None

# ── Routes ──────────────────────────────────────────────────────────

router = APIRouter()


# ── Helpers ─────────────────────────────────────────────────────

async def _fetch_user(conn, user_id: UUID) -> dict | None:
    """Fetch a single user row by id."""
    row = await conn.fetchrow(
        """
        SELECT id, email, display_name, locale,
               created_at, last_active_at
        FROM users
        WHERE id = $1
        """,
        user_id,
    )
    return dict(row) if row else None


# ── GET /v1/me ──────────────────────────────────────────────────

@router.get("", response_model=UserPublic)
async def get_my_profile(
    auth: AuthPayload = Depends(require_user),
    conn=Depends(get_conn),
) -> UserPublic:
    """Return the authenticated user's profile."""
    user = await _fetch_user(conn, UUID(auth["sub"]))
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    return UserPublic(**user)


# ── PUT /v1/me ──────────────────────────────────────────────────

@router.put("", response_model=UserPublic)
async def update_my_profile(
    body: UserUpdate,
    auth: AuthPayload = Depends(require_user),
    conn=Depends(get_conn),
) -> UserPublic:
    """Update the authenticated user's display_name and/or locale."""
    user_id = UUID(auth["sub"])

    # Build dynamic SET clause
    sets: list[str] = []
    params: list[object] = []
    idx = 1

    if body.display_name is not None:
        sets.append(f"display_name = ${idx}")
        params.append(body.display_name)
        idx += 1

    if body.locale is not None:
        sets.append(f"locale = ${idx}")
        params.append(body.locale)
        idx += 1

    if not sets:
        # Nothing to update — just return current profile
        user = await _fetch_user(conn, user_id)
        if user is None:
            raise HTTPException(status_code=404, detail="User not found")
        return UserPublic(**user)

    sets.append(f"last_active_at = ${idx}")
    params.append(datetime.now(timezone.utc))
    idx += 1

    params.append(user_id)
    query = (
        "UPDATE users SET "
        + ", ".join(sets)
        + f" WHERE id = ${idx}"
        + " RETURNING id, email, display_name, locale, created_at, last_active_at"
    )

    row = await conn.fetchrow(query, *params)
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    return UserPublic(**dict(row))
