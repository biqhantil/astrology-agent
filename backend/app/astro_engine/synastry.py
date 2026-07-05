"""Synastry engine — computes inter-chart aspects and house overlays.

Compares two natal charts body-by-body to produce:
- Inter-chart aspects (Chart A body vs Chart B body)
- House overlays (where Chart A's bodies fall in Chart B's houses, and vice versa)
- Compatibility scoring based on aspect analysis
"""

from __future__ import annotations

from typing import Any

from app.astro_engine.aspects import (
    ASPECT_DEFS,
    _angular_separation,
    _is_applying,
)
from app.astro_engine.serializers import _assign_house

# Body categories for scoring dimensions
EMOTIONAL_BODIES = {"moon", "venus", "neptune"}
COMMUNICATION_BODIES = {"mercury", "sun", "jupiter"}
PASSION_BODIES = {"mars", "pluto", "sun", "venus"}
COMMITMENT_BODIES = {"saturn", "sun", "moon", "jupiter"}

# Aspect weights for scoring (higher = more harmonius for positive aspects)
HARMONIOUS_ASPECTS = {"conjunction": 1.0, "sextile": 0.8, "trine": 1.0}
CHALLENGING_ASPECTS = {"square": -0.8, "opposition": -0.6, "quincunx": -0.4}
NEUTRAL_ASPECTS = {"semi_sextile": 0.2, "semi_square": -0.2, "sesquiquadrate": -0.3}


def compute_synastry(
    chart_a_bodies: list[dict[str, Any]],
    chart_b_bodies: list[dict[str, Any]],
    chart_a_houses: list[dict[str, Any]] | None = None,
    chart_b_houses: list[dict[str, Any]] | None = None,
    orb_major: float = 8.0,
    orb_minor: float = 2.0,
    include_minor: bool = True,
) -> dict[str, Any]:
    """Compute inter-chart aspects and house overlays between two charts.

    Parameters
    ----------
    chart_a_bodies : list[dict]
        Rows from ``chart_bodies`` for the first chart. Each dict must
        contain ``body_key``, ``longitude`` (numeric), ``sign``,
        ``sign_degree``, ``house``, ``speed``.
    chart_b_bodies : list[dict]
        Rows from ``chart_bodies`` for the second chart.
    chart_a_houses : list[dict] | None
        Rows from ``chart_houses`` for chart A, for house overlay analysis.
    chart_b_houses : list[dict] | None
        Rows from ``chart_houses`` for chart B, for house overlay analysis.
    orb_major : float
        Maximum orb for major aspects.
    orb_minor : float
        Maximum orb for minor aspects.
    include_minor : bool
        Whether to include minor aspects.

    Returns
    -------
    dict
        Keys:
        - ``aspects``: list of aspect dicts
        - ``score_summary``: dict with emotional, communication, passion,
          commitment, overall scores (0–10)
        - ``house_overlays_a_in_b``: chart A's bodies in chart B's houses
        - ``house_overlays_b_in_a``: chart B's bodies in chart A's houses
    """
    # Build lookup maps
    bodies_a: dict[str, dict[str, Any]] = {}
    for b in chart_a_bodies:
        bodies_a[b["body_key"]] = b

    bodies_b: dict[str, dict[str, Any]] = {}
    for b in chart_b_bodies:
        bodies_b[b["body_key"]] = b

    # Build house cusp lists
    cusps_a: list[float] | None = None
    cusps_b: list[float] | None = None
    if chart_a_houses:
        cusps_a = [float(h["cusps_longitude"]) for h in sorted(chart_a_houses, key=lambda x: x["house_number"])]
    if chart_b_houses:
        cusps_b = [float(h["cusps_longitude"]) for h in sorted(chart_b_houses, key=lambda x: x["house_number"])]

    # ---- Compute inter-chart aspects ----
    aspects: list[dict[str, Any]] = _compute_inter_aspects(
        bodies_a, bodies_b, orb_major, orb_minor, include_minor,
    )

    # ---- Compute house overlays ----
    house_overlays_a_in_b = _compute_house_overlays(bodies_a, cusps_b)
    house_overlays_b_in_a = _compute_house_overlays(bodies_b, cusps_a)

    # ---- Compute scoring ----
    score_summary = _compute_scores(aspects)

    return {
        "aspects": aspects,
        "score_summary": score_summary,
        "house_overlays_a_in_b": house_overlays_a_in_b,
        "house_overlays_b_in_a": house_overlays_b_in_a,
    }


# ======================================================================
# Internal helpers
# ======================================================================


def _compute_inter_aspects(
    bodies_a: dict[str, dict[str, Any]],
    bodies_b: dict[str, dict[str, Any]],
    orb_major: float,
    orb_minor: float,
    include_minor: bool,
) -> list[dict[str, Any]]:
    """Compute aspects between every body in chart A vs every body in chart B."""
    aspects: list[dict[str, Any]] = []

    # Bodies to exclude from cross-aspecting
    angle_keys = {"asc", "mc", "dsc", "ic", "part_of_fortune"}

    for key_a, body_a in bodies_a.items():
        if key_a in angle_keys:
            continue
        lon_a = float(body_a["longitude"])
        speed_a = float(body_a.get("speed", 0.0))

        for key_b, body_b in bodies_b.items():
            if key_b in angle_keys:
                continue
            if key_a == key_b:
                continue
            lon_b = float(body_b["longitude"])

            for aspect_type, aspect_def in ASPECT_DEFS.items():
                if not include_minor and not aspect_def["major"]:
                    continue

                target_angle = aspect_def["angle"]
                max_orb = orb_major if aspect_def["major"] else orb_minor

                sep = _angular_separation(lon_a, lon_b)
                orb = abs(sep - target_angle)
                if orb > max_orb:
                    orb_alt = abs(360 - sep - target_angle)
                    if orb_alt > max_orb:
                        if target_angle == 0 and orb_alt <= max_orb:
                            orb = orb_alt
                        else:
                            continue
                    else:
                        orb = orb_alt

                is_applying = _is_applying(
                    lon_a, lon_b, speed_a, float(body_b.get("speed", 0.0)),
                    sep, target_angle,
                )

                aspects.append({
                    "body_a_key": key_a,
                    "body_b_key": key_b,
                    "aspect_type": aspect_type,
                    "orb": round(orb, 2),
                    "is_applying": is_applying,
                })
                break  # one aspect per pair

    # Sort by orb ascending
    aspects.sort(key=lambda a: abs(a["orb"]))
    return aspects


def _compute_house_overlays(
    bodies: dict[str, dict[str, Any]],
    cusps: list[float] | None,
) -> dict[str, int | None]:
    """Determine which house each body falls in, given a set of cusps."""
    if cusps is None or len(cusps) < 12:
        return {key: None for key in bodies}

    overlays: dict[str, int | None] = {}
    for key, body in bodies.items():
        lon = float(body["longitude"])
        overlays[key] = _assign_house(lon, cusps)
    return overlays


def _compute_scores(
    aspects: list[dict[str, Any]],
) -> dict[str, float | None]:
    """Compute compatibility dimension scores from inter-chart aspects.

    Each dimension is scored 0–10 based on weighted aspect analysis.
    """
    if not aspects:
        return {
            "emotional": None,
            "communication": None,
            "passion": None,
            "commitment": None,
            "overall": None,
        }

    scores: dict[str, float | None] = {}

    for dimension, body_set in [
        ("emotional", EMOTIONAL_BODIES),
        ("communication", COMMUNICATION_BODIES),
        ("passion", PASSION_BODIES),
        ("commitment", COMMITMENT_BODIES),
    ]:
        relevant = [
            a for a in aspects
            if a["body_a_key"] in body_set or a["body_b_key"] in body_set
        ]
        if not relevant:
            scores[dimension] = None
            continue

        raw = 5.0  # start at neutral
        for asp in relevant:
            weight = _aspect_weight(asp["aspect_type"], asp["orb"])
            raw += weight

        # Clamp to 0–10
        scores[dimension] = round(max(0.0, min(10.0, raw)), 1)

    # Overall = average of non-None dimensions
    valid = [v for v in scores.values() if v is not None]
    if valid:
        scores["overall"] = round(sum(valid) / len(valid), 1)
    else:
        scores["overall"] = None

    return scores


def _aspect_weight(aspect_type: str, orb: float) -> float:
    """Return the scoring weight for an aspect, modulated by orb."""
    base = HARMONIOUS_ASPECTS.get(aspect_type) or CHALLENGING_ASPECTS.get(aspect_type) or NEUTRAL_ASPECTS.get(aspect_type) or 0.0
    # Reduce weight for wider orbs (orb 0 = full weight, orb 8 = ~halved)
    orb_factor = max(0.0, 1.0 - (orb / 10.0))
    return base * orb_factor
