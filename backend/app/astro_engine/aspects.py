"""Aspect detection engine — computes aspects between celestial bodies.

Iterates over all body pairs, computes angular separation, and tests against
established orbs.  Classifies major vs minor aspects and determines
applying/separating direction via speed differential.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# ── Aspect definitions ──────────────────────────────────────────

ASPECT_DEFS: dict[str, dict[str, Any]] = {
    "conjunction": {"angle": 0, "orb": 8, "major": True},
    "opposition": {"angle": 180, "orb": 8, "major": True},
    "trine": {"angle": 120, "orb": 8, "major": True},
    "square": {"angle": 90, "orb": 8, "major": True},
    "sextile": {"angle": 60, "orb": 6, "major": True},
    "quincunx": {"angle": 150, "orb": 3, "major": False},
    "semi_sextile": {"angle": 30, "orb": 3, "major": False},
    "semi_square": {"angle": 45, "orb": 2, "major": False},
    "sesquiquadrate": {"angle": 135, "orb": 2, "major": False},
}

# Default orbs for major and minor aspects
DEFAULT_ORB_MAJOR = 8.0
DEFAULT_ORB_MINOR = 2.0


@dataclass
class Aspect:
    """A single aspect between two bodies."""

    body_a_key: str
    body_b_key: str
    aspect_type: str
    orb: float          # degrees from exact (0 = exact)
    is_applying: bool | None  # True = applying, False = separating, None = stationary
    is_major: bool


# ======================================================================
# Aspect computation
# ======================================================================


def compute_aspects(
    bodies: dict[str, dict[str, Any]],
    *,
    orb_major: float = DEFAULT_ORB_MAJOR,
    orb_minor: float = DEFAULT_ORB_MINOR,
    include_minor: bool = True,
    major_only: bool = False,
    include_angles: bool = True,
    exclude_body_pairs: set[tuple[str, str]] | None = None,
) -> list[Aspect]:
    """Compute all aspects between bodies in a chart.

    Parameters
    ----------
    bodies : dict[str, dict]
        Dictionary keyed by body_key, where each value is a dict containing
        at least ``longitude`` (float) and ``speed`` (float, °/day).
    orb_major : float
        Maximum orb for major aspects (conjunction, sextile, square, trine,
        opposition).  Default 8°.
    orb_minor : float
        Maximum orb for minor aspects (quincunx, semi-sextile, semi-square,
        sesquiquadrate).  Default 2°.
    include_minor : bool
        Whether to compute minor aspects.  Default True.
    major_only : bool
        If True, only compute major aspects (ignores *include_minor*).
    include_angles : bool
        Whether to include angles (asc, mc, dsc, ic) in aspect computation.
        Default True.
    exclude_body_pairs : set[tuple[str, str]] | None
        Set of (body_a, body_b) pairs to skip (e.g., always skip angles).

    Returns
    -------
    list[Aspect]
        Detected aspects sorted by absolute orb (smallest first).
    """
    if exclude_body_pairs is None:
        exclude_body_pairs = set()

    # Filter bodies if angles should be excluded
    body_keys = list(bodies.keys())
    if not include_angles:
        angle_keys = {"asc", "mc", "dsc", "ic", "part_of_fortune"}
        body_keys = [k for k in body_keys if k not in angle_keys]

    aspects: list[Aspect] = []
    n = len(body_keys)

    for i in range(n):
        for j in range(i + 1, n):
            key_a = body_keys[i]
            key_b = body_keys[j]

            # Skip excluded pairs
            if (key_a, key_b) in exclude_body_pairs or (key_b, key_a) in exclude_body_pairs:
                continue

            body_a = bodies[key_a]
            body_b = bodies[key_b]

            lon_a = body_a.get("longitude", 0.0)
            lon_b = body_b.get("longitude", 0.0)
            speed_a = body_a.get("speed", 0.0)
            speed_b = body_b.get("speed", 0.0)

            # Compute angular separation (shortest arc 0–180°)
            sep = _angular_separation(lon_a, lon_b)

            # Test each aspect type
            for aspect_type, aspect_def in ASPECT_DEFS.items():
                if major_only and not aspect_def["major"]:
                    continue
                if not include_minor and not aspect_def["major"]:
                    continue

                target_angle = aspect_def["angle"]
                max_orb = aspect_def["orb"]

                # Use custom orbs if specified
                if aspect_def["major"]:
                    max_orb = orb_major
                else:
                    max_orb = orb_minor

                # Check if separation is within orb
                orb = abs(sep - target_angle)
                if orb > max_orb:
                    # Also check the "other side" (for 0°/360° wrap)
                    orb = abs(360 - sep - target_angle)
                    if orb > max_orb:
                        # For 0° aspects, check both sides
                        if target_angle == 0:
                            if orb > max_orb:
                                continue
                        else:
                            continue

                # Determine applying / separating
                is_applying = _is_applying(lon_a, lon_b, speed_a, speed_b, sep, target_angle)

                aspects.append(Aspect(
                    body_a_key=key_a,
                    body_b_key=key_b,
                    aspect_type=aspect_type,
                    orb=round(orb, 2),
                    is_applying=is_applying,
                    is_major=aspect_def["major"],
                ))
                break  # only one aspect per pair (closest match)

    # Sort by smallest orb first
    aspects.sort(key=lambda a: a.orb)
    return aspects


# ======================================================================
# Helpers
# ======================================================================


def _angular_separation(lon1: float, lon2: float) -> float:
    """Compute the shortest angular distance between two longitudes.

    Returns a value between 0 and 180 degrees.
    """
    diff = abs(lon1 - lon2) % 360
    if diff > 180:
        diff = 360 - diff
    return diff


def _is_applying(
    lon_a: float,
    lon_b: float,
    speed_a: float,
    speed_b: float,
    separation: float,
    target_angle: float,
) -> bool | None:
    """Determine if the aspect is applying (getting closer) or separating.

    Returns ``True`` for applying, ``False`` for separating, ``None`` if
    stationary (cannot determine).
    """
    # Speed differential: how fast body_a is catching up to body_b
    diff_speed = speed_a - speed_b

    if abs(diff_speed) < 0.001:
        return None  # stationary

    # Compute the forward arc from body_a to body_b (zodiacal order)
    arc_forward = (lon_b - lon_a) % 360  # 0–360

    # Determine if the bodies are moving toward or away from the target angle
    if target_angle == 0:
        # Conjunction: bodies are getting closer if arc is decreasing
        if diff_speed > 0:
            return arc_forward < 180  # body_a catching up from behind
        else:
            return arc_forward > 180  # body_b catching up from behind
    elif target_angle == 180:
        # Opposition: bodies are getting closer to 180° separation
        if diff_speed > 0:
            return arc_forward < 180  # body_a moving toward opposition
        else:
            return arc_forward > 180
    else:
        # For other aspects, simplified approach
        if diff_speed > 0:
            return arc_forward < target_angle
        else:
            return arc_forward > (360 - target_angle)
