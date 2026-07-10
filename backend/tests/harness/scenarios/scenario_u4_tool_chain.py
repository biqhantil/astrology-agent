"""U4 — Complex: multi-tool chain across turns + synthesis + memory (5 turns)."""

SCENARIO = {
    "id": "u4_tool_chain",
    "description": "Complex: natal tool → transits tool → synthesize → avoid → memory",
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
            "id": "natal_tool",
            "description": "Natal big three from injected chart context (no recompute needed)",
            "user": (
                "Using my natal chart data, summarize Sun, Moon, and Rising "
                "with sign and house for each."
            ),
            "expect": {
                "status": 201,
                "min_content_len": 80,
                "require_astro_grounding": True,
                "assistant_contains_any": ["sun", "moon", "rising", "asc", "sol", "lua"],
            },
            "stop_on_fail": True,
        },
        {
            "id": "transits",
            "description": "Transit window",
            "user": (
                "Now compute current transits for the next 14 days against my natal chart. "
                "List the top 3 events with the transiting planet and natal point."
            ),
            "expect": {
                "status": 201,
                "min_content_len": 80,
                "require_astro_grounding": True,
                "tools_any_of": ["render_transit_timeline"],
            },
            "stop_on_fail": True,
        },
        {
            "id": "synthesize",
            "description": "Cross-source synthesis",
            "user": (
                "Putting natal + transits together: what is the one practical theme "
                "for this fortnight, and what should I avoid?"
            ),
            "expect": {
                "status": 201,
                "min_content_len": 60,
            },
        },
        {
            "id": "memory",
            "description": "Conversation memory check",
            "user": (
                "Without recomputing, remind me what you said my Sun and Moon were "
                "in the first answer."
            ),
            "expect": {
                "status": 201,
                "min_content_len": 30,
                "assistant_contains_any": ["sun", "moon", "virgo", "sol", "lua"],
            },
        },
        {
            "id": "edge",
            "description": "Ambiguous ask after rich context",
            "user": "and love?",
            "expect": {
                "status": 201,
                "min_content_len": 40,
            },
        },
    ],
}
