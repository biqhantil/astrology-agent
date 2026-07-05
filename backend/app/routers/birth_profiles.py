"""Birth profile CRUD — nested under /v1/me/profile."""

from __future__ import annotations

from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.auth import AuthPayload, require_user
from app.core.deps import get_conn
from app.schemas.birth_profile import (
    BirthProfileCreate,
    BirthProfileResponse,
    BirthProfileUpdate,
)

router = APIRouter()


# ── Helpers ─────────────────────────────────────────────────────

# Approximate sun sign date ranges (tropical zodiac)
_ZODIAC_CUTOFFS: list[tuple[int, int, str]] = [
    (3, 21, "aries"),
    (4, 20, "taurus"),
    (5, 21, "gemini"),
    (6, 21, "cancer"),
    (7, 23, "leo"),
    (8, 23, "virgo"),
    (9, 23, "libra"),
    (10, 23, "scorpio"),
    (11, 22, "sagittarius"),
    (12, 22, "capricorn"),
    (1, 20, "aquarius"),
    (2, 19, "pisces"),
]


def _compute_sun_sign(birth_date: date) -> str:
    """Return the tropical sun sign for a given birth date using date ranges."""
    month = birth_date.month
    day = birth_date.day
    val = month * 100 + day

    # Ordered by start date for easy comparison
    ranges = [
        (321, 419, "aries"),       # Mar 21 - Apr 19
        (420, 520, "taurus"),      # Apr 20 - May 20
        (521, 620, "gemini"),      # May 21 - Jun 20
        (621, 722, "cancer"),      # Jun 21 - Jul 22
        (723, 822, "leo"),         # Jul 23 - Aug 22
        (823, 922, "virgo"),       # Aug 23 - Sep 22
        (923, 1022, "libra"),     # Sep 23 - Oct 22
        (1023, 1121, "scorpio"),  # Oct 23 - Nov 21
        (1122, 1221, "sagittarius"),  # Nov 22 - Dec 21
        (1222, 1231, "capricorn"),    # Dec 22 - Dec 31
        (101, 119, "capricorn"),      # Jan 1 - Jan 19
        (120, 218, "aquarius"),       # Jan 20 - Feb 18
        (219, 320, "pisces"),         # Feb 19 - Mar 20
    ]

    for start, end, sign in ranges:
        if start <= val <= end:
            return sign

    return "capricorn"

async def _fetch_profile(conn, user_id: UUID) -> dict | None:
    """Return the birth profile row for *user_id*, or ``None``."""
    row = await conn.fetchrow(
        """
        SELECT
            id, user_id, birth_date, birth_time, time_zone,
            utc_offset::text AS utc_offset,
            latitude, longitude, location_name, house_system,
            has_unknown_time, sun_sign, moon_sign, rising_sign,
            updated_at
        FROM birth_profiles
        WHERE user_id = $1
        """,
        user_id,
    )
    return dict(row) if row else None


# ── POST /v1/me/profile ─────────────────────────────────────────

@router.post("", response_model=BirthProfileResponse, status_code=status.HTTP_201_CREATED)
async def create_birth_profile(
    body: BirthProfileCreate,
    auth: AuthPayload = Depends(require_user),
    conn=Depends(get_conn),
) -> BirthProfileResponse:
    """Create a birth profile for the authenticated user.

    Only one profile per user is allowed (the UNIQUE constraint on
    ``birth_profiles.user_id`` enforces this at the database level).
    """
    user_id = UUID(auth["sub"])

    # Check if profile already exists
    existing = await conn.fetchval(
        "SELECT id FROM birth_profiles WHERE user_id = $1",
        user_id,
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Birth profile already exists for this user",
        )

    sun_sign = _compute_sun_sign(body.birth_date)

    row = await conn.fetchrow(
        """
        INSERT INTO birth_profiles
            (user_id, birth_date, birth_time, time_zone,
             latitude, longitude, location_name, house_system,
             sun_sign)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
        RETURNING
            id, user_id, birth_date, birth_time, time_zone,
            utc_offset::text AS utc_offset,
            latitude, longitude, location_name, house_system,
            has_unknown_time, sun_sign, moon_sign, rising_sign,
            updated_at
        """,
        user_id,
        body.birth_date,
        body.birth_time,
        body.time_zone,
        body.latitude,
        body.longitude,
        body.location_name,
        body.house_system,
        sun_sign,
    )
    return BirthProfileResponse(**dict(row))


# ── GET /v1/me/profile ──────────────────────────────────────────

@router.get("", response_model=BirthProfileResponse)
async def get_birth_profile(
    auth: AuthPayload = Depends(require_user),
    conn=Depends(get_conn),
) -> BirthProfileResponse:
    """Return the authenticated user's birth profile."""
    user_id = UUID(auth["sub"])
    profile = await _fetch_profile(conn, user_id)
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Birth profile not found",
        )
    return BirthProfileResponse(**profile)


# ── PUT /v1/me/profile ──────────────────────────────────────────

@router.put("", response_model=BirthProfileResponse)
async def upsert_birth_profile(
    body: BirthProfileUpdate,
    auth: AuthPayload = Depends(require_user),
    conn=Depends(get_conn),
) -> BirthProfileResponse:
    """Create or update the authenticated user's birth profile (upsert).

    Since there is a UNIQUE constraint on ``user_id``, we use ``INSERT … ON
    CONFLICT DO UPDATE`` so that a single PUT call works for both creation
    (first-time) and updates.
    """
    user_id = UUID(auth["sub"])

    put_data = body.model_dump(exclude_unset=True)
    if not put_data:
        # Nothing to upsert — return current
        profile = await _fetch_profile(conn, user_id)
        if profile is None:
            raise HTTPException(status_code=404, detail="Birth profile not found")
        return BirthProfileResponse(**profile)

    # Build INSERT column list + EXCLUDED references for the ON CONFLICT UPDATE
    insert_cols: list[str] = []
    insert_vals: list[str] = []
    update_set: list[str] = []
    params: list[object] = []
    idx = 1

    # Always include user_id
    insert_cols.append("user_id")
    insert_vals.append(f"${idx}")
    params.append(user_id)
    idx += 1

    for col, val in put_data.items():
        if val is not None and col in (
            "birth_date", "birth_time", "time_zone",
            "latitude", "longitude", "location_name", "house_system",
        ):
            insert_cols.append(col)
            placeholder = f"${idx}"
            insert_vals.append(placeholder)
            params.append(val)
            update_set.append(f"{col} = {placeholder}")
            idx += 1

    # Compute sun_sign from birth_date if provided
    if "birth_date" in put_data and put_data["birth_date"] is not None:
        sun_sign = _compute_sun_sign(put_data["birth_date"])
        insert_cols.append("sun_sign")
        placeholder = f"${idx}"
        insert_vals.append(placeholder)
        params.append(sun_sign)
        update_set.append(f"sun_sign = {placeholder}")
        idx += 1

    update_set.append(f"updated_at = now()")

    row = await conn.fetchrow(
        f"""
        INSERT INTO birth_profiles ({', '.join(insert_cols)})
        VALUES ({', '.join(insert_vals)})
        ON CONFLICT (user_id) DO UPDATE SET
            {', '.join(update_set)}
        RETURNING
            id, user_id, birth_date, birth_time, time_zone,
            utc_offset::text AS utc_offset,
            latitude, longitude, location_name, house_system,
            has_unknown_time, sun_sign, moon_sign, rising_sign,
            updated_at
        """,
        *params,
    )

    return BirthProfileResponse(**dict(row))


# ── DELETE /v1/me/profile ───────────────────────────────────────

@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
async def delete_birth_profile(
    auth: AuthPayload = Depends(require_user),
    conn=Depends(get_conn),
) -> None:
    """Delete the authenticated user's birth profile."""
    user_id = UUID(auth["sub"])
    result = await conn.execute(
        "DELETE FROM birth_profiles WHERE user_id = $1",
        user_id,
    )
    if result == "DELETE 0":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Birth profile not found",
        )
