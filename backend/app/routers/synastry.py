"""Synastry endpoints — inter-chart compatibility analysis.

POST /v1/synastry — compute synastry between two charts
GET  /v1/synastry/{id} — retrieve full synastry data
GET  /v1/synastry — list synastry pairs for the current user
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.astro_engine.synastry import compute_synastry
from app.core.auth import AuthPayload, require_user
from app.core.deps import get_conn
from app.database import DatabasePool

# ── Domain schemas (colocated) ────────────────────────────────────
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

# ── Routes ──────────────────────────────────────────────────────────
router = APIRouter()


# ======================================================================
# POST /v1/synastry
# ======================================================================


@router.post("", response_model=SynastryResponse, status_code=status.HTTP_201_CREATED)
async def create_synastry(
    body: SynastryCreate,
    auth: AuthPayload = Depends(require_user),
    conn: DatabasePool = Depends(get_conn),
) -> SynastryResponse:
    """Compute synastry between two charts.

    Loads both charts' bodies and houses, computes inter-chart aspects,
    house overlays, and compatibility scores, then persists the results.
    """
    user_id = UUID(auth["sub"])

    chart_a_id = body.chart_a_id
    chart_b_id = body.chart_b_id

    if chart_a_id == chart_b_id:
        raise HTTPException(
            status_code=422,
            detail="Cannot compute synastry between a chart and itself",
        )

    # --- Fetch both charts ---
    chart_a = await conn.fetchrow(
        "SELECT id, user_id, chart_type, house_system FROM charts WHERE id = $1",
        chart_a_id,
    )
    chart_b = await conn.fetchrow(
        "SELECT id, user_id, chart_type, house_system FROM charts WHERE id = $1",
        chart_b_id,
    )

    if not chart_a or not chart_b:
        raise HTTPException(
            status_code=404,
            detail="One or both charts not found",
        )

    # --- Fetch bodies for both charts ---
    bodies_a = await conn.fetch(
        "SELECT body_key, longitude, latitude, speed, sign, sign_degree, house, dignity "
        "FROM chart_bodies WHERE chart_id = $1",
        chart_a_id,
    )
    bodies_b = await conn.fetch(
        "SELECT body_key, longitude, latitude, speed, sign, sign_degree, house, dignity "
        "FROM chart_bodies WHERE chart_id = $1",
        chart_b_id,
    )

    if not bodies_a or not bodies_b:
        raise HTTPException(
            status_code=422,
            detail="One or both charts have no bodies computed",
        )

    # --- Fetch houses for both charts ---
    houses_a = await conn.fetch(
        "SELECT house_number, cusps_longitude, sign, sign_degree "
        "FROM chart_houses WHERE chart_id = $1 ORDER BY house_number",
        chart_a_id,
    )
    houses_b = await conn.fetch(
        "SELECT house_number, cusps_longitude, sign, sign_degree "
        "FROM chart_houses WHERE chart_id = $1 ORDER BY house_number",
        chart_b_id,
    )

    # --- Compute synastry ---
    try:
        synastry_result = compute_synastry(
            chart_a_bodies=[dict(r) for r in bodies_a],
            chart_b_bodies=[dict(r) for r in bodies_b],
            chart_a_houses=[dict(r) for r in houses_a],
            chart_b_houses=[dict(r) for r in houses_b],
        )
    except Exception as exc:
        raise HTTPException(
            status_code=422,
            detail=f"Synastry calculation failed: {exc}",
        )

    # --- Persist synastry ---
    synastry_id = uuid4()
    aspects = synastry_result["aspects"]
    score_summary = synastry_result["score_summary"]
    overlays_a_in_b = synastry_result["house_overlays_a_in_b"]
    overlays_b_in_a = synastry_result["house_overlays_b_in_a"]

    score_json = json.dumps(score_summary) if score_summary else "null"

    async with conn.transaction():
        # Insert synastry_pairs
        await conn.execute(
            """
            INSERT INTO synastry_pairs
                (id, user_id, chart_a_id, chart_b_id,
                 relationship_type, score_summary, created_at)
            VALUES ($1, $2, $3, $4, $5, $6::jsonb, now())
            """,
            synastry_id,
            user_id,
            chart_a_id,
            chart_b_id,
            body.relationship_type,
            score_json,
        )

        # Insert synastry_aspects
        for asp in aspects:
            # Build house overlay for this specific pair
            ho: dict[str, object] = {}
            if asp["body_a_key"] in overlays_a_in_b:
                ho["body_a_house_in_chart_b"] = overlays_a_in_b[asp["body_a_key"]]
            if asp["body_b_key"] in overlays_b_in_a:
                ho["body_b_house_in_chart_a"] = overlays_b_in_a[asp["body_b_key"]]

            await conn.execute(
                """
                INSERT INTO synastry_aspects
                    (synastry_id, chart_a_id, chart_b_id,
                     body_a_key, body_b_key, aspect_type,
                     orb, is_applying, house_overlay)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9::jsonb)
                """,
                synastry_id,
                chart_a_id,
                chart_b_id,
                asp["body_a_key"],
                asp["body_b_key"],
                asp["aspect_type"],
                asp["orb"],
                asp["is_applying"],
                json.dumps(ho) if ho else None,
            )

    # Return the created synastry
    return await _fetch_synastry_response(conn, synastry_id)


# ======================================================================
# GET /v1/synastry/{synastry_id}
# ======================================================================


@router.get("/{synastry_id}", response_model=SynastryResponse)
async def get_synastry(
    synastry_id: UUID,
    auth: AuthPayload = Depends(require_user),
    conn: DatabasePool = Depends(get_conn),
) -> SynastryResponse:
    """Retrieve a complete synastry analysis with all inter-chart aspects."""
    return await _fetch_synastry_response(conn, synastry_id)


# ======================================================================
# GET /v1/synastry
# ======================================================================


@router.get("", response_model=list[SynastryListResponse])
async def list_synastry(
    auth: AuthPayload = Depends(require_user),
    conn: DatabasePool = Depends(get_conn),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> list[SynastryListResponse]:
    """List all synastry pairs for the authenticated user."""
    user_id = UUID(auth["sub"])

    rows = await conn.fetch(
        """
        SELECT id, chart_a_id, chart_b_id, relationship_type,
               score_summary, created_at
        FROM synastry_pairs
        WHERE user_id = $1
        ORDER BY created_at DESC
        LIMIT $2 OFFSET $3
        """,
        user_id,
        limit,
        offset,
    )

    result: list[SynastryListResponse] = []
    for row in rows:
        score = row["score_summary"]
        if isinstance(score, str):
            score = json.loads(score)
        result.append(SynastryListResponse(
            id=row["id"],
            chart_a_id=row["chart_a_id"],
            chart_b_id=row["chart_b_id"],
            relationship_type=row.get("relationship_type"),
            score_summary=ScoreSummary(**score) if score else None,
            created_at=row["created_at"],
        ))

    return result


# ======================================================================
# Internal helpers
# ======================================================================


async def _fetch_synastry_response(
    conn: DatabasePool,
    synastry_id: UUID,
) -> SynastryResponse:
    """Fetch a synastry pair and all its aspects, returning a SynastryResponse."""
    row = await conn.fetchrow(
        """
        SELECT id, user_id, chart_a_id, chart_b_id,
               relationship_type, score_summary,
               composite_chart_id, davison_chart_id,
               created_at
        FROM synastry_pairs
        WHERE id = $1
        """,
        synastry_id,
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Synastry not found")

    # Fetch aspects
    aspect_rows = await conn.fetch(
        """
        SELECT body_a_key, body_b_key, aspect_type, orb,
               is_applying, house_overlay
        FROM synastry_aspects
        WHERE synastry_id = $1
        ORDER BY orb ASC
        """,
        synastry_id,
    )

    aspects: list[SynastryAspectResponse] = []
    for r in aspect_rows:
        ho = r["house_overlay"]
        if isinstance(ho, str):
            ho = json.loads(ho)
        aspects.append(SynastryAspectResponse(
            body_a_key=r["body_a_key"],
            body_b_key=r["body_b_key"],
            aspect_type=r["aspect_type"],
            orb=float(r["orb"]),
            is_applying=r["is_applying"],
            house_overlay=ho,
        ))

    # Parse score summary
    score_data = row["score_summary"]
    if isinstance(score_data, str):
        score_data = json.loads(score_data)
    score_summary = ScoreSummary(**score_data) if score_data else None

    return SynastryResponse(
        id=row["id"],
        user_id=row["user_id"],
        chart_a_id=row["chart_a_id"],
        chart_b_id=row["chart_b_id"],
        relationship_type=row.get("relationship_type"),
        aspects=aspects,
        score_summary=score_summary,
        composite_chart_id=row.get("composite_chart_id"),
        davison_chart_id=row.get("davison_chart_id"),
        created_at=row["created_at"],
    )
