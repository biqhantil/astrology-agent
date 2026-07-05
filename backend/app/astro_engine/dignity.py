"""Essential dignity lookup tables and assignment logic.

Assigns essential dignity — domicile, exaltation, detriment, fall, peregrine —
to each body based on its sign placement.
"""

from __future__ import annotations

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
    from .ephemeris import ZODIAC_SIGNS

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
