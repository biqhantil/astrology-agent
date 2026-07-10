"""Tool definitions and execution functions for the astrology LLM.

JSON Schema tool definitions are used in the OpenAI-compatible API request.
Execution functions call into the existing ``astro_engine`` modules and
return structured data for both the LLM and SSE event stream.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any
from uuid import UUID

from app.astro_engine import compute_chart
from app.astro_engine.life_phases import compute_life_phases
from app.astro_engine.synastry import compute_synastry
from app.astro_engine.transit import TransitCalculator


# ======================================================================
# JSON Schema Tool Definitions (for LLM function calling)
# ======================================================================

TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "render_natal_chart",
            "description": (
                "Compute the user's natal (birth) chart — planet positions, houses, and aspects. "
                "ONLY call this when natal placements are NOT already in the system prompt / "
                "Current Chart Context. Skip if chart data is already injected."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "user_id": {
                        "type": "string",
                        "description": "The UUID of the user whose natal chart to compute (optional — defaults to the current user)",
                    },
                },
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "render_transit_timeline",
            "description": (
                "Compute current or upcoming transits against the user's natal chart for a date range. "
                "Use for today/week/month forecasts. chart_id is optional (defaults to user's natal). "
                "Prefer a tight window (1–30 days) unless the user asks for longer."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "chart_id": {
                        "type": "string",
                        "description": "UUID of the natal chart (optional — defaults to user's natal)",
                    },
                    "start_date": {
                        "type": "string",
                        "description": "Start date for the transit window (YYYY-MM-DD format, e.g. 2026-07-06)",
                    },
                    "end_date": {
                        "type": "string",
                        "description": "End date for the transit window (YYYY-MM-DD format, e.g. 2026-08-06)",
                    },
                },
                "required": ["start_date", "end_date"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "render_synastry",
            "description": "Compare two natal charts for relationship compatibility. Computes inter-chart aspects, house overlays, and dimension scores (emotional, communication, passion, commitment). Use when comparing two people's charts for relationship insight.",
            "parameters": {
                "type": "object",
                "properties": {
                    "chart_a_id": {
                        "type": "string",
                        "description": "UUID of the first chart (typically the user's natal chart)",
                    },
                    "chart_b_id": {
                        "type": "string",
                        "description": "UUID of the second chart (the partner / other person's chart)",
                    },
                },
                "required": ["chart_a_id", "chart_b_id"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "render_life_phases",
            "description": (
                "Compute major life phase milestones (Saturn returns, Uranus opposition, "
                "Chiron return, Expansion, Legacy). ONLY use when the user asks about life "
                "phase, Saturn return, or life-timing eras — NOT for general natal overview, "
                "Moon, career, or daily forecasts."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "user_id": {
                        "type": "string",
                        "description": "The UUID of the user whose life phases to compute (optional — defaults to the current user)",
                    },
                },
                "additionalProperties": False,
            },
        },
    },
]


# ======================================================================
# Tool Execution
# ======================================================================

# Map tool names to handler functions
_TOOL_HANDLERS: dict[str, Any] = {}


def _register(name: str):
    """Decorator to register a tool handler."""
    def wrapper(func):
        _TOOL_HANDLERS[name] = func
        return func
    return wrapper


async def execute_tool(
    tool_name: str,
    arguments: dict[str, Any],
    conn,
    user_id: UUID,
) -> dict[str, Any]:
    """Execute a tool by name and return the result.

    Parameters
    ----------
    tool_name : str
        Name of the tool to execute (must be one of the four defined in
        ``TOOL_DEFINITIONS``).
    arguments : dict
        Arguments for the tool, parsed from the LLM's tool call.
    conn : Connection
        Database connection (from the ``get_conn`` dependency).
    user_id : UUID
        The authenticated user's ID (used as default ``user_id`` when the
        tool does not explicitly provide one).

    Returns
    -------
    dict
        Result data. Always includes a ``"result"`` key with a human-readable
        summary string, plus tool-specific keys.

    Raises
    ------
    ValueError
        If *tool_name* is unknown.
    """
    handler = _TOOL_HANDLERS.get(tool_name)
    if handler is None:
        raise ValueError(f"Unknown tool: {tool_name}")

    return await handler(arguments, conn, user_id)


# ── Individual tool handlers ────────────────────────────────────


@_register("render_natal_chart")
async def _execute_render_natal_chart(
    args: dict[str, Any],
    conn,
    user_id: UUID,
) -> dict[str, Any]:
    """Compute the natal chart for the given user and return structured data."""
    target_user_id = UUID(args["user_id"]) if args.get("user_id") else user_id

    # Fetch the user's birth profile (1:1 with user)
    profile = await conn.fetchrow(
        """
        SELECT id, user_id, birth_date, birth_time, latitude, longitude, time_zone, location_name
        FROM birth_profiles
        WHERE user_id = $1
        LIMIT 1
        """,
        target_user_id,
    )
    if profile is None:
        return {
            "result": "No birth profile found. The user needs to create a birth profile first with their date, time, and location of birth.",
            "error": "birth_profile_not_found",
        }

    # Parse birth datetime (SQLite stores date/time as text)
    dob_raw = profile["birth_date"]
    if isinstance(dob_raw, date) and not isinstance(dob_raw, datetime):
        dob = dob_raw
    else:
        dob = date.fromisoformat(str(dob_raw)[:10])

    tob_raw = profile["birth_time"]
    if tob_raw is None or tob_raw == "":
        tob = datetime.strptime("12:00:00", "%H:%M:%S").time()
    elif hasattr(tob_raw, "hour"):
        tob = tob_raw
    else:
        tstr = str(tob_raw)
        if len(tstr) == 5:
            tstr += ":00"
        tob = datetime.strptime(tstr[:8], "%H:%M:%S").time()

    dt_utc = datetime.combine(dob, tob)

    # Compute the chart
    try:
        chart_data = compute_chart(
            user_id=target_user_id,
            chart_type="natal",
            dt_utc=dt_utc,
            latitude=float(profile["latitude"]),
            longitude=float(profile["longitude"]),
            time_zone=profile["time_zone"],
            location_name=profile.get("location_name"),
        )
    except Exception as exc:
        return {
            "result": f"Failed to compute natal chart: {exc}",
            "error": "chart_computation_failed",
        }

    # Format bodies, aspects, houses for the response
    bodies = [
        {
            "body_key": b["body_key"],
            "sign": b["sign"],
            "sign_degree": str(b["sign_degree"]),
            "house": b["house"],
            "dignity": b.get("dignity"),
        }
        for b in chart_data["bodies"]
    ]

    aspects = [
        {
            "body_a": a["body_a_key"],
            "body_b": a["body_b_key"],
            "aspect": a["aspect_type"],
            "orb": str(a["orb"]),
        }
        for a in chart_data["aspects"]
    ]

    houses = [
        {
            "house_number": h["house_number"],
            "sign": h["sign"],
            "sign_degree": str(h["sign_degree"]),
        }
        for h in chart_data["houses"]
    ]

    return {
        "result": (
            f"Natal chart computed for {profile['time_zone']}. "
            f"{len(bodies)} bodies placed, {len(aspects)} aspects found."
        ),
        "chart_type": "natal",
        "chart_id": str(chart_data["chart"]["id"]),
        "bodies": bodies,
        "houses": houses,
        "aspects": aspects,
    }


@_register("render_transit_timeline")
async def _execute_render_transit_timeline(
    args: dict[str, Any],
    conn,
    user_id: UUID,
) -> dict[str, Any]:
    """Compute transits against a natal chart for a date range."""
    today = date.today()
    start_date_str = args.get("start_date") or today.isoformat()
    # Default end: +14 days when not specified (better for "this week/fortnight")
    if args.get("end_date"):
        end_date_str = args["end_date"]
    else:
        from datetime import timedelta

        end_date_str = (today + timedelta(days=14)).isoformat()

    try:
        start_date = date.fromisoformat(str(start_date_str)[:10])
        end_date = date.fromisoformat(str(end_date_str)[:10])
    except ValueError as exc:
        return {
            "result": f"Invalid date format: {exc}. Please use YYYY-MM-DD format.",
            "error": "invalid_date",
        }

    # Clamp absurd ranges that explode ephemeris work / tokens
    if (end_date - start_date).days > 90:
        from datetime import timedelta

        end_date = start_date + timedelta(days=90)

    if start_date > end_date:
        return {
            "result": "Start date must be before or equal to end date.",
            "error": "invalid_date_range",
        }

    # Resolve natal chart: explicit id, else user's most recent natal chart
    chart_row = None
    if args.get("chart_id"):
        chart_id = UUID(str(args["chart_id"]))
        chart_row = await conn.fetchrow(
            """
            SELECT id, user_id, latitude, longitude, time_zone, house_system
            FROM charts WHERE id = $1
            """,
            chart_id,
        )
    if chart_row is None:
        chart_row = await conn.fetchrow(
            """
            SELECT id, user_id, latitude, longitude, time_zone, house_system
            FROM charts
            WHERE user_id = $1 AND chart_type = 'natal'
            ORDER BY created_at DESC
            LIMIT 1
            """,
            user_id,
        )
    if chart_row is None:
        return {
            "result": "Natal chart not found. Compute a natal chart first.",
            "error": "chart_not_found",
        }
    chart_id = chart_row["id"] if not isinstance(chart_row["id"], UUID) else chart_row["id"]
    try:
        chart_id = UUID(str(chart_id))
    except Exception:
        pass

    # Fetch natal bodies
    bodies_rows = await conn.fetch(
        """
        SELECT body_key, longitude, sign, sign_degree, house
        FROM chart_bodies WHERE chart_id = $1
        """,
        chart_id,
    )
    if not bodies_rows:
        return {
            "result": "Natal chart exists but has no body data.",
            "error": "chart_data_missing",
        }

    # Fetch natal houses
    houses_rows = await conn.fetch(
        """
        SELECT house_number, cusps_longitude, sign, sign_degree
        FROM chart_houses WHERE chart_id = $1
        ORDER BY house_number
        """,
        chart_id,
    )

    # Compute transits
    calc = TransitCalculator()
    try:
        events = calc.compute_transits(
            natal_bodies=[dict(r) for r in bodies_rows],
            natal_houses=[dict(r) for r in houses_rows],
            start_date=start_date,
            end_date=end_date,
            latitude=float(chart_row["latitude"]),
            longitude=float(chart_row["longitude"]),
            time_zone=chart_row["time_zone"],
            house_system=chart_row.get("house_system", "P"),
        )
    except Exception as exc:
        return {
            "result": f"Failed to compute transits: {exc}",
            "error": "transit_computation_failed",
        }

    # Filter to significant events
    significant = TransitCalculator.get_significant_transits(events, max_results=30)
    significant_dicts = [dict(e) for e in significant]

    return {
        "result": (
            f"Found {len(events)} transit events ({len(significant)} significant) "
            f"from {start_date_str} to {end_date_str}."
        ),
        "transit_events": significant_dicts,
        "total_events": len(events),
        "start_date": start_date_str,
        "end_date": end_date_str,
        "chart_id": str(chart_id),
    }


@_register("render_synastry")
async def _execute_render_synastry(
    args: dict[str, Any],
    conn,
    user_id: UUID,
) -> dict[str, Any]:
    """Compute synastry (relationship compatibility) between two charts."""
    chart_a_id = UUID(args["chart_a_id"])
    chart_b_id = UUID(args["chart_b_id"])

    if chart_a_id == chart_b_id:
        return {
            "result": "Cannot compute synastry between the same chart. Please provide two different chart IDs.",
            "error": "same_chart",
        }

    # Fetch bodies for both charts
    bodies_a = await conn.fetch(
        """
        SELECT body_key, longitude, sign, sign_degree, house, speed
        FROM chart_bodies WHERE chart_id = $1
        """,
        chart_a_id,
    )
    bodies_b = await conn.fetch(
        """
        SELECT body_key, longitude, sign, sign_degree, house, speed
        FROM chart_bodies WHERE chart_id = $1
        """,
        chart_b_id,
    )

    if not bodies_a:
        return {
            "result": "Chart A (first chart) has no body data.",
            "error": "chart_a_data_missing",
        }
    if not bodies_b:
        return {
            "result": "Chart B (second chart) has no body data.",
            "error": "chart_b_data_missing",
        }

    # Fetch houses for overlay computation
    houses_a = await conn.fetch(
        """
        SELECT house_number, cusps_longitude
        FROM chart_houses WHERE chart_id = $1
        ORDER BY house_number
        """,
        chart_a_id,
    )
    houses_b = await conn.fetch(
        """
        SELECT house_number, cusps_longitude
        FROM chart_houses WHERE chart_id = $1
        ORDER BY house_number
        """,
        chart_b_id,
    )

    # Compute synastry
    try:
        synastry_data = compute_synastry(
            chart_a_bodies=[dict(r) for r in bodies_a],
            chart_b_bodies=[dict(r) for r in bodies_b],
            chart_a_houses=[dict(r) for r in houses_a] if houses_a else None,
            chart_b_houses=[dict(r) for r in houses_b] if houses_b else None,
        )
    except Exception as exc:
        return {
            "result": f"Failed to compute synastry: {exc}",
            "error": "synastry_computation_failed",
        }

    return {
        "result": (
            f"Synastry computed: {len(synastry_data['aspects'])} inter-chart aspects. "
            f"Overall compatibility score: {synastry_data['score_summary'].get('overall', 'N/A')}/10."
        ),
        "aspects": synastry_data["aspects"],
        "score_summary": synastry_data["score_summary"],
        "house_overlays_a_in_b": synastry_data["house_overlays_a_in_b"],
        "house_overlays_b_in_a": synastry_data["house_overlays_b_in_a"],
        "chart_a_id": str(chart_a_id),
        "chart_b_id": str(chart_b_id),
    }


@_register("render_life_phases")
async def _execute_render_life_phases(
    args: dict[str, Any],
    conn,
    user_id: UUID,
) -> dict[str, Any]:
    """Compute life phase milestones for a user from their birth data."""
    target_user_id = UUID(args["user_id"]) if args.get("user_id") else user_id

    # Fetch the user's birth profile
    profile = await conn.fetchrow(
        """
        SELECT id, user_id, birth_date, latitude, longitude, time_zone
        FROM birth_profiles
        WHERE user_id = $1
        LIMIT 1
        """,
        target_user_id,
    )
    if profile is None:
        return {
            "result": "No birth profile found. The user needs to create a birth profile first.",
            "error": "birth_profile_not_found",
        }

    # Try to get Saturn's natal longitude from the most recent natal chart
    saturn_longitude: float | None = None
    chart_row = await conn.fetchrow(
        """
        SELECT c.id
        FROM charts c
        WHERE c.user_id = $1 AND c.chart_type = 'natal'
        ORDER BY c.created_at DESC
        LIMIT 1
        """,
        target_user_id,
    )
    if chart_row:
        saturn_row = await conn.fetchrow(
            "SELECT longitude FROM chart_bodies WHERE chart_id = $1 AND body_key = 'saturn'",
            chart_row["id"],
        )
        if saturn_row:
            saturn_longitude = float(saturn_row["longitude"])

    birth_date_val = profile["birth_date"]
    if isinstance(birth_date_val, datetime):
        birth_date_val = birth_date_val.date()
    elif not isinstance(birth_date_val, date):
        birth_date_val = date.fromisoformat(str(birth_date_val)[:10])

    # Compute life phases
    try:
        phases = compute_life_phases(
            birth_date=birth_date_val,
            saturn_longitude=saturn_longitude,
            include_descriptions=True,
            include_dominant_transits=True,
        )
    except Exception as exc:
        return {
            "result": f"Failed to compute life phases: {exc}",
            "error": "life_phase_computation_failed",
        }

    return {
        "result": f"Found {len(phases)} life phases from birth date {birth_date_val}.",
        "phases": phases,
        "birth_date": str(birth_date_val),
        "saturn_longitude": saturn_longitude,
    }
