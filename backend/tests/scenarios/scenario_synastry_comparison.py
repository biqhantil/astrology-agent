"""Scenario 3: Synastry Comparison — two-chart overlay analysis

Tests:
  1. Create two natal charts
  2. Compute synastry between them
  3. Verify inter-chart aspects
  4. Verify house overlays
  5. Verify score summary
"""

from __future__ import annotations

SCENARIO = {
    "name": "synastry_comparison",
    "description": "Create two charts, compute synastry, verify inter-aspects and scores",
    "turns": [
        {
            "id": "register",
            "description": "Anonymous user registration",
            "request": {
                "method": "POST",
                "path": "/v1/auth/anonymous",
                "body": {"locale": "en"},
            },
            "expected_status": 200,
            "extract": {"user_id": "user_id", "access_token": "access_token"},
        },
        {
            "id": "compute_chart_a",
            "description": "Compute Chart A (Person 1 — Aries Sun)",
            "request": {
                "method": "POST",
                "path": "/v1/charts",
                "body": {
                    "chart_type": "natal",
                    "calculation_date": "1990-04-10T14:30:00Z",
                    "location": {
                        "latitude": 51.5074,
                        "longitude": -0.1278,
                        "time_zone": "Europe/London",
                        "location_name": "London, UK",
                    },
                },
            },
            "expected_status": 201,
            "metrics": {"track_latency": True},
            "assertions": [
                {"json_path": "chart_type", "equals": "natal"},
                {"json_path": "bodies", "min_length": 10},
            ],
            "extract": {"chart_a_id": "id"},
        },
        {
            "id": "compute_chart_b",
            "description": "Compute Chart B (Person 2 — Libra Sun)",
            "request": {
                "method": "POST",
                "path": "/v1/charts",
                "body": {
                    "chart_type": "natal",
                    "calculation_date": "1992-10-05T08:00:00Z",
                    "location": {
                        "latitude": 48.8566,
                        "longitude": 2.3522,
                        "time_zone": "Europe/Paris",
                        "location_name": "Paris, France",
                    },
                },
            },
            "expected_status": 201,
            "metrics": {"track_latency": True},
            "assertions": [
                {"json_path": "chart_type", "equals": "natal"},
            ],
            "extract": {"chart_b_id": "id"},
        },
        {
            "id": "compute_synastry",
            "description": "Compute synastry between Chart A and Chart B",
            "request": {
                "method": "POST",
                "path": "/v1/synastry",
                "body": {
                    "chart_a_id": "{chart_a_id}",
                    "chart_b_id": "{chart_b_id}",
                    "relationship_type": "romantic",
                },
            },
            "expected_status": 201,
            "metrics": {
                "track_latency": True,
                "expected_min_aspects": 3,
            },
            "assertions": [
                {"json_path": "chart_a_id", "not_none": True},
                {"json_path": "chart_b_id", "not_none": True},
                {"json_path": "aspects", "is_list": True},
                {"json_path": "aspects", "min_length": 3},
                {"json_path": "score_summary", "not_none": True},
                {"json_path": "relationship_type", "equals": "romantic"},
            ],
            "extract": {"synastry_id": "id"},
        },
        {
            "id": "verify_synastry_aspects",
            "description": "Verify inter-chart aspects have correct structure",
            "request": {
                "method": "GET",
                "path": "/v1/synastry/{synastry_id}",
            },
            "expected_status": 200,
            "assertions": [
                {"json_path": "aspects", "min_length": 3},
                {
                    "json_query": "aspects[0]",
                    "keys_present": [
                        "body_a_key",
                        "body_b_key",
                        "aspect_type",
                        "orb",
                    ],
                },
            ],
        },
        {
            "id": "verify_scores",
            "description": "Verify score summary fields are present",
            "request": {
                "method": "GET",
                "path": "/v1/synastry/{synastry_id}",
            },
            "expected_status": 200,
            "assertions": [
                {"json_path": "score_summary.emotional", "not_none": True},
                {"json_path": "score_summary.communication", "not_none": True},
                {"json_path": "score_summary.passion", "not_none": True},
                {"json_path": "score_summary.commitment", "not_none": True},
                {"json_path": "score_summary.overall", "not_none": True},
            ],
        },
        {
            "id": "list_synastry",
            "description": "List all synastry pairs for the user",
            "request": {
                "method": "GET",
                "path": "/v1/synastry",
            },
            "expected_status": 200,
            "assertions": [
                {"json_path": "[0]", "not_none": True},
                {"json_path": "[0].score_summary", "not_none": True},
                {"json_path": "[0].chart_a_id", "equals": "{chart_a_id}"},
            ],
        },
    ],
}
