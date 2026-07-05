"""Serialization layer — transforms raw ephemeris data into DB-ready rows.

Converts ``RawEphemeris`` + aspects into dicts suitable for inserting into
the ``charts``, ``chart_bodies``, ``chart_houses``, and ``chart_aspects``
tables.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from app.astro_engine.aspects import Aspect
from app.astro_engine.dignity import assign_dignity
from app.astro_engine.ephemeris import (
    RawEphemeris,
    RawBodyPosition,
    ZODIAC_SIGNS,
    longitude_to_sign,
)


def serialize_chart(
    user_id: UUID,
    chart_type: str,
    calculation_date: datetime,
    latitude: float,
    longitude: float,
    time_zone: str,
    house_system: str,
    raw_ephemeris: RawEphemeris,
    location_name: str | None = None,
    reference_chart_id: UUID | None = None,
    title: str | None = None,
    aspects: list[Aspect] | None = None,
) -> dict[str, Any]:
    """Serialize a full chart computation into DB-ready dicts.

    Returns
    -------
    dict
        Keys:
        - ``chart``: row dict for ``charts`` table
        - ``bodies``: list of row dicts for ``chart_bodies`` table
        - ``houses``: list of row dicts for ``chart_houses`` table
        - ``aspects``: list of row dicts for ``chart_aspects`` table
    """
    chart_id = uuid4()
    now = datetime.now(timezone.utc)

    # --- Chart row ---
    chart_row: dict[str, Any] = {
        "id": chart_id,
        "user_id": user_id,
        "chart_type": chart_type,
        "reference_chart_id": reference_chart_id,
        "title": title,
        "calculation_date": calculation_date,
        "house_system": house_system,
        "location_name": location_name,
        "latitude": Decimal(str(round(latitude, 6))),
        "longitude": Decimal(str(round(longitude, 6))),
        "time_zone": time_zone,
        "raw_ephemeris": _serialize_raw_ephemeris(raw_ephemeris),
        "metadata": {
            "ephemeris_version": "swisseph-20230604",
            "calculation_library": "pyswisseph",
            "house_system": house_system,
            "calc_flags": raw_ephemeris.calc_flags,
        },
        "created_at": now,
        "expires_at": None,
    }

    # --- Bodies rows ---
    bodies_rows: list[dict[str, Any]] = []
    for body_key, pos in raw_ephemeris.bodies.items():
        sign, sign_deg = longitude_to_sign(pos.longitude)
        body_dict = _serialize_body(chart_id, body_key, pos, sign, sign_deg, raw_ephemeris)
        bodies_rows.append(body_dict)

    # --- Houses rows ---
    houses_rows: list[dict[str, Any]] = []
    for i in range(12):
        house_num = i + 1
        cusp_lon = raw_ephemeris.house_cusps[i]
        sign, sign_deg = longitude_to_sign(cusp_lon)
        houses_rows.append({
            "chart_id": chart_id,
            "house_number": house_num,
            "cusps_longitude": Decimal(str(round(cusp_lon, 7))),
            "sign": sign,
            "sign_degree": Decimal(str(round(sign_deg, 2))),
        })

    # --- Aspects rows ---
    aspects_rows: list[dict[str, Any]] = []
    if aspects:
        for asp in aspects:
            aspects_rows.append({
                "chart_id": chart_id,
                "body_a_key": asp.body_a_key,
                "body_b_key": asp.body_b_key,
                "aspect_type": asp.aspect_type,
                "orb": Decimal(str(round(asp.orb, 2))),
                "is_applying": asp.is_applying,
                "is_major": asp.is_major,
            })

    return {
        "chart": chart_row,
        "bodies": bodies_rows,
        "houses": houses_rows,
        "aspects": aspects_rows,
    }


def _serialize_body(
    chart_id: UUID,
    body_key: str,
    pos: RawBodyPosition,
    sign: str,
    sign_deg: float,
    raw: RawEphemeris,
) -> dict[str, Any]:
    """Serialize a single body position into a chart_bodies row."""
    longitude = float(Decimal(str(round(pos.longitude, 7))))
    latitude = float(Decimal(str(round(pos.latitude, 7))))
    speed = float(Decimal(str(round(pos.speed, 7))))
    sign_deg_rounded = float(Decimal(str(round(sign_deg, 2))))

    # Assign house (bodies in houses)
    house = _assign_house(pos.longitude, raw.house_cusps)

    # Assign dignity
    dignity = assign_dignity(body_key, sign)

    return {
        "chart_id": chart_id,
        "body_key": body_key,
        "longitude": Decimal(str(longitude)),
        "latitude": Decimal(str(latitude)),
        "speed": Decimal(str(speed)),
        "sign": sign,
        "sign_degree": Decimal(str(sign_deg_rounded)),
        "house": house,
        "dignity": dignity,
    }


def _assign_house(longitude: float, house_cusps: list[float]) -> int | None:
    """Determine which house a body falls in given the cusp list.

    Returns house number 1–12, or None if unable to determine.
    """
    if not house_cusps or len(house_cusps) < 12:
        return None

    # Normalize longitude and cusps to 0–360
    lon = longitude % 360

    # Find the house where cusp[i] <= lon < cusp[i+1]
    # Handle the wrap-around at 0°
    for i in range(12):
        cusp_start = house_cusps[i] % 360
        cusp_end = house_cusps[(i + 1) % 12] % 360

        if cusp_start <= cusp_end:
            if cusp_start <= lon < cusp_end:
                return i + 1
        else:
            # Wrap around (e.g., cusp_start=350, cusp_end=20)
            if lon >= cusp_start or lon < cusp_end:
                return i + 1

    return 1  # fallback


def _serialize_raw_ephemeris(raw: RawEphemeris) -> dict[str, Any]:
    """Convert RawEphemeris to a JSON-serializable dict for JSONB storage."""
    bodies_json: dict[str, dict[str, Any]] = {}
    for key, pos in raw.bodies.items():
        bodies_json[key] = {
            "longitude": round(pos.longitude, 7),
            "latitude": round(pos.latitude, 7),
            "speed": round(pos.speed, 7),
            "is_retrograde": pos.is_retrograde,
        }

    return {
        "julian_day": raw.julian_day,
        "bodies": bodies_json,
        "house_cusps": [round(c, 7) for c in raw.house_cusps],
        "ascendant": round(raw.ascendant, 7),
        "mc": round(raw.mc, 7),
        "ascmc_raw": list(raw.houses_ascmc),
        "calc_flags": raw.calc_flags,
    }
