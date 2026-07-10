"""U6 — Ceiling probe: longer thread + hard asks + recovery under load (7 turns).

Designed to find product/UX/cost ceilings beyond u5:
- multi-tool year window (expensive)
- error path (synastry without partner chart)
- memory after heavy context
- language switch mid-thread
- ultra-short follow-up after long answers
"""

SCENARIO = {
    "id": "u6_ceiling_probe",
    "description": "Ceiling: phase → year → bad synastry → memory → pt switch → practices → one-word edge",
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
            "description": "Life phase + Saturn return",
            "user": (
                "What major life phase am I in? Use life-phase tools and give "
                "Saturn return timing for my birth date."
            ),
            "expect": {
                "status": 201,
                "min_content_len": 80,
                "require_astro_grounding": True,
                "tools_any_of": ["render_life_phases"],
            },
            "stop_on_fail": True,
        },
        {
            "id": "year",
            "description": "12-month themes (known expensive path)",
            "user": (
                "Looking at the next 12 months, what are 3 transit seasons I should watch? "
                "Be specific with planets and houses."
            ),
            "expect": {
                "status": 201,
                "min_content_len": 100,
                "require_astro_grounding": True,
                "tools_any_of": ["render_transit_timeline"],
            },
            "stop_on_fail": True,
        },
        {
            "id": "synastry_fail",
            "description": "Ask for synastry without partner data — must recover gracefully",
            "user": (
                "Now compare my chart with my partner for compatibility. "
                "Just run the synastry tool."
            ),
            "expect": {
                "status": 201,
                "min_content_len": 40,
                # Should not crash; either no tool or tool error recovery in text
            },
        },
        {
            "id": "memory",
            "description": "Recall earlier phase under long context",
            "user": "Without tools: what life phase did you say I was in at the start?",
            "expect": {
                "status": 201,
                "min_content_len": 20,
                "tools_empty": True,
            },
        },
        {
            "id": "pt_switch",
            "description": "Mid-thread language switch to Portuguese",
            "user": (
                "Agora responde em português: resume em 5 linhas o que eu devo "
                "observar nos próximos 3 meses."
            ),
            "expect": {
                "status": 201,
                "min_content_len": 40,
                "assistant_contains_any": [
                    "você", "voce", "próxim", "proxim", "meses", "trâns",
                    "trans", "lua", "sol", "casa", "saturn",
                ],
            },
        },
        {
            "id": "practices",
            "description": "Concrete practices after heavy context",
            "user": "Back to English. Three tiny weekly practices. Max one short paragraph each.",
            "expect": {
                "status": 201,
                "min_content_len": 60,
                "tools_none_of": ["render_natal_chart"],
            },
        },
        {
            "id": "edge",
            "description": "One-word edge after long thread",
            "user": "love?",
            "expect": {
                "status": 201,
                "min_content_len": 30,
            },
        },
    ],
}
