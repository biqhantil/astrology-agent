"""Transit engine — computes current sky positions vs a natal chart.

``TransitCalculator`` generates time-series transit events by iterating a
date range, computing transiting planet positions via the ephemeris, and
comparing them against a stored set of natal chart bodies.
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from typing import Any

from app.astro_engine.aspects import (
    ASPECT_DEFS,
    _angular_separation,
    _is_applying,
)
from app.astro_engine.ephemeris import (
    DEFAULT_BODIES,
    compute_raw_ephemeris,
)

# Slow-moving planets considered most significant for transit analysis
SLOW_PLANETS = {"jupiter", "saturn", "uranus", "neptune", "pluto"}


class TransitCalculator:
    """Calculates transits of current celestial bodies against a natal chart.

    Usage::

        calc = TransitCalculator()
        events = calc.compute_transits(
            natal_bodies=[...],
            natal_houses=[...],
            start_date=date.today(),
            end_date=date.today() + timedelta(days=30),
            latitude=40.7128,
            longitude=-74.0060,
        )
    """

    def __init__(
        self,
        orb_major: float = 8.0,
        orb_minor: float = 2.0,
        include_minor: bool = True,
    ) -> None:
        self.orb_major = orb_major
        self.orb_minor = orb_minor
        self.include_minor = include_minor

    # ── Public API ──────────────────────────────────────────────

    def compute_transits(
        self,
        natal_bodies: list[dict[str, Any]],
        natal_houses: list[dict[str, Any]],
        start_date: date,
        end_date: date,
        latitude: float,
        longitude: float,
        time_zone: str = "UTC",
        transit_bodies: list[str] | None = None,
        house_system: str = "P",
    ) -> list[dict[str, Any]]:
        """Compute all transit events over a date range.

        Parameters
        ----------
        natal_bodies : list[dict]
            Rows from ``chart_bodies`` for the natal chart. Each dict must
            contain ``body_key``, ``longitude`` (numeric), ``sign``,
            ``sign_degree``, and ``house``.
        natal_houses : list[dict]
            Rows from ``chart_houses`` for the natal chart (12 rows).
        start_date : date
            First day of the transit window.
        end_date : date
            Last day of the transit window (inclusive).
        latitude, longitude : float
            Observer location for transit chart calculation (typically the
            natal chart's location).
        time_zone : str
            IANA timezone identifier.
        transit_bodies : list[str] | None
            Subset of bodies to compute transits for. Defaults to all
            standard bodies.
        house_system : str
            House system for transit charts.

        Returns
        -------
        list[dict]
            Each dict: ``{date, transiting_body, natal_body, aspect_type,
            orb, is_applying, transit_house, natal_house}``.
        """
        if transit_bodies is None:
            transit_bodies = [b for b in DEFAULT_BODIES if b not in ("north_node", "south_node", "lilith")]
            transit_bodies.extend(["asc", "mc"])

        # Build natal lookup
        natal_map: dict[str, dict[str, Any]] = {}
        for b in natal_bodies:
            natal_map[b["body_key"]] = b

        # Build natal house cusps lookup
        natal_house_map: dict[int, dict[str, Any]] = {}
        for h in natal_houses:
            natal_house_map[h["house_number"]] = h

        events: list[dict[str, Any]] = []
        current = start_date

        while current <= end_date:
            day_events = self._compute_day_transits(
                dt=current,
                latitude=latitude,
                longitude=longitude,
                house_system=house_system,
                natal_map=natal_map,
                natal_house_map=natal_house_map,
                transit_bodies=transit_bodies,
            )
            events.extend(day_events)
            current += timedelta(days=1)

        # Sort by date, then orb ascending
        events.sort(key=lambda e: (e["date"], abs(e["orb"])))
        return events

    # ── Internal ────────────────────────────────────────────────

    def _compute_day_transits(
        self,
        dt: date,
        latitude: float,
        longitude: float,
        house_system: str,
        natal_map: dict[str, dict[str, Any]],
        natal_house_map: dict[int, dict[str, Any]],
        transit_bodies: list[str],
    ) -> list[dict[str, Any]]:
        """Compute transit events for a single day."""
        dt_utc = datetime.combine(dt, time(12, 0, 0), tzinfo=timezone.utc)

        # Compute transit positions for this day
        raw = compute_raw_ephemeris(
            dt_utc=dt_utc,
            latitude=latitude,
            longitude=longitude,
            house_system=house_system,
            bodies=transit_bodies,
        )

        events: list[dict[str, Any]] = []

        for transit_key, transit_pos in raw.bodies.items():
            if transit_key not in natal_map:
                # e.g., "part_of_fortune" may not be in natal bodies
                continue

            transit_lon = transit_pos.longitude
            transit_speed = transit_pos.speed

            # Determine which natal house the transit body falls in
            transit_house = self._find_house(transit_lon, raw.house_cusps)

            # Compare against each natal body
            for natal_key, natal_body in natal_map.items():
                if natal_key in ("asc", "mc", "dsc", "ic", "part_of_fortune"):
                    # Don't transit against angles by default
                    if natal_key not in ("asc", "mc"):
                        continue

                natal_lon = float(natal_body["longitude"])
                natal_house = natal_body.get("house")

                # Compute angular separation
                for aspect_type, aspect_def in ASPECT_DEFS.items():
                    if not self.include_minor and not aspect_def["major"]:
                        continue

                    target_angle = aspect_def["angle"]
                    max_orb = self.orb_major if aspect_def["major"] else self.orb_minor

                    sep = _angular_separation(transit_lon, natal_lon)
                    orb = abs(sep - target_angle)
                    if orb > max_orb:
                        # Check the other side (for 0°/360° wrap)
                        orb_alt = abs(360 - sep - target_angle)
                        if orb_alt > max_orb:
                            if target_angle == 0 and orb_alt <= max_orb:
                                orb = orb_alt
                            else:
                                continue
                        else:
                            orb = orb_alt

                    # Determine applying/separating (natal body is stationary from transit perspective)
                    is_applying = _is_applying(
                        transit_lon,
                        natal_lon,
                        transit_speed,
                        0.0,  # natal speed is irrelevant for transit aspects
                        sep,
                        target_angle,
                    )

                    events.append({
                        "date": dt,
                        "transiting_body": transit_key,
                        "natal_body": natal_key,
                        "aspect_type": aspect_type,
                        "orb": round(orb, 2),
                        "is_applying": is_applying,
                        "transit_house": transit_house,
                        "natal_house": natal_house,
                    })
                    break  # one aspect per pair per day

        return events

    @staticmethod
    def _find_house(longitude: float, house_cusps: list[float]) -> int | None:
        """Determine which house a longitude falls in given cusps."""
        if not house_cusps or len(house_cusps) < 12:
            return None

        lon = longitude % 360
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
        return 1

    @staticmethod
    def get_significant_transits(
        events: list[dict[str, Any]],
        slow_only: bool = False,
        major_only: bool = True,
        max_results: int = 50,
    ) -> list[dict[str, Any]]:
        """Filter transit events to the most astrologically significant ones.

        Significance criteria:
        - Major aspects only (conjunction, sextile, square, trine, opposition)
        - Slow-moving planets preferred (Jupiter+)
        - Smaller orbs are more significant
        """
        filtered = list(events)

        if major_only:
            major_aspects = {"conjunction", "sextile", "square", "trine", "opposition"}
            filtered = [e for e in filtered if e["aspect_type"] in major_aspects]

        if slow_only:
            filtered = [e for e in filtered if e["transiting_body"] in SLOW_PLANETS]

        # Sort by absolute orb (smaller = more significant), then by date
        filtered.sort(key=lambda e: (e["date"], abs(e["orb"])))
        return filtered[:max_results]
