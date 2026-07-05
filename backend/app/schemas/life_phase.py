"""Pydantic v2 schemas for the ``life_phases`` resource."""

from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


# ======================================================================
# Request schemas
# ======================================================================


class LifePhaseRecalculateRequest(BaseModel):
    """Request body for ``POST /v1/me/life-phases/recalculate``.

    If ``chart_id`` is provided, Saturn's position is extracted from that
    chart for more precise phase calculation.
    """

    chart_id: UUID | None = Field(
        None,
        description="Chart ID to extract Saturn position from. "
        "If omitted, phases are estimated from default age ranges.",
    )


# ======================================================================
# Response schemas
# ======================================================================


class DominantTransit(BaseModel):
    """A single dominant transit activation within a life phase."""

    model_config = ConfigDict(from_attributes=True)

    planet: str
    aspect: str
    natal_body: str
    date: str
    description: str | None = None


class LifePhase(BaseModel):
    """A single life phase in the timeline."""

    model_config = ConfigDict(from_attributes=True)

    phase_key: str = Field(
        ...,
        pattern="^(foundation|saturn_return_1|expansion|chiron_return|"
        "saturn_return_2|uranus_opposition|legacy)$",
    )
    title: str
    start_date: date
    end_date: date | None = None
    description: str | None = None
    dominant_transits: list[DominantTransit] = []


class LifePhaseListResponse(BaseModel):
    """Response for ``GET /v1/me/life-phases`` — ordered phase timeline."""

    model_config = ConfigDict(from_attributes=True)

    user_id: UUID
    phases: list[LifePhase]
    generated_at: datetime


class CurrentLifePhaseResponse(BaseModel):
    """Response for ``GET /v1/me/life-phases/current``."""

    model_config = ConfigDict(from_attributes=True)

    user_id: UUID
    current_phase: LifePhase | None = Field(
        None,
        description="The phase active today. None if no phase matches.",
    )
    phase_index: int | None = Field(
        None,
        description="Index of the current phase in the full timeline (0-based).",
    )
    generated_at: datetime


# ======================================================================
# Chart-scoped life phases (for GET /v1/charts/{id}/life-phases)
# ======================================================================


class ChartLifePhase(BaseModel):
    """A life phase scoped to a specific chart (user's birth chart)."""

    model_config = ConfigDict(from_attributes=True)

    phase_key: str
    title: str
    year_range: str = Field(
        ...,
        description="Human-friendly range like '27–31' or '60+'",
    )
    start_year: int
    end_year: int | None = None
    description: str | None = None
    dominant_transits: list[DominantTransit] = []


class ChartLifePhasesResponse(BaseModel):
    """Response for ``GET /v1/charts/{id}/life-phases``."""

    model_config = ConfigDict(from_attributes=True)

    chart_id: UUID
    birth_date: date
    saturn_longitude: float | None = Field(
        None,
        description="Saturn's ecliptic longitude in the natal chart",
    )
    phases: list[ChartLifePhase]
    generated_at: datetime
