"""Pydantic v2 schemas for the ``synastry`` resource."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


# ======================================================================
# Request schemas
# ======================================================================


class SynastryCreate(BaseModel):
    """Request body for ``POST /v1/synastry``."""

    chart_a_id: UUID
    chart_b_id: UUID
    relationship_type: str | None = Field(
        None,
        pattern="^(romantic|friendship|business|family)$",
    )


# ======================================================================
# Response schemas
# ======================================================================


class SynastryAspectResponse(BaseModel):
    """A single inter-chart aspect between Chart A body and Chart B body."""

    model_config = ConfigDict(from_attributes=True)

    body_a_key: str
    body_b_key: str
    aspect_type: str
    orb: float
    is_applying: bool | None = None
    house_overlay: dict | None = None


class ScoreSummary(BaseModel):
    """Aggregated compatibility metrics."""

    emotional: float | None = Field(None, ge=0, le=10)
    communication: float | None = Field(None, ge=0, le=10)
    passion: float | None = Field(None, ge=0, le=10)
    commitment: float | None = Field(None, ge=0, le=10)
    overall: float | None = Field(None, ge=0, le=10)


class SynastryResponse(BaseModel):
    """Full synastry response for ``GET /v1/synastry/{id}``."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    chart_a_id: UUID
    chart_b_id: UUID
    relationship_type: str | None = None
    aspects: list[SynastryAspectResponse] = []
    score_summary: ScoreSummary | None = None
    composite_chart_id: UUID | None = None
    davison_chart_id: UUID | None = None
    created_at: datetime


class SynastryListResponse(BaseModel):
    """List of synastry pairs for a user."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    chart_a_id: UUID
    chart_b_id: UUID
    relationship_type: str | None = None
    score_summary: ScoreSummary | None = None
    created_at: datetime
