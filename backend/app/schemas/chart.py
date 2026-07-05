"""Pydantic v2 schemas for the ``charts`` resource."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


# ======================================================================
# Request schemas
# ======================================================================

class ChartLocation(BaseModel):
    """Location data for chart calculation."""

    latitude: Decimal = Field(..., ge=-90, le=90, decimal_places=6)
    longitude: Decimal = Field(..., ge=-180, le=180, decimal_places=6)
    time_zone: str
    location_name: str | None = None


class ChartOptions(BaseModel):
    """Optional parameters for chart calculation."""

    bodies: list[str] | None = None
    aspects: list[str] | None = None
    orb_major: float = 8.0
    orb_minor: float = 2.0
    include_minor_aspects: bool = True


class ChartCreate(BaseModel):
    """Request body for ``POST /v1/charts``."""

    chart_type: str = Field(
        ...,
        pattern="^(natal|transit|progressed|solar_return|synastry_composite|event)$",
    )
    reference_chart_id: UUID | None = None
    calculation_date: datetime
    location: ChartLocation
    house_system: str = Field(default="P", pattern="^[PWKERCV]$")
    options: ChartOptions | None = None


# ======================================================================
# Response schemas
# ======================================================================

class ChartBodyResponse(BaseModel):
    """A single celestial body in a chart."""

    model_config = ConfigDict(from_attributes=True)

    body_key: str
    longitude: Decimal
    sign: str
    sign_degree: Decimal
    house: int | None = None
    speed: Decimal
    is_retrograde: bool
    dignity: str | None = None


class ChartHouseResponse(BaseModel):
    """A single house cusp in a chart."""

    model_config = ConfigDict(from_attributes=True)

    house_number: int
    cusps_longitude: Decimal
    sign: str
    sign_degree: Decimal


class ChartAspectResponse(BaseModel):
    """A single aspect between two bodies in a chart."""

    model_config = ConfigDict(from_attributes=True)

    body_a_key: str
    body_b_key: str
    aspect_type: str
    orb: Decimal
    is_applying: bool | None = None
    is_major: bool


class ChartResponse(BaseModel):
    """Full chart response matching ``GET /v1/charts/:id``."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    chart_type: str
    user_id: UUID
    calculation_date: datetime
    house_system: str
    latitude: Decimal
    longitude: Decimal
    time_zone: str
    location_name: str | None = None
    title: str | None = None
    bodies: list[ChartBodyResponse] = []
    houses: list[ChartHouseResponse] = []
    aspects: list[ChartAspectResponse] = []
    metadata: dict = {}
    created_at: datetime


class ChartSummaryResponse(BaseModel):
    """Lightweight chart summary (signs, key aspects)."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    chart_type: str
    calculation_date: datetime
    sun: ChartBodyResponse | None = None
    moon: ChartBodyResponse | None = None
    rising: ChartBodyResponse | None = None
    key_aspects: list[ChartAspectResponse] = []
