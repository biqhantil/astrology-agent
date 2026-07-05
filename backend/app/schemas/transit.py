"""Pydantic v2 schemas for the ``transits`` resource."""

from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


# ======================================================================
# Request schemas
# ======================================================================


class TransitRequest(BaseModel):
    """Request body for ``POST /v1/charts/{id}/transits``."""

    start_date: date | None = None
    end_date: date | None = None
    bodies: list[str] | None = None


# ======================================================================
# Response schemas
# ======================================================================


class TransitEvent(BaseModel):
    """A single transit event — a transiting planet aspecting a natal body."""

    model_config = ConfigDict(from_attributes=True)

    date: date
    transiting_body: str
    natal_body: str
    aspect_type: str
    orb: float
    is_applying: bool | None = None
    transit_house: int | None = None
    natal_house: int | None = None


class TransitSnapshotResponse(BaseModel):
    """Response for a set of computed transits."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    natal_chart_id: UUID
    date_from: date
    date_to: date
    transit_events: list[TransitEvent]
    created_at: datetime
    expires_at: datetime


class TransitSummaryResponse(BaseModel):
    """Lightweight summary of important transits (major aspects only)."""

    model_config = ConfigDict(from_attributes=True)

    natal_chart_id: UUID
    date_from: date
    date_to: date
    total_events: int
    major_events: list[TransitEvent]
    slow_planets: list[TransitEvent] = Field(
        default_factory=list,
        description="Transits involving Jupiter, Saturn, Uranus, Neptune, Pluto",
    )
