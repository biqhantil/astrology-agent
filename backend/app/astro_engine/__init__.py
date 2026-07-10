"""Astrological calculation engine.

Public entry point: ``compute_chart()`` — runs the full pipeline:
  1. Time normalization → JD
  2. Ephemeris compute (bodies, houses, angles)
  3. Aspect detection
  4. Dignity assignment
  5. Serialization → DB-ready rows

Modules:
  - ephemeris.py   Swiss Ephemeris wrapper (positions, houses)
  - aspects.py     Aspect detection engine
  - serializers.py DB serialization + essential dignity
  - transit.py / synastry.py / life_phases.py — domain calculators
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from app.astro_engine.aspects import compute_aspects
from app.astro_engine.ephemeris import (
    DEFAULT_BODIES,
    compute_raw_ephemeris,
)
from app.astro_engine.serializers import serialize_chart


def compute_chart(
    user_id: UUID,
    chart_type: str,
    dt_utc: datetime,
    latitude: float,
    longitude: float,
    time_zone: str,
    house_system: str = "P",
    location_name: str | None = None,
    reference_chart_id: UUID | None = None,
    title: str | None = None,
    bodies: list[str] | None = None,
    *,
    include_aspects: bool = True,
    orb_major: float = 8.0,
    orb_minor: float = 2.0,
    include_minor_aspects: bool = True,
) -> dict:
    """Compute a full astrological chart and return DB-ready serialised rows.

    This is the main public API of the ``astro_engine`` package.

    Parameters
    ----------
    user_id : UUID
        Owner of the chart (must exist in ``users`` table).
    chart_type : str
        ``"natal"``, ``"transit"``, ``"progressed"``, ``"solar_return"``,
        ``"synastry_composite"``, ``"event"``.
    dt_utc : datetime
        The UTC date/time for the chart calculation.
    latitude : float
        Geographic latitude (-90 to 90).
    longitude : float
        Geographic longitude (-180 to 180).
    time_zone : str
        IANA timezone identifier (e.g., ``"America/New_York"``).
    house_system : str
        One-letter house system (default ``"P"`` = Placidus).
    location_name : str or None
        Human-readable location label.
    reference_chart_id : UUID or None
        For transit/progressed charts, the base natal chart.
    title : str or None
        Optional user-facing label.
    bodies : list[str] or None
        List of body keys to compute. Defaults to all standard bodies.
    include_aspects : bool
        Whether to compute aspects (default True).
    orb_major : float
        Maximum orb for major aspects (default 8°).
    orb_minor : float
        Maximum orb for minor aspects (default 2°).
    include_minor_aspects : bool
        Whether to compute minor aspects (default True).

    Returns
    -------
    dict
        Keys ``chart``, ``bodies``, ``houses``, ``aspects`` containing
        dicts/lists suitable for DB insertion.
    """
    if bodies is None:
        bodies = DEFAULT_BODIES

    # ── Step 1-2: Ephemeris computation ──
    raw = compute_raw_ephemeris(
        dt_utc=dt_utc,
        latitude=latitude,
        longitude=longitude,
        house_system=house_system,
        bodies=bodies,
    )

    # ── Step 3: Aspect computation ──
    aspects = None
    if include_aspects:
        # Build body dict with longitude and speed for aspect engine
        body_dict = {}
        for key, pos in raw.bodies.items():
            body_dict[key] = {
                "longitude": pos.longitude,
                "speed": pos.speed,
            }

        aspects = compute_aspects(
            body_dict,
            orb_major=orb_major,
            orb_minor=orb_minor,
            include_minor=include_minor_aspects,
            include_angles=False,  # don't aspect angles (asc, mc, etc.)
        )

    # ── Step 4-5: Serialization ──
    serialized = serialize_chart(
        user_id=user_id,
        chart_type=chart_type,
        calculation_date=dt_utc,
        latitude=latitude,
        longitude=longitude,
        time_zone=time_zone,
        house_system=house_system,
        raw_ephemeris=raw,
        location_name=location_name,
        reference_chart_id=reference_chart_id,
        title=title,
        aspects=aspects,
    )

    return serialized
