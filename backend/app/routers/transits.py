"""Transit endpoints — current sky vs natal chart comparisons.

POST /v1/charts/{chart_id}/transits — compute transits for a date range
GET  /v1/charts/{chart_id}/transits — retrieve cached transit snapshot(s)
"""

from __future__ import annotations

import json
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.astro_engine.transit import TransitCalculator
from app.core.auth import AuthPayload, require_user
from app.core.deps import get_conn
from app.database import DatabasePool
from app.schemas.transit import (
    TransitEvent,
    TransitRequest,
    TransitSnapshotResponse,
    TransitSummaryResponse,
)

router = APIRouter()

# Transit cache TTL (transit snapshots expire after this duration)
TRANSIT_CACHE_DAYS = 7


# ======================================================================
# POST /v1/charts/{chart_id}/transits
# ======================================================================


@router.post("/{chart_id}/transits", response_model=TransitSnapshotResponse, status_code=status.HTTP_201_CREATED)
async def create_transits(
    chart_id: UUID,
    body: TransitRequest,
    auth: AuthPayload = Depends(require_user),
    conn: DatabasePool = Depends(get_conn),
) -> TransitSnapshotResponse:
    """Compute transits for a natal chart over a date range.

    Accepts optional ``start_date`` and ``end_date`` (defaults to today
    through +30 days). Computes daily transit positions, compares against
    the stored natal chart bodies, and returns all aspect events.
    """
    user_id = UUID(auth["sub"])

    # --- Fetch the natal chart ---
    chart_row = await conn.fetchrow(
        """
        SELECT id, user_id, chart_type, latitude, longitude, time_zone,
               house_system, raw_ephemeris
        FROM charts
        WHERE id = $1
        """,
        chart_id,
    )
    if chart_row is None:
        raise HTTPException(status_code=404, detail="Chart not found")

    # Only natal charts can be used as transit base
    # (but we accept any chart type for flexibility)

    # --- Fetch natal bodies and houses ---
    natal_bodies = await conn.fetch(
        """
        SELECT body_key, longitude, sign, sign_degree, house, speed, dignity
        FROM chart_bodies
        WHERE chart_id = $1
        """,
        chart_id,
    )
    if not natal_bodies:
        raise HTTPException(status_code=404, detail="Chart has no bodies computed")

    natal_houses = await conn.fetch(
        """
        SELECT house_number, cusps_longitude, sign, sign_degree
        FROM chart_houses
        WHERE chart_id = $1
        ORDER BY house_number
        """,
        chart_id,
    )

    # --- Parse inputs ---
    today = date.today()
    start_date = body.start_date or today
    end_date = body.end_date or (today + timedelta(days=30))
    transit_bodies = body.bodies

    if start_date > end_date:
        raise HTTPException(
            status_code=422,
            detail="start_date must be before or equal to end_date",
        )

    # --- Run transit calculator ---
    calc = TransitCalculator()
    try:
        transit_events = calc.compute_transits(
            natal_bodies=[dict(r) for r in natal_bodies],
            natal_houses=[dict(r) for r in natal_houses],
            start_date=start_date,
            end_date=end_date,
            latitude=float(chart_row["latitude"]),
            longitude=float(chart_row["longitude"]),
            time_zone=chart_row["time_zone"],
            transit_bodies=transit_bodies,
            house_system=chart_row["house_system"],
        )
    except Exception as exc:
        raise HTTPException(
            status_code=422,
            detail=f"Transit calculation failed: {exc}",
        )

    # --- Store in transit_snapshots ---
    snapshot_id = uuid4()
    expires_at = datetime.now(timezone.utc) + timedelta(days=TRANSIT_CACHE_DAYS)

    # Serialize events to JSONB-safe dicts
    events_json = [
        {
            "date": str(e["date"]),
            "transiting_body": e["transiting_body"],
            "natal_body": e["natal_body"],
            "aspect_type": e["aspect_type"],
            "orb": e["orb"],
            "is_applying": e["is_applying"],
            "transit_house": e["transit_house"],
            "natal_house": e["natal_house"],
        }
        for e in transit_events
    ]

    await conn.execute(
        """
        INSERT INTO transit_snapshots
            (id, natal_chart_id, date_from, date_to,
             transit_events, created_at, expires_at)
        VALUES ($1, $2, $3, $4, $5::jsonb, now(), $6)
        """,
        snapshot_id,
        chart_id,
        start_date,
        end_date,
        json.dumps(events_json),
        expires_at,
    )

    # --- Build response ---
    return TransitSnapshotResponse(
        id=snapshot_id,
        natal_chart_id=chart_id,
        date_from=start_date,
        date_to=end_date,
        transit_events=[TransitEvent(**e) for e in events_json],
        created_at=datetime.now(timezone.utc),
        expires_at=expires_at,
    )


# ======================================================================
# GET /v1/charts/{chart_id}/transits
# ======================================================================


@router.get("/{chart_id}/transits", response_model=list[TransitSnapshotResponse])
async def get_transits(
    chart_id: UUID,
    auth: AuthPayload = Depends(require_user),
    conn: DatabasePool = Depends(get_conn),
    date_from: date | None = Query(None, description="Earliest transit date filter"),
    date_to: date | None = Query(None, description="Latest transit date filter"),
    limit: int = Query(10, ge=1, le=100, description="Max snapshots to return"),
) -> list[TransitSnapshotResponse]:
    """Retrieve cached transit snapshots for a chart.

    Returns the most recent transit snapshots, optionally filtered by
    date range. New transit computations should be created via
    ``POST /v1/charts/{chart_id}/transits``.
    """
    # Build query with optional date filtering
    query = """
        SELECT id, natal_chart_id, date_from, date_to,
               transit_events, created_at, expires_at
        FROM transit_snapshots
        WHERE natal_chart_id = $1
    """
    params: list[object] = [chart_id]
    idx = 2

    if date_from:
        query += f" AND date_to >= ${idx}"
        params.append(date_from)
        idx += 1

    if date_to:
        query += f" AND date_from <= ${idx}"
        params.append(date_to)
        idx += 1

    query += " ORDER BY created_at DESC LIMIT $" + str(idx)
    params.append(limit)

    rows = await conn.fetch(query, *params)

    if not rows:
        raise HTTPException(
            status_code=404,
            detail="No transit snapshots found for this chart. "
            "Create one via POST /v1/charts/{chart_id}/transits first.",
        )

    result: list[TransitSnapshotResponse] = []
    for row in rows:
        events_data = row["transit_events"]
        if isinstance(events_data, str):
            events_data = json.loads(events_data)

        result.append(TransitSnapshotResponse(
            id=row["id"],
            natal_chart_id=row["natal_chart_id"],
            date_from=row["date_from"],
            date_to=row["date_to"],
            transit_events=[TransitEvent(**e) for e in events_data],
            created_at=row["created_at"],
            expires_at=row["expires_at"],
        ))

    return result


# ======================================================================
# GET /v1/charts/{chart_id}/transits/summary
# ======================================================================


@router.get("/{chart_id}/transits/summary", response_model=TransitSummaryResponse)
async def get_transit_summary(
    chart_id: UUID,
    auth: AuthPayload = Depends(require_user),
    conn: DatabasePool = Depends(get_conn),
) -> TransitSummaryResponse:
    """Return a condensed summary of the most recent transit snapshot.

    Focuses on major aspects from slow-moving planets.
    """
    rows = await conn.fetch(
        """
        SELECT id, natal_chart_id, date_from, date_to,
               transit_events, created_at, expires_at
        FROM transit_snapshots
        WHERE natal_chart_id = $1
        ORDER BY created_at DESC
        LIMIT 1
        """,
        chart_id,
    )

    if not rows:
        raise HTTPException(
            status_code=404,
            detail="No transit snapshots found for this chart.",
        )

    row = rows[0]
    events_data = row["transit_events"]
    if isinstance(events_data, str):
        events_data = json.loads(events_data)

    all_events = [TransitEvent(**e) for e in events_data]

    # Filter to major aspects only
    major_aspects = {"conjunction", "sextile", "square", "trine", "opposition"}
    major_events = [e for e in all_events if e.aspect_type in major_aspects]

    # Slow planet transits
    slow_planets = {"jupiter", "saturn", "uranus", "neptune", "pluto"}
    slow_events = [e for e in major_events if e.transiting_body in slow_planets]

    return TransitSummaryResponse(
        natal_chart_id=chart_id,
        date_from=row["date_from"],
        date_to=row["date_to"],
        total_events=len(all_events),
        major_events=major_events,
        slow_planets=slow_events,
    )
