"""U1 — Short / simple: Diário-style daily forecast (2 turns)."""

_PROFILE = {
    "birth_date": "1990-06-15",
    "birth_time": "14:30:00",
    "time_zone": "America/New_York",
    "latitude": 40.7128,
    "longitude": -74.006,
    "location_name": "New York, NY",
    "house_system": "P",
}
_CHART = {
    "chart_type": "natal",
    "calculation_date": "1990-06-15T18:30:00Z",
    "location": {
        "latitude": 40.7128,
        "longitude": -74.006,
        "time_zone": "America/New_York",
        "location_name": "New York, NY",
    },
    "house_system": "P",
}

SCENARIO = {
    "id": "u1_quick_daily",
    "description": "Short: daily forecast then one practical follow-up",
    "setup": {"birth_profile": _PROFILE, "natal_chart": _CHART},
    "turns": [
        {
            "id": "daily",
            "description": "User opens Diário",
            "user": (
                "What do the stars say about today? Give me a daily forecast based on my chart."
            ),
            "expect": {
                "status": 201,
                "min_content_len": 100,
                "require_astro_grounding": True,
                "tools_any_of": ["render_transit_timeline", "render_natal_chart"],
            },
            "stop_on_fail": True,
        },
        {
            "id": "practical",
            "description": "One practical ask (should reuse prior transit context)",
            "user": "What is one concrete thing I should do or avoid today?",
            "expect": {
                "status": 201,
                "min_content_len": 40,
                # Prefer no recompute on a pure follow-up
                "tools_none_of": ["render_natal_chart"],
            },
        },
    ],
}
