"""U3 — Medium-complex: pt-BR vague → specific → pushback (4 turns)."""

SCENARIO = {
    "id": "u3_ptbr_recovery",
    "description": "pt-BR: vague chat → daily transit → demand specificity → follow-up",
    "setup": {
        "birth_profile": {
            "birth_date": "1992-11-03",
            "birth_time": "22:00:00",
            "time_zone": "America/Sao_Paulo",
            "latitude": -23.5505,
            "longitude": -46.6333,
            "location_name": "São Paulo, Brazil",
            "house_system": "P",
        },
        "natal_chart": {
            "chart_type": "natal",
            "calculation_date": "1992-11-04T01:00:00Z",
            "location": {
                "latitude": -23.5505,
                "longitude": -46.6333,
                "time_zone": "America/Sao_Paulo",
                "location_name": "São Paulo, Brazil",
            },
            "house_system": "P",
        },
    },
    "turns": [
        {
            "id": "greet",
            "description": "Casual opener",
            "user": "oi, tudo bem?",
            "expect": {"status": 201, "min_content_len": 10},
        },
        {
            "id": "vague",
            "description": "Vague stars ask",
            "user": "me fala um pouco das estrelas, o que você vê pra mim",
            "expect": {"status": 201, "min_content_len": 40},
        },
        {
            "id": "daily",
            "description": "Specific daily with transits",
            "user": (
                "Quero o prognóstico diário de hoje com trânsitos reais no meu mapa natal. "
                "Seja prático e cite planetas."
            ),
            "expect": {
                "status": 201,
                "min_content_len": 80,
                "require_astro_grounding": True,
            },
            "stop_on_fail": True,
        },
        {
            "id": "pushback",
            "description": "User demands less generic answer",
            "user": (
                "Isso ainda parece genérico. Usa os dados do meu mapa e cita "
                "pelo menos um planeta com signo ou casa, e um aspecto ou trânsito concreto."
            ),
            "expect": {
                "status": 201,
                "min_content_len": 60,
                "require_astro_grounding": True,
            },
        },
    ],
}
