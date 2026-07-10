"""U5 — Long/complex: life phases + timing + emotional follow-through (4 turns)."""

SCENARIO = {
    "id": "u5_life_phase_long",
    "description": "Life phase + Saturn return + emotional integration + next year",
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
            "id": "phase",
            "description": "Life phase question",
            "user": (
                "What major life phase am I in right now? Use your life-phase tools "
                "and explain Saturn return timing for my birth date."
            ),
            "expect": {
                "status": 201,
                "min_content_len": 100,
                "require_astro_grounding": True,
                "tools_any_of": ["render_life_phases", "render_natal_chart"],
            },
            "stop_on_fail": True,
        },
        {
            "id": "emotion",
            "description": "Emotional meaning",
            "user": (
                "How should I work with this phase emotionally? "
                "Connect it to my natal Moon or chart themes if you can."
            ),
            "expect": {
                "status": 201,
                "min_content_len": 60,
            },
        },
        {
            "id": "year",
            "description": "Year-ahead bridge",
            "user": (
                "Looking at the next 12 months within this life phase, what are 2-3 "
                "themes or transit seasons I should watch?"
            ),
            "expect": {
                "status": 201,
                "min_content_len": 80,
                "require_astro_grounding": True,
            },
        },
        {
            "id": "action",
            "description": "Actionable close",
            "user": "Give me three small weekly practices aligned with that guidance.",
            "expect": {
                "status": 201,
                "min_content_len": 50,
            },
        },
    ],
}
