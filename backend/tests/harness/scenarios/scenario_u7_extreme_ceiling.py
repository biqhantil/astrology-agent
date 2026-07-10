"""U7 — Extreme ceiling: multi-window year stack + dense multi-ask (stress tokens/latency)."""

SCENARIO = {
    "id": "u7_extreme_ceiling",
    "description": "Extreme: phase → 12mo → 90d detail → multi-part mega ask → memory → short",
    "setup": {
        "birth_profile": {
            "birth_date": "1988-09-12",
            "birth_time": "11:05:00",
            "time_zone": "America/Los_Angeles",
            "latitude": 34.0522,
            "longitude": -118.2437,
            "location_name": "Los Angeles, CA",
            "house_system": "P",
        },
        "natal_chart": {
            "chart_type": "natal",
            "calculation_date": "1988-09-12T18:05:00Z",
            "location": {
                "latitude": 34.0522,
                "longitude": -118.2437,
                "time_zone": "America/Los_Angeles",
                "location_name": "Los Angeles, CA",
            },
            "house_system": "P",
        },
    },
    "turns": [
        {
            "id": "phase",
            "user": "Life phase + Saturn return timing. Use tools.",
            "expect": {
                "status": 201,
                "min_content_len": 60,
                "tools_any_of": ["render_life_phases"],
            },
            "stop_on_fail": True,
        },
        {
            "id": "year",
            "user": (
                "Next 12 months: list every major outer-planet transit to my natal chart "
                "and group them into seasons. Use transit tools."
            ),
            "expect": {
                "status": 201,
                "min_content_len": 80,
                "tools_any_of": ["render_transit_timeline"],
            },
            "stop_on_fail": True,
        },
        {
            "id": "window90",
            "user": (
                "Now zoom into the next 90 days only. Top 5 exact hits with dates if possible."
            ),
            "expect": {
                "status": 201,
                "min_content_len": 60,
                "tools_any_of": ["render_transit_timeline"],
            },
        },
        {
            "id": "mega",
            "user": (
                "In one answer: (1) my current phase name, (2) the single hardest transit "
                "this season, (3) one career tip from natal MC/10th, (4) one love tip from Venus, "
                "(5) three weekly practices. Number the sections."
            ),
            "expect": {
                "status": 201,
                "min_content_len": 120,
                "require_astro_grounding": True,
            },
        },
        {
            "id": "memory",
            "user": "What was item (1) and item (2) in your last answer? One sentence each.",
            "expect": {
                "status": 201,
                "min_content_len": 20,
                "tools_empty": True,
            },
        },
        {
            "id": "short",
            "user": "ok thanks — one word for the vibe of this month?",
            "expect": {
                "status": 201,
                "min_content_len": 3,
            },
        },
    ],
}
