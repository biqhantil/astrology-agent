"""Chart computation and retrieval endpoints.

POST /v1/charts — create a new chart (natal, transit, etc.)
GET  /v1/charts/:id — full chart with bodies, houses, aspects
GET  /v1/charts/:id/summary — lightweight chart summary
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.astro_engine import compute_chart
from app.core.auth import AuthPayload, require_user
from app.core.deps import get_conn
from app.database import DatabasePool

# ── Domain schemas (colocated) ────────────────────────────────────
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, computed_field


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

    @computed_field  # type: ignore[prop-decorator]
    @property
    def degree(self) -> float:
        """Alias for ``sign_degree`` for clients/scenarios."""
        return float(self.sign_degree)


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

# ── Routes ──────────────────────────────────────────────────────────
router = APIRouter()


# ======================================================================
# GET /v1/charts  (list current user's charts)
# ======================================================================


@router.get("", response_model=list[ChartResponse])
async def list_charts(
    auth: AuthPayload = Depends(require_user),
    conn: DatabasePool = Depends(get_conn),
) -> list[ChartResponse]:
    """List charts owned by the authenticated user (most recent first)."""
    user_id = UUID(auth["sub"])
    rows = await conn.fetch(
        """
        SELECT id FROM charts
        WHERE user_id = $1
        ORDER BY created_at DESC
        """,
        user_id,
    )
    results: list[ChartResponse] = []
    for row in rows:
        results.append(await _fetch_chart_response(conn, row["id"], owner_id=user_id))
    return results


# ======================================================================
# POST /v1/charts
# ======================================================================


@router.post("", response_model=ChartResponse, status_code=status.HTTP_201_CREATED)
async def create_chart(
    body: ChartCreate,
    auth: AuthPayload = Depends(require_user),
    conn: DatabasePool = Depends(get_conn),
) -> ChartResponse:
    """Calculate a new astrological chart.

    Computes bodies, houses, and aspects from the given datetime and location,
    persists all data to the database, and returns the full chart.
    """
    user_id = UUID(auth["sub"])
    dt_utc = body.calculation_date
    lat = float(body.location.latitude)
    lon = float(body.location.longitude)
    tz = body.location.time_zone

    # Extract optional parameters
    ref_chart_id = body.reference_chart_id
    house_system = body.house_system
    location_name = body.location.location_name
    opts = body.options

    # Compute the chart
    try:
        result = compute_chart(
            user_id=user_id,
            chart_type=body.chart_type,
            dt_utc=dt_utc,
            latitude=lat,
            longitude=lon,
            time_zone=tz,
            house_system=house_system,
            location_name=location_name,
            reference_chart_id=ref_chart_id,
            bodies=opts.bodies if opts else None,
            orb_major=opts.orb_major if opts else 8.0,
            orb_minor=opts.orb_minor if opts else 2.0,
            include_minor_aspects=opts.include_minor_aspects if opts else True,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Chart calculation failed: {exc}",
        )

    # --- Persist to database ---
    chart = result["chart"]
    bodies = result["bodies"]
    houses = result["houses"]
    aspects = result["aspects"]

    chart_id = chart["id"]

    async with conn.transaction():
        # Insert chart
        await conn.execute(
            """
            INSERT INTO charts
                (id, user_id, chart_type, reference_chart_id, title,
                 calculation_date, house_system, location_name,
                 latitude, longitude, time_zone,
                 raw_ephemeris, metadata, created_at, expires_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8,
                    $9, $10, $11,
                    $12::jsonb, $13::jsonb, $14, $15)
            """,
            chart["id"],
            chart["user_id"],
            chart["chart_type"],
            chart["reference_chart_id"],
            chart["title"],
            chart["calculation_date"],
            chart["house_system"],
            chart["location_name"],
            chart["latitude"],
            chart["longitude"],
            chart["time_zone"],
            _jsonb(chart["raw_ephemeris"]),
            _jsonb(chart["metadata"]),
            chart["created_at"],
            chart["expires_at"],
        )

        # Insert bodies
        for b in bodies:
            await conn.execute(
                """
                INSERT INTO chart_bodies
                    (chart_id, body_key, longitude, latitude, speed,
                     sign, sign_degree, house, dignity)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                """,
                b["chart_id"],
                b["body_key"],
                b["longitude"],
                b["latitude"],
                b["speed"],
                b["sign"],
                b["sign_degree"],
                b["house"],
                b["dignity"],
            )

        # Insert houses
        for h in houses:
            await conn.execute(
                """
                INSERT INTO chart_houses
                    (chart_id, house_number, cusps_longitude, sign, sign_degree)
                VALUES ($1, $2, $3, $4, $5)
                """,
                h["chart_id"],
                h["house_number"],
                h["cusps_longitude"],
                h["sign"],
                h["sign_degree"],
            )

        # Insert aspects
        for a in aspects:
            await conn.execute(
                """
                INSERT INTO chart_aspects
                    (chart_id, body_a_key, body_b_key, aspect_type,
                     orb, is_applying, is_major)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                """,
                a["chart_id"],
                a["body_a_key"],
                a["body_b_key"],
                a["aspect_type"],
                a["orb"],
                a["is_applying"],
                a["is_major"],
            )

    # Fetch the newly created chart with joins
    return await _fetch_chart_response(conn, chart_id)


# ======================================================================
# GET /v1/charts/:id
# ======================================================================


@router.get("/{chart_id}", response_model=ChartResponse)
async def get_chart(
    chart_id: UUID,
    auth: AuthPayload = Depends(require_user),
    conn: DatabasePool = Depends(get_conn),
) -> ChartResponse:
    """Retrieve a full chart with bodies, houses, and aspects (owner only)."""
    return await _fetch_chart_response(conn, chart_id, owner_id=UUID(auth["sub"]))


# ======================================================================
# GET /v1/charts/:id/summary
# ======================================================================


@router.get("/{chart_id}/summary", response_model=ChartSummaryResponse)
async def get_chart_summary(
    chart_id: UUID,
    auth: AuthPayload = Depends(require_user),
    conn: DatabasePool = Depends(get_conn),
) -> ChartSummaryResponse:
    """Retrieve a lightweight chart summary (sun, moon, rising, key aspects)."""
    chart = await _fetch_chart_response(conn, chart_id, owner_id=UUID(auth["sub"]))

    sun = next((b for b in chart.bodies if b.body_key == "sun"), None)
    moon = next((b for b in chart.bodies if b.body_key == "moon"), None)
    rising = next((b for b in chart.bodies if b.body_key == "asc"), None)
    major_aspects = [a for a in chart.aspects if a.is_major]

    return ChartSummaryResponse(
        id=chart.id,
        chart_type=chart.chart_type,
        calculation_date=chart.calculation_date,
        sun=sun,
        moon=moon,
        rising=rising,
        key_aspects=major_aspects[:5],  # top 5 major aspects
    )


# ======================================================================
# Internal helpers
# ======================================================================


async def _fetch_chart_response(
    conn: DatabasePool,
    chart_id: UUID,
    owner_id: UUID | None = None,
) -> ChartResponse:
    """Fetch a chart and all its related data, returning a ChartResponse.

    If ``owner_id`` is set, returns 404 when the chart belongs to another user
    (avoids leaking existence across tenants).
    """
    # Fetch chart
    chart_row = await conn.fetchrow(
        """
        SELECT id, user_id, chart_type, calculation_date,
               house_system, latitude, longitude, time_zone,
               location_name, title, metadata, created_at
        FROM charts WHERE id = $1
        """,
        chart_id,
    )
    if chart_row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chart not found",
        )
    if owner_id is not None and str(chart_row["user_id"]) != str(owner_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chart not found",
        )

    # Fetch bodies
    bodies_rows = await conn.fetch(
        """
        SELECT body_key, longitude, sign, sign_degree, house,
               speed, is_retrograde, dignity
        FROM chart_bodies
        WHERE chart_id = $1
        ORDER BY
            CASE body_key
                WHEN 'asc'  THEN 0 WHEN 'sun'  THEN 1 WHEN 'moon'   THEN 2
                WHEN 'mc'   THEN 3 WHEN 'dsc'  THEN 4 WHEN 'ic'     THEN 5
                ELSE 6
            END,
            body_key
        """,
        chart_id,
    )

    # Fetch houses
    houses_rows = await conn.fetch(
        """
        SELECT house_number, cusps_longitude, sign, sign_degree
        FROM chart_houses
        WHERE chart_id = $1
        ORDER BY house_number
        """,
        chart_id,
    )

    # Fetch aspects
    aspects_rows = await conn.fetch(
        """
        SELECT body_a_key, body_b_key, aspect_type, orb,
               is_applying, is_major
        FROM chart_aspects
        WHERE chart_id = $1
        ORDER BY orb ASC
        """,
        chart_id,
    )

    return ChartResponse(
        id=chart_row["id"],
        chart_type=chart_row["chart_type"],
        user_id=chart_row["user_id"],
        calculation_date=chart_row["calculation_date"],
        house_system=chart_row["house_system"],
        latitude=chart_row["latitude"],
        longitude=chart_row["longitude"],
        time_zone=chart_row["time_zone"],
        location_name=chart_row.get("location_name"),
        title=chart_row.get("title"),
        bodies=[ChartBodyResponse(**dict(r)) for r in bodies_rows],
        houses=[ChartHouseResponse(**dict(r)) for r in houses_rows],
        aspects=[ChartAspectResponse(**dict(r)) for r in aspects_rows],
        metadata=_parse_metadata(chart_row["metadata"]),
        created_at=chart_row["created_at"],
    )


def _jsonb(obj: object) -> str:
    """Serialize an object as a JSON string for JSONB columns."""
    import json

    return json.dumps(obj, default=str)


def _parse_metadata(value: object) -> dict:
    """Parse a JSONB value returned from asyncpg into a dict.

    asyncpg returns JSONB columns as Python strings by default.
    This helper converts them to dicts for Pydantic validation.
    """
    import json

    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return {}
    if value is None:
        return {}
    return value
