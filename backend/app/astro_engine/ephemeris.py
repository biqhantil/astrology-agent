"""Swiss Ephemeris wrapper — computes planetary positions, house cusps, and angles.

Uses ``swisseph`` (pyswisseph) with the Moshier internal ephemeris as default,
falling back to JPL ephemeris files if available.  All positions returned in
tropical zodiac, ecliptic coordinates.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

import swisseph as swe

# ── Ephemeris mode ──────────────────────────────────────────────
# Use Moshier (internal, no external files) by default for speed.
# The Moshier ephemeris is accurate to ~1 arcsecond for planets and
# doesn't require downloading the full JPL ephemeris files.
# Fall back to SWIEPH if available (auto-detected).
_FLAGS = swe.FLG_MOSEPH | swe.FLG_SPEED

# ── Planet index constants ──────────────────────────────────────

#: Mapping of human-friendly body keys to Swiss Ephemeris planet numbers.
BODY_EPHEM_INDEX: dict[str, int] = {
    "sun": swe.SUN,          # 0
    "moon": swe.MOON,        # 1
    "mercury": swe.MERCURY,  # 2
    "venus": swe.VENUS,      # 3
    "mars": swe.MARS,        # 4
    "jupiter": swe.JUPITER,  # 5
    "saturn": swe.SATURN,    # 6
    "uranus": swe.URANUS,    # 7
    "neptune": swe.NEPTUNE,  # 8
    "pluto": swe.PLUTO,      # 9
    # True Node (north_node is the DB column name; true_node kept for compat)
    "north_node": swe.TRUE_NODE,  # 11
    "true_node": swe.TRUE_NODE,   # 11 (alias, kept for backward compat)
    "south_node": swe.TRUE_NODE,  # 11 (same calc, will invert longitude)
    # Lilith / Black Moon Lilith (mean_apog kept for compat)
    "lilith": swe.MEAN_APOG,       # 12 (Black Moon Lilith)
    "mean_apog": swe.MEAN_APOG,    # 12 (alias, kept for backward compat)
    "chiron": swe.CHIRON,    # 15
}

#: House system codes (single uppercase letter).
HOUSE_SYSTEMS: dict[str, bytes] = {
    "P": b"P",  # Placidus
    "W": b"W",  # Whole Sign
    "K": b"K",  # Koch
    "E": b"E",  # Equal
    "R": b"R",  # Regiomontanus
    "C": b"C",  # Campanus
    "V": b"V",  # Vehlow
}

# Zodiac signs
ZODIAC_SIGNS = [
    "aries", "taurus", "gemini", "cancer",
    "leo", "virgo", "libra", "scorpio",
    "sagittarius", "capricorn", "aquarius", "pisces",
]

# Standard set of bodies for a natal chart
DEFAULT_BODIES = [
    "sun", "moon", "mercury", "venus", "mars",
    "jupiter", "saturn", "uranus", "neptune", "pluto",
    "north_node", "chiron", "lilith",
]

# ======================================================================
# Data containers
# ======================================================================


@dataclass
class RawBodyPosition:
    """Raw position for a single celestial body from the ephemeris."""

    body_key: str
    longitude: float        # 0–360°
    latitude: float         # ecliptic latitude
    speed: float            # °/day, negative = retrograde
    is_retrograde: bool


@dataclass
class RawEphemeris:
    """Complete raw output of a chart calculation."""

    julian_day: float
    bodies: dict[str, RawBodyPosition]  # keyed by body_key
    house_cusps: list[float]            # cusps[1..12]
    ascendant: float
    mc: float
    houses_ascmc: tuple                   # raw ascmc from swe.houses_ex
    calc_flags: int


# ======================================================================
# Helper: convert longitude to sign
# ======================================================================


def longitude_to_sign(longitude: float) -> tuple[str, float]:
    """Convert ecliptic longitude 0–360° to (sign_name, degree_within_sign)."""
    idx = int(longitude // 30) % 12
    degree = longitude % 30
    return ZODIAC_SIGNS[idx], degree


# ======================================================================
# Core compute function
# ======================================================================


def compute_raw_ephemeris(
    dt_utc: datetime,
    latitude: float,
    longitude: float,
    house_system: str = "P",
    bodies: list[str] | None = None,
) -> RawEphemeris:
    """Compute raw ephemeris data for a given datetime and location.

    Parameters
    ----------
    dt_utc : datetime
        The date and time **in UTC** for which to compute the chart.
    latitude : float
        Geographic latitude (-90 to 90).
    longitude : float
        Geographic longitude (-180 to 180).
    house_system : str
        One-letter house system code (default ``P`` = Placidus).
    bodies : list[str] | None
        List of body keys to compute.  Defaults to
        ``DEFAULT_BODIES`` (sun … mean_apog).

    Returns
    -------
    RawEphemeris
        Structured raw output with all positions, houses, and angles.
    """
    if bodies is None:
        bodies = DEFAULT_BODIES

    # --- 1. Julian Day ---
    jd = _datetime_to_jd(dt_utc)

    # --- 2. Planet positions ---
    raw_bodies: dict[str, RawBodyPosition] = {}

    for key in bodies:
        ephem_idx = BODY_EPHEM_INDEX.get(key)
        if ephem_idx is None:
            continue  # skip unknown body keys (angles handled separately)

        # Compute node / special handling
        if key == "south_node":
            # South Node = opposite of North Node
            pos_south = _calc_planet(jd, ephem_idx, _FLAGS)
            if pos_south is not None:
                lon = (pos_south[0] + 180) % 360
                lat = -pos_south[1]
                speed = pos_south[3]
                raw_bodies[key] = RawBodyPosition(
                    body_key=key,
                    longitude=lon,
                    latitude=lat,
                    speed=speed,
                    is_retrograde=speed < 0,
                )
            continue

        pos = _calc_planet(jd, ephem_idx, _FLAGS)
        if pos is None:
            continue

        raw_bodies[key] = RawBodyPosition(
            body_key=key,
            longitude=pos[0],
            latitude=pos[1],
            speed=pos[3],
            is_retrograde=pos[3] < 0,
        )

    # --- 3. Houses & angles ---
    house_sys_bytes = HOUSE_SYSTEMS.get(house_system, b"P")
    cusps, ascmc = swe.houses_ex(jd, latitude, longitude, house_sys_bytes)

    # cusps is a 12-element tuple (house 1–12)
    # ascmc: [0]=asc, [1]=mc, [2]=armc, [3]=vertex, ...

    ascendant = ascmc[0]
    mc = ascmc[1]

    # Add angle bodies
    raw_bodies["asc"] = RawBodyPosition(
        body_key="asc",
        longitude=ascendant,
        latitude=0.0,
        speed=0.0,
        is_retrograde=False,
    )
    raw_bodies["mc"] = RawBodyPosition(
        body_key="mc",
        longitude=mc,
        latitude=0.0,
        speed=0.0,
        is_retrograde=False,
    )
    raw_bodies["dsc"] = RawBodyPosition(
        body_key="dsc",
        longitude=(ascendant + 180) % 360,
        latitude=0.0,
        speed=0.0,
        is_retrograde=False,
    )
    raw_bodies["ic"] = RawBodyPosition(
        body_key="ic",
        longitude=(mc + 180) % 360,
        latitude=0.0,
        speed=0.0,
        is_retrograde=False,
    )

    # Part of Fortune: ASC + Moon - Sun (day formula)
    if "moon" in raw_bodies and "sun" in raw_bodies:
        moon_lon = raw_bodies["moon"].longitude
        sun_lon = raw_bodies["sun"].longitude
        pof = (ascendant + moon_lon - sun_lon) % 360
        raw_bodies["part_of_fortune"] = RawBodyPosition(
            body_key="part_of_fortune",
            longitude=pof,
            latitude=0.0,
            speed=0.0,
            is_retrograde=False,
        )

    return RawEphemeris(
        julian_day=jd,
        bodies=raw_bodies,
        house_cusps=list(cusps),  # cusps[0] is house 1
        ascendant=ascendant,
        mc=mc,
        houses_ascmc=ascmc,
        calc_flags=_FLAGS,
    )


# ======================================================================
# Internal helpers
# ======================================================================


def _datetime_to_jd(dt: datetime) -> float:
    """Convert a UTC datetime to Julian Day using swisseph."""
    # Ensure UTC
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)

    # Date arithmetic for Swiss Ephemeris
    year = dt.year
    month = dt.month
    day = dt.day
    hour = dt.hour + dt.minute / 60.0 + dt.second / 3600.0

    # Use GREG_CAL (1) if date is after Oct 15, 1582
    if year > 1582 or (year == 1582 and (month > 10 or (month == 10 and day >= 15))):
        gregflag = swe.GREG_CAL
    else:
        gregflag = swe.JUL_CAL

    return swe.julday(year, month, day, hour, gregflag)


def _calc_planet(jd: float, planet_idx: int, flags: int) -> tuple[float, ...] | None:
    """Calculate a single planet's position.

    Returns ``None`` if the ephemeris file is missing (e.g., asteroids).
    """
    try:
        result = swe.calc_ut(jd, planet_idx, flags)
        # result is a tuple: (longitude, latitude, distance, lon_speed, lat_speed, dist_speed)
        # result[0] contains the main array
        return result[0]
    except swe.Error:
        return None
    except Exception:
        return None


def longitude_to_sign_degree(longitude: float) -> dict[str, Any]:
    """Convert longitude to sign info dict.

    Returns ``{"sign": "aries", "sign_degree": 15.5, "longitude": 15.5}``
    """
    sign, degree = longitude_to_sign(longitude)
    return {
        "sign": sign,
        "sign_degree": float(Decimal(str(degree)).quantize(Decimal("0.01"))),
        "longitude": float(Decimal(str(longitude)).quantize(Decimal("0.0000001"))),
    }
