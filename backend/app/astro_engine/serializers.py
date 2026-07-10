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
from app.astro_engine.ephemeris import (
    RawEphemeris,
    RawBodyPosition,
    ZODIAC_SIGNS,
    longitude_to_sign,
)

# ── Essential dignity (merged from dignity.py) ───────────────────
# ── Dignity tables ──────────────────────────────────────────────
# Format: {body_key: {sign_index: dignity_string}}

# Body keys mapped to sign indices (0=Aries, 1=Taurus, ..., 11=Pisces)
# Domicile: planet rules the sign
# Detriment: planet is in the opposite sign of its domicile
# Exaltation: planet is exalted in this sign
# Fall: planet is in the opposite sign of its exaltation

#: Planetary rulers (domicile) by sign index.
DOMICILE: dict[str, int] = {
    "sun": 4,         # Leo
    "moon": 3,        # Cancer
    "mercury": 5,     # Virgo (also Gemini, handled below)
    "venus": 6,       # Libra (also Taurus)
    "mars": 0,        # Aries (also Scorpio)
    "jupiter": 8,     # Sagittarius (also Pisces)
    "saturn": 9,      # Capricorn (also Aquarius)
    "uranus": 10,     # Aquarius
    "neptune": 11,    # Pisces
    "pluto": 7,       # Scorpio
    "chiron": 8,      # Sagittarius (traditional)
}

#: Secondary domicile (co-ruler) for dual-ruled signs.
DOMICILE_SECONDARY: dict[str, int] = {
    "mercury": 2,     # Gemini
    "venus": 1,       # Taurus
    "mars": 7,        # Scorpio
    "jupiter": 11,    # Pisces
    "saturn": 10,     # Aquarius
}

#: Exaltation by planet.
EXALTATION: dict[str, int] = {
    "sun": 0,         # Aries
    "moon": 1,        # Taurus
    "mercury": 5,     # Virgo
    "venus": 11,      # Pisces
    "mars": 9,        # Capricorn
    "jupiter": 3,     # Cancer
    "saturn": 6,      # Libra
    "uranus": 7,      # Scorpio
    "neptune": 4,     # Leo
    "pluto": 5,       # Virgo
    "chiron": 2,      # Gemini
}


def _opposite_sign(sign_idx: int) -> int:
    """Return the index of the opposite sign (6 signs apart)."""
    return (sign_idx + 6) % 12


def assign_dignity(body_key: str, sign: str) -> str | None:
    """Assign essential dignity for a body in a given sign.

    Parameters
    ----------
    body_key : str
        The body identifier (e.g., ``"sun"``, ``"moon"``, ``"mars"``).
    sign : str
        The zodiac sign name (lowercase, e.g., ``"leo"``, ``"virgo"``).

    Returns
    -------
    str or None
        One of ``"domicile"``, ``"exaltation"``, ``"detriment"``, ``"fall"``,
        ``"peregrine"``, or ``None`` if the body is not in the dignity tables.
    """
    from app.astro_engine.ephemeris import ZODIAC_SIGNS

    try:
        sign_idx = ZODIAC_SIGNS.index(sign)
    except ValueError:
        return None

    # Check domicile (primary)
    if body_key in DOMICILE and DOMICILE[body_key] == sign_idx:
        return "domicile"

    # Check secondary domicile
    if body_key in DOMICILE_SECONDARY and DOMICILE_SECONDARY[body_key] == sign_idx:
        return "domicile"

    # Check detriment (opposite of domicile)
    if body_key in DOMICILE:
        if _opposite_sign(DOMICILE[body_key]) == sign_idx:
            return "detriment"
    if body_key in DOMICILE_SECONDARY:
        if _opposite_sign(DOMICILE_SECONDARY[body_key]) == sign_idx:
            return "detriment"

    # Check exaltation
    if body_key in EXALTATION and EXALTATION[body_key] == sign_idx:
        return "exaltation"

    # Check fall (opposite of exaltation)
    if body_key in EXALTATION and _opposite_sign(EXALTATION[body_key]) == sign_idx:
        return "fall"

    # Check if the body has dignity tables (only planets with known rulers)
    known_bodies = set(DOMICILE.keys()) | set(DOMICILE_SECONDARY.keys()) | set(EXALTATION.keys())
    if body_key in known_bodies:
        return "peregrine"

    return None



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
