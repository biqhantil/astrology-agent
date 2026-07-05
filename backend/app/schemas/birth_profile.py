"""Pydantic schemas for the ``birth_profiles`` resource."""

from __future__ import annotations

from datetime import date, datetime, time
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

HOUSE_SYSTEM_CHOICES = ("P", "W", "K", "E", "R", "C", "V")


# ── Request ─────────────────────────────────────────────────────

class BirthProfileCreate(BaseModel):
    """Create a birth profile for the current user."""

    birth_date: date
    birth_time: time | None = None
    time_zone: str  # IANA timezone, e.g. "America/New_York"
    latitude: Decimal = Field(..., ge=-90, le=90, decimal_places=6)
    longitude: Decimal = Field(..., ge=-180, le=180, decimal_places=6)
    location_name: str | None = None
    house_system: str = Field(default="P", pattern="^[PWKERCV]$")


class BirthProfileUpdate(BaseModel):
    """Partial update of a birth profile."""

    birth_date: date | None = None
    birth_time: time | None = None
    time_zone: str | None = None
    latitude: Decimal | None = Field(None, ge=-90, le=90, decimal_places=6)
    longitude: Decimal | None = Field(None, ge=-180, le=180, decimal_places=6)
    location_name: str | None = None
    house_system: str | None = Field(None, pattern="^[PWKERCV]$")


# ── Response ────────────────────────────────────────────────────

class BirthProfileResponse(BaseModel):
    """Full birth profile returned to the client."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    birth_date: date
    birth_time: time | None = None
    time_zone: str
    utc_offset: str | None = None  # INTERVAL cast to string
    latitude: Decimal
    longitude: Decimal
    location_name: str | None = None
    house_system: str = "P"
    has_unknown_time: bool = False
    sun_sign: str | None = None
    moon_sign: str | None = None
    rising_sign: str | None = None
    updated_at: datetime
