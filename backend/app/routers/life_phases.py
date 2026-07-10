"""Life phases endpoints — precomputed major life phase timeline.

POST /v1/me/life-phases/recalculate — compute life phases for the user
GET  /v1/me/life-phases — retrieve ordered phase timeline
GET  /v1/me/life-phases/current — active phase with dominant transits
GET  /v1/charts/{id}/life-phases — phases scoped to a specific chart
"""

from __future__ import annotations

import json
from datetime import date, datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.astro_engine.life_phases import LifePhaseCalculator
from app.core.auth import AuthPayload, require_user
from app.core.deps import get_conn
from app.database import DatabasePool

# ── Domain schemas (colocated) ────────────────────────────────────
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

# ── Routes ──────────────────────────────────────────────────────────
router = APIRouter()


# ======================================================================
# POST /v1/me/life-phases/recalculate
# ======================================================================


@router.post(
    "/me/life-phases/recalculate",
    response_model=LifePhaseListResponse,
    status_code=status.HTTP_201_CREATED,
)
async def recalculate_life_phases(
    body: LifePhaseRecalculateRequest | None = None,
    auth: AuthPayload = Depends(require_user),
    conn: DatabasePool = Depends(get_conn),
) -> LifePhaseListResponse:
    """Compute (or recompute) life phases for the authenticated user.

    Extracts the user's birth date from their birth profile, optionally
    uses Saturn's position from the specified chart, computes the phase
    timeline, persists to the ``life_phases`` table, and returns the
    ordered phases.
    """
    user_id = UUID(auth["sub"])

    # 1. Fetch the user's birth profile
    bp = await conn.fetchrow(
        """
        SELECT birth_date, sun_sign, moon_sign, rising_sign
        FROM birth_profiles
        WHERE user_id = $1
        """,
        user_id,
    )
    if bp is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No birth profile found. Create one via PUT /v1/me/birth-profile first.",
        )

    birth_date = bp["birth_date"]

    # 2. Optionally extract Saturn's longitude from the specified chart
    saturn_longitude: float | None = None
    if body and body.chart_id:
        saturn_row = await conn.fetchrow(
            """
            SELECT longitude FROM chart_bodies
            WHERE chart_id = $1 AND body_key = 'saturn'
            """,
            body.chart_id,
        )
        if saturn_row:
            saturn_longitude = float(saturn_row["longitude"])

    # 3. Compute phases
    calc = LifePhaseCalculator()
    phases_data = calc.compute_phases(
        birth_date=birth_date,
        saturn_longitude=saturn_longitude,
        include_descriptions=True,
        include_dominant_transits=True,
    )

    # 4. Persist to life_phases table (clear old, insert new)
    async with conn.transaction():
        # Remove existing phases for this user
        await conn.execute(
            "DELETE FROM life_phases WHERE user_id = $1",
            user_id,
        )

        # Insert new phases
        for phase in phases_data:
            dominant_json = json.dumps(phase.get("dominant_transits", [])) if phase.get("dominant_transits") else None

            await conn.execute(
                """
                INSERT INTO life_phases
                    (user_id, phase_key, title, start_date, end_date,
                     dominant_transits, description)
                VALUES ($1, $2, $3, $4, $5, $6::jsonb, $7)
                """,
                user_id,
                phase["phase_key"],
                phase["title"],
                phase["start_date"],
                phase.get("end_date"),
                dominant_json,
                phase.get("description", ""),
            )

    # 5. Return the computed phases
    return _build_list_response(user_id, phases_data)


# ======================================================================
# GET /v1/me/life-phases
# ======================================================================


@router.get(
    "/me/life-phases",
    response_model=LifePhaseListResponse,
)
async def get_life_phases(
    auth: AuthPayload = Depends(require_user),
    conn: DatabasePool = Depends(get_conn),
) -> LifePhaseListResponse:
    """Retrieve the ordered life phase timeline for the user.

    If no phases have been precomputed yet, returns a 404 with
    instructions to call ``/v1/me/life-phases/recalculate`` first.
    """
    user_id = UUID(auth["sub"])

    rows = await conn.fetch(
        """
        SELECT phase_key, title, start_date, end_date,
               dominant_transits, description
        FROM life_phases
        WHERE user_id = $1
        ORDER BY start_date ASC
        """,
        user_id,
    )

    if not rows:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No life phases found. "
            "Call POST /v1/me/life-phases/recalculate first to compute them.",
        )

    phases = [_row_to_phase(r) for r in rows]
    return _build_list_response(user_id, [p.model_dump() for p in phases])


# ======================================================================
# GET /v1/me/life-phases/current
# ======================================================================


@router.get(
    "/me/life-phases/current",
    response_model=CurrentLifePhaseResponse,
)
async def get_current_life_phase(
    auth: AuthPayload = Depends(require_user),
    conn: DatabasePool = Depends(get_conn),
) -> CurrentLifePhaseResponse:
    """Return the currently active life phase.

    Determines which phase is active today based on the stored phase
    date ranges.
    """
    user_id = UUID(auth["sub"])
    today = date.today()

    rows = await conn.fetch(
        """
        SELECT phase_key, title, start_date, end_date,
               dominant_transits, description
        FROM life_phases
        WHERE user_id = $1
        ORDER BY start_date ASC
        """,
        user_id,
    )

    if not rows:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No life phases found. "
            "Call POST /v1/me/life-phases/recalculate first.",
        )

    all_phases = [_row_to_phase(r) for r in rows]
    current_index: int | None = None
    current_phase: LifePhase | None = None

    for i, phase in enumerate(all_phases):
        if phase.start_date <= today and (phase.end_date is None or today <= phase.end_date):
            current_index = i
            current_phase = phase
            break

    return CurrentLifePhaseResponse(
        user_id=user_id,
        current_phase=current_phase,
        phase_index=current_index,
        generated_at=datetime.now(timezone.utc),
    )


# ======================================================================
# GET /v1/charts/{chart_id}/life-phases
# ======================================================================


@router.get(
    "/charts/{chart_id}/life-phases",
    response_model=ChartLifePhasesResponse,
)
async def get_chart_life_phases(
    chart_id: UUID,
    auth: AuthPayload = Depends(require_user),
    conn: DatabasePool = Depends(get_conn),
) -> ChartLifePhasesResponse:
    """Compute and return life phases scoped to a specific natal chart.

    This endpoint is useful for chart-level queries. It extracts the
    birth date from the chart's user's birth profile and Saturn's
    longitude from the chart bodies.
    """
    user_id = UUID(auth["sub"])

    # 1. Fetch the chart
    chart_row = await conn.fetchrow(
        """
        SELECT id, user_id, chart_type, calculation_date
        FROM charts
        WHERE id = $1
        """,
        chart_id,
    )
    if chart_row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chart not found",
        )

    # 2. Fetch the user's birth profile to get birth_date
    bp = await conn.fetchrow(
        """
        SELECT birth_date FROM birth_profiles
        WHERE user_id = $1
        """,
        # Use the chart owner's user_id, but ensure it's the requesting user
        # or a shared chart. For now, scope to requesting user.
        user_id,
    )
    if bp is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No birth profile for chart owner. Cannot compute life phases.",
        )

    birth_date = bp["birth_date"]

    # 3. Fetch Saturn's longitude from the chart bodies
    saturn_row = await conn.fetchrow(
        """
        SELECT longitude FROM chart_bodies
        WHERE chart_id = $1 AND body_key = 'saturn'
        """,
        chart_id,
    )
    saturn_longitude = float(saturn_row["longitude"]) if saturn_row else None

    # 4. Compute phases
    calc = LifePhaseCalculator()
    phases_data = calc.compute_phases(
        birth_date=birth_date,
        saturn_longitude=saturn_longitude,
        include_descriptions=True,
        include_dominant_transits=True,
    )

    # 5. Build chart-scoped response
    chart_phases = []
    for phase in phases_data:
        start_year = phase["start_date"].year
        end_year = phase["end_date"].year if phase.get("end_date") else None
        year_range = f"{start_year}–{end_year}" if end_year else f"{start_year}+"

        transits = [
            DominantTransit(**t) for t in phase.get("dominant_transits", [])
        ]

        chart_phases.append(ChartLifePhase(
            phase_key=phase["phase_key"],
            title=phase["title"],
            year_range=year_range,
            start_year=start_year,
            end_year=end_year,
            description=phase.get("description"),
            dominant_transits=transits,
        ))

    return ChartLifePhasesResponse(
        chart_id=chart_id,
        birth_date=birth_date,
        saturn_longitude=saturn_longitude,
        phases=chart_phases,
        generated_at=datetime.now(timezone.utc),
    )


# ======================================================================
# Internal helpers
# ======================================================================


def _row_to_phase(row: dict) -> LifePhase:
    """Convert a ``life_phases`` DB row to a ``LifePhase`` schema."""
    transits_data = row["dominant_transits"]
    if isinstance(transits_data, str):
        transits_data = json.loads(transits_data)

    transits = []
    if transits_data:
        transits = [DominantTransit(**t) for t in transits_data]

    return LifePhase(
        phase_key=row["phase_key"],
        title=row["title"],
        start_date=row["start_date"],
        end_date=row.get("end_date"),
        description=row.get("description"),
        dominant_transits=transits,
    )


def _build_list_response(
    user_id: UUID,
    phases_data: list[dict],
) -> LifePhaseListResponse:
    """Build a ``LifePhaseListResponse`` from computed phase data."""
    phases = []
    for p in phases_data:
        transits = [
            DominantTransit(**t) for t in p.get("dominant_transits", [])
        ]
        phases.append(LifePhase(
            phase_key=p["phase_key"],
            title=p["title"],
            start_date=p["start_date"],
            end_date=p.get("end_date"),
            description=p.get("description"),
            dominant_transits=transits,
        ))

    return LifePhaseListResponse(
        user_id=user_id,
        phases=phases,
        generated_at=datetime.now(timezone.utc),
    )
