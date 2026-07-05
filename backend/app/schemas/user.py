"""Pydantic schemas for the ``users`` resource."""

from __future__ import annotations

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
