"""U2 — Medium: natal exploration with multi-turn focus (3 turns)."""

SCENARIO = {
    "id": "u2_natal_deep",
    "description": "Medium: natal overview → Moon deep-dive → career house",
    "setup": {
        "birth_profile": {
            "birth_date": "1985-03-21",
            "birth_time": "08:15:00",
            "time_zone": "Europe/London",
            "latitude": 51.5074,
            "longitude": -0.1278,
            "location_name": "London, UK",
            "house_system": "P",
        },
        "natal_chart": {
            "chart_type": "natal",
            "calculation_date": "1985-03-21T08:15:00Z",
            "location": {
                "latitude": 51.5074,
                "longitude": -0.1278,
                "time_zone": "Europe/London",
                "location_name": "London, UK",
            },
            "house_system": "P",
        },
    },
    "turns": [
        {
            "id": "overview",
            "description": "Full natal themes",
            "user": (
                "Show me my natal chart and explain the main placements and life themes. "
                "Use tools if helpful."
            ),
            "expect": {
                "status": 201,
                "min_content_len": 120,
                "require_astro_grounding": True,
            },
            "stop_on_fail": True,
        },
        {
            "id": "moon",
            "description": "Deepen Moon",
            "user": (
                "Focus on my Moon: sign, house, and key aspects. "
                "How does it color my emotional life day to day?"
            ),
            "expect": {
                "status": 201,
                "min_content_len": 80,
                "assistant_contains_any": ["moon", "lua", "emotional", "emoc"],
            },
        },
        {
            "id": "career",
            "description": "Career angle",
            "user": (
                "What does my chart say about work and vocation? "
                "Mention MC, 10th house, or relevant planets."
            ),
            "expect": {
                "status": 201,
                "min_content_len": 60,
                "require_astro_grounding": True,
            },
        },
    ],
}
