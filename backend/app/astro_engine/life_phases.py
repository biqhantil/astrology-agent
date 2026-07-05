"""Life Phase Engine — computes major life phase milestones from a natal chart.

Phases are derived from the user's birth year and Saturn position in the
natal chart. The engine calculates approximate windows for:

- **Foundation** (0–27): Early life, before the first Saturn return.
- **Saturn Return 1** (~27–31): First Saturn return — maturity, accountability.
- **Expansion** (~31–41): Post-Saturn, Jupiter-driven growth.
- **Uranus Opposition** (~41–45): Midlife awakening, restructuring.
- **Saturn Return 2** (~56–60): Second Saturn return — legacy, wisdom.
- **Legacy** (~60+): Later years, culmination, reflection.
- **Chiron Return** (~49–53): Healing and integration cycle.
"""

from __future__ import annotations

import math
from datetime import date, datetime
from typing import Any

# ── Constants ───────────────────────────────────────────────────

# Saturn's orbital period in years (approx)
SATURN_ORBITAL_PERIOD = 29.5

# Default age ranges for each phase (used if Saturn position unknown)
PHASE_AGE_RANGES: dict[str, tuple[int, int | None]] = {
    "foundation": (0, 27),
    "saturn_return_1": (27, 31),
    "expansion": (31, 41),
    "uranus_opposition": (41, 45),
    "chiron_return": (49, 53),
    "saturn_return_2": (56, 60),
    "legacy": (60, None),  # None = ongoing / indefinite
}

PHASE_TITLES: dict[str, str] = {
    "foundation": "Foundation Years",
    "saturn_return_1": "First Saturn Return",
    "expansion": "Expansion & Growth",
    "uranus_opposition": "Uranus Opposition (Midlife Awakening)",
    "chiron_return": "Chiron Return (Deep Healing)",
    "saturn_return_2": "Second Saturn Return",
    "legacy": "Legacy & Reflection",
}

PHASE_DESCRIPTIONS: dict[str, str] = {
    "foundation": (
        "Early life — forming identity, family imprint, education, and "
        "the foundational structures that will be tested at the first Saturn return."
    ),
    "saturn_return_1": (
        "A pivotal maturity checkpoint. Saturn returns to its natal position, "
        "signaling the end of youth and the beginning of adult responsibility. "
        "Career, relationships, and life direction are often restructured."
    ),
    "expansion": (
        "A period of growth, opportunity, and exploration driven by Jupiter's "
        "transits. The lessons of the first Saturn return are applied toward "
        "building a meaningful life."
    ),
    "uranus_opposition": (
        "Uranus opposes its natal position, triggering a midlife awakening. "
        "Deep-seated patterns surface for transformation. Often involves "
        "major life changes — career shifts, relationship re-evaluation, "
        "or creative rebirth."
    ),
    "chiron_return": (
        "Chiron returns to its natal position, activating the deepest "
        "wounding and healing potential. A time for profound inner work, "
        "therapy, and integrating past trauma."
    ),
    "saturn_return_2": (
        "The second Saturn return marks a transition into wisdom and "
        "authority. Life review, legacy-building, and mentorship come to "
        "the forefront. Often coincides with retirement or major status shifts."
    ),
    "legacy": (
        "The later years — reflection, legacy, and integration of life "
        "experience. The focus shifts from achievement to meaning, "
        "generativity, and passing on wisdom."
    ),
}


# ======================================================================
# Life Phase Calculator
# ======================================================================


class LifePhaseCalculator:
    """Computes life phase milestones from a natal chart.

    Usage::

        calc = LifePhaseCalculator()
        phases = calc.compute_phases(
            birth_date=date(1990, 6, 15),
            saturn_longitude=280.5,   # Saturn position in natal chart
        )
    """

    def __init__(
        self,
        saturn_period: float = SATURN_ORBITAL_PERIOD,
    ) -> None:
        self.saturn_period = saturn_period

    # ── Public API ──────────────────────────────────────────────

    def compute_phases(
        self,
        birth_date: date,
        saturn_longitude: float | None = None,
        *,
        include_descriptions: bool = True,
        include_dominant_transits: bool = True,
    ) -> list[dict[str, Any]]:
        """Compute the full life phase timeline for a user.

        Parameters
        ----------
        birth_date : date
            The user's date of birth.
        saturn_longitude : float | None
            Saturn's ecliptic longitude in the natal chart (0–360°).
            If ``None``, phases are estimated from default age ranges.
        include_descriptions : bool
            Whether to include human-readable phase descriptions.
        include_dominant_transits : bool
            Whether to compute dominant transit activations for each phase.

        Returns
        -------
        list[dict]
            Ordered list of phase dicts, each with keys:
            ``phase_key``, ``title``, ``start_date``, ``end_date``,
            ``description`` (optional), ``dominant_transits`` (optional).
        """
        birth_year = birth_date.year
        phases: list[dict[str, Any]] = []

        # Determine precise phase windows based on Saturn position
        phase_windows = self._compute_phase_windows(
            birth_date, saturn_longitude,
        )

        for phase_key, (start_age, end_age) in phase_windows.items():
            start_date = self._age_to_date(birth_date, start_age)
            end_date = self._age_to_date(birth_date, end_age) if end_age is not None else None

            phase: dict[str, Any] = {
                "phase_key": phase_key,
                "title": PHASE_TITLES.get(phase_key, phase_key),
                "start_date": start_date,
                "end_date": end_date,
            }

            if include_descriptions:
                phase["description"] = PHASE_DESCRIPTIONS.get(phase_key, "")

            if include_dominant_transits:
                phase["dominant_transits"] = self._compute_dominant_transits(
                    phase_key, start_date, end_date, saturn_longitude,
                )

            phases.append(phase)

        return phases

    def get_current_phase(
        self,
        birth_date: date,
        saturn_longitude: float | None = None,
        as_of_date: date | None = None,
    ) -> dict[str, Any] | None:
        """Return the phase active on *as_of_date* (or today)."""
        if as_of_date is None:
            as_of_date = date.today()

        phases = self.compute_phases(birth_date, saturn_longitude)
        for phase in phases:
            start = phase["start_date"]
            end = phase["end_date"]
            if start <= as_of_date and (end is None or as_of_date <= end):
                return phase
        return None

    # ── Phase window computation ────────────────────────────────

    def _compute_phase_windows(
        self,
        birth_date: date,
        saturn_longitude: float | None,
    ) -> dict[str, tuple[int, int | None]]:
        """Determine the age-based windows for each life phase.

        If Saturn's natal longitude is available, Saturn return ages are
        computed precisely. Otherwise, default age ranges are used.
        """
        if saturn_longitude is not None:
            # Saturn return occurs when transiting Saturn returns to birth position
            # ~29.5 years, but can vary based on Saturn's current speed/retrograde
            saturn_return_1_age = self._compute_saturn_return_age(
                birth_date, saturn_longitude, return_number=1,
            )
            saturn_return_2_age = self._compute_saturn_return_age(
                birth_date, saturn_longitude, return_number=2,
            )
        else:
            saturn_return_1_age = 29.5
            saturn_return_2_age = 59.0

        # Build phase windows using Saturn return ages as anchor points
        return {
            "foundation": (0, int(saturn_return_1_age - 2)),
            "saturn_return_1": (
                int(saturn_return_1_age - 2),
                int(saturn_return_1_age + 2),
            ),
            "expansion": (
                int(saturn_return_1_age + 2),
                int(saturn_return_1_age + 12),
            ),
            "uranus_opposition": (
                int(saturn_return_1_age + 12),
                int(saturn_return_1_age + 16),
            ),
            "chiron_return": (
                int(saturn_return_1_age + 20),
                int(saturn_return_1_age + 24),
            ),
            "saturn_return_2": (
                int(saturn_return_2_age - 2),
                int(saturn_return_2_age + 2),
            ),
            "legacy": (
                int(saturn_return_2_age + 2),
                None,
            ),
        }

    @staticmethod
    def _compute_saturn_return_age(
        birth_date: date,
        saturn_longitude: float,
        return_number: int = 1,
    ) -> float:
        """Estimate the age at which Saturn returns to its natal position.

        Saturn takes ~29.5 years per full cycle. This method accounts for
        Saturn's speed variation and retrogradation.

        Returns the age in years (including fractional) at the approximate
        Saturn return date.
        """
        # Base age from Saturn's orbital period
        base_age = SATURN_ORBITAL_PERIOD * return_number

        # Adjust based on Saturn's natal position:
        # Saturn's speed varies from ~0.95° to ~1.05° per day depending on
        # its position in the orbit (aphelion/perihelion).
        # Approximate correction using zodiacal position:
        # Saturn is faster at perihelion (~Sagittarius) and slower at aphelion (~Gemini).
        if saturn_longitude is not None:
            # Normalize to 0-360
            lon = saturn_longitude % 360
            # Speed factor: ~1.0 at 0° (Aries), ~1.05 at 270° (Capricorn perihelion),
            # ~0.95 at 90° (Cancer aphelion)
            speed_factor = 1.0 + 0.05 * math.sin(math.radians(lon - 270))
            # Adjust the base age inversely (faster Saturn = shorter return period)
            adjusted_age = base_age / speed_factor
        else:
            adjusted_age = base_age

        return round(adjusted_age, 1)

    @staticmethod
    def _age_to_date(birth_date: date, age_years: int) -> date:
        """Convert an age in years to a calendar date."""
        try:
            return date(
                birth_date.year + age_years,
                birth_date.month,
                birth_date.day,
            )
        except ValueError:
            # Handle Feb 29 birthdays in non-leap years
            import calendar

            year = birth_date.year + age_years
            month = birth_date.month
            day = min(birth_date.day, calendar.monthrange(year, month)[1])
            return date(year, month, day)

    # ── Dominant transit computation ────────────────────────────

    def _compute_dominant_transits(
        self,
        phase_key: str,
        start_date: date,
        end_date: date | None,
        saturn_longitude: float | None,
    ) -> list[dict[str, Any]]:
        """Generate dominant planetary activations for a given phase.

        Returns a list of notable transits that define this phase,
        derived from the natal Saturn position and the phase's meaning.
        """
        if saturn_longitude is None:
            return []

        transits: list[dict[str, Any]] = []

        if phase_key == "foundation":
            # Early life: Saturn square (age ~7), Saturn opposition (~14)
            transits.extend([
                {
                    "planet": "saturn",
                    "aspect": "square",
                    "natal_body": "saturn",
                    "date": str(self._age_to_date(
                        date.today().replace(year=start_date.year) if start_date.year > 1900 else start_date,
                        int(7.5),
                    )),
                    "description": "Saturn square Saturn — early challenges and structure-building",
                },
                {
                    "planet": "saturn",
                    "aspect": "opposition",
                    "natal_body": "saturn",
                    "date": str(self._age_to_date(
                        date.today().replace(year=start_date.year) if start_date.year > 1900 else start_date,
                        int(14.5),
                    )),
                    "description": "Saturn opposition Saturn — adolescence, authority struggles",
                },
            ])

        elif phase_key == "saturn_return_1":
            # Saturn return exact hits
            transits.append({
                "planet": "saturn",
                "aspect": "conjunction",
                "natal_body": "saturn",
                "date": str(self._age_to_date(
                    date.today().replace(year=start_date.year),
                    int(29.5),
                )),
                "description": "First Saturn return — maturity checkpoint, life restructuring",
            })

        elif phase_key == "expansion":
            # Jupiter transits, Saturn trine/sextile
            transits.extend([
                {
                    "planet": "jupiter",
                    "aspect": "conjunction",
                    "natal_body": "jupiter",
                    "date": str(self._age_to_date(
                        date.today().replace(year=start_date.year),
                        int(36),
                    )),
                    "description": "Jupiter return — cyclical growth and opportunity",
                },
            ])

        elif phase_key == "uranus_opposition":
            transits.append({
                "planet": "uranus",
                "aspect": "opposition",
                "natal_body": "uranus",
                "date": str(self._age_to_date(
                    date.today().replace(year=start_date.year),
                    int(42),
                )),
                "description": "Uranus opposition — midlife awakening, restructuring",
            })

        elif phase_key == "chiron_return":
            transits.append({
                "planet": "chiron",
                "aspect": "conjunction",
                "natal_body": "chiron",
                "date": str(self._age_to_date(
                    date.today().replace(year=start_date.year),
                    int(50),
                )),
                "description": "Chiron return — deep healing, integration of wounds",
            })

        elif phase_key == "saturn_return_2":
            transits.append({
                "planet": "saturn",
                "aspect": "conjunction",
                "natal_body": "saturn",
                "date": str(self._age_to_date(
                    date.today().replace(year=start_date.year),
                    int(59),
                )),
                "description": "Second Saturn return — wisdom, legacy, life review",
            })

        elif phase_key == "legacy":
            transits.extend([
                {
                    "planet": "saturn",
                    "aspect": "trine",
                    "natal_body": "saturn",
                    "date": str(self._age_to_date(
                        date.today().replace(year=start_date.year),
                        int(65),
                    )),
                    "description": "Saturn trine Saturn — integration and wisdom",
                },
                {
                    "planet": "neptune",
                    "aspect": "square",
                    "natal_body": "neptune",
                    "date": str(self._age_to_date(
                        date.today().replace(year=start_date.year),
                        int(67),
                    )),
                    "description": "Neptune square Neptune — spiritual deepening or confusion",
                },
            ])

        return transits


# ======================================================================
# Convenience function
# ======================================================================


def compute_life_phases(
    birth_date: date,
    saturn_longitude: float | None = None,
    *,
    include_descriptions: bool = True,
    include_dominant_transits: bool = True,
) -> list[dict[str, Any]]:
    """Convenience wrapper — computes life phases with default calculator.

    Usage::

        phases = compute_life_phases(
            birth_date=date(1990, 6, 15),
            saturn_longitude=280.5,
        )
    """
    calc = LifePhaseCalculator()
    return calc.compute_phases(
        birth_date=birth_date,
        saturn_longitude=saturn_longitude,
        include_descriptions=include_descriptions,
        include_dominant_transits=include_dominant_transits,
    )
