"""Scenario 5: Full Workflow — register → chart → transits → synastry → life phases

End-to-end scenario that exercises the complete user journey:
  1. Register anonymous user
  2. Create birth profile
  3. Compute natal chart
  4. Compute transits for current period
  5. Create a second chart (friend/partner)
  6. Compute synastry
  7. Recalculate and retrieve life phases
"""

from __future__ import annotations

SCENARIO = {
    "name": "full_workflow",
    "description": "End-to-end: register → birth profile → natal chart → transits → synastry → life phases",
    "turns": [
        # ── Setup ──
        {
            "id": "register_user_1",
            "description": "Register User 1 (anonymous)",
            "request": {
                "method": "POST",
                "path": "/v1/auth/anonymous",
                "body": {"locale": "en"},
            },
            "expected_status": 200,
            "extract": {
                "user_id_1": "user_id",
                "access_token": "access_token",
            },
        },
        {
            "id": "register_user_2",
            "description": "Register User 2 (as context user, will be used for second chart)",
            "request": {
                "method": "POST",
                "path": "/v1/auth/anonymous",
                "body": {"locale": "en"},
            },
            "expected_status": 200,
            "extract": {
                "user_id_2": "user_id",
                "access_token_2": "access_token",
            },
        },
        # ── Birth Profile + Natal Chart for User 1 ──
        {
            "id": "profile_user_1",
            "description": "Create birth profile for User 1 (1990, New York)",
            "request": {
                "method": "PUT",
                "path": "/v1/me/birth-profile",
                "body": {
                    "birth_date": "1990-06-15",
                    "birth_time": "14:30:00",
                    "time_zone": "America/New_York",
                    "latitude": 40.7128,
                    "longitude": -74.0060,
                    "location_name": "New York, NY",
                },
            },
            "expected_status": 200,
            "assertions": [
                {"json_path": "birth_date", "equals": "1990-06-15"},
                {"json_path": "sun_sign", "not_none": True},
            ],
            "extract": {"profile_id_1": "id"},
        },
        {
            "id": "chart_user_1",
            "description": "Compute natal chart for User 1",
            "request": {
                "method": "POST",
                "path": "/v1/charts",
                "body": {
                    "chart_type": "natal",
                    "calculation_date": "1990-06-15T18:30:00Z",
                    "location": {
                        "latitude": 40.7128,
                        "longitude": -74.0060,
                        "time_zone": "America/New_York",
                        "location_name": "New York, NY",
                    },
                },
            },
            "expected_status": 201,
            "metrics": {"track_latency": True},
            "assertions": [
                {"json_path": "chart_type", "equals": "natal"},
                {"json_path": "bodies", "min_length": 10},
            ],
            "extract": {"chart_id_1": "id"},
        },
        # ── Chart for User 2 (partner) ──
        {
            "id": "chart_user_2",
            "description": "Compute chart for User 2 (partner, 1992, Paris)",
            "api_key_ref": "access_token_2",
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
            "extract": {"chart_id_2": "id"},
        },
        # ── Transits ──
        {
            "id": "compute_transits",
            "description": "Compute transits for User 1's chart (July–September 2026)",
            "request": {
                "method": "POST",
                "path": "/v1/charts/{chart_id_1}/transits",
                "body": {
                    "start_date": "2026-07-01",
                    "end_date": "2026-09-30",
                },
            },
            "expected_status": 201,
            "metrics": {"track_latency": True},
            "assertions": [
                {"json_path": "transit_events", "min_length": 5},
                {"json_path": "date_from", "equals": "2026-07-01"},
                {"json_path": "date_to", "equals": "2026-09-30"},
            ],
            "extract": {"snapshot_id": "id"},
        },
        # ── Synastry ──
        {
            "id": "compute_synastry",
            "description": "Compute synastry between User 1 and User 2 charts",
            "request": {
                "method": "POST",
                "path": "/v1/synastry",
                "body": {
                    "chart_a_id": "{chart_id_1}",
                    "chart_b_id": "{chart_id_2}",
                    "relationship_type": "romantic",
                },
            },
            "expected_status": 201,
            "metrics": {"track_latency": True},
            "assertions": [
                {"json_path": "aspects", "min_length": 3},
                {"json_path": "score_summary", "not_none": True},
                {"json_path": "score_summary.overall", "not_none": True},
            ],
            "extract": {"synastry_id": "id"},
        },
        # ── Life Phases ──
        {
            "id": "recalculate_phases",
            "description": "Compute life phases for User 1 using natal chart",
            "request": {
                "method": "POST",
                "path": "/v1/me/life-phases/recalculate",
                "body": {
                    "chart_id": "{chart_id_1}",
                },
            },
            "expected_status": 201,
            "metrics": {"track_latency": True},
            "assertions": [
                {"json_path": "phases", "min_length": 7},
                {"json_path": "phases[0].phase_key", "equals": "foundation"},
                {"json_path": "phases[-1].phase_key", "equals": "legacy"},
            ],
        },
        {
            "id": "get_current_phase",
            "description": "Verify current phase is detected",
            "request": {
                "method": "GET",
                "path": "/v1/me/life-phases/current",
            },
            "expected_status": 200,
            "assertions": [
                {"json_path": "current_phase", "not_none": True},
            ],
        },
        # ── Cross-verify: chart detail ──
        {
            "id": "verify_chart_1_detail",
            "description": "Verify User 1's full chart details",
            "request": {
                "method": "GET",
                "path": "/v1/charts/{chart_id_1}",
            },
            "expected_status": 200,
            "assertions": [
                {"json_path": "id", "equals": "{chart_id_1}"},
                {"json_path": "bodies", "min_length": 10},
                {"json_path": "houses", "min_length": 12},
                {"json_path": "aspects", "min_length": 5},
            ],
            "metrics": {
                "verify_aspect_accuracy": True,
            },
        },
        # ── Cross-verify: chart-scoped life phases ──
        {
            "id": "verify_chart_life_phases",
            "description": "Verify chart-scoped life phases match",
            "request": {
                "method": "GET",
                "path": "/v1/charts/{chart_id_1}/life-phases",
            },
            "expected_status": 200,
            "assertions": [
                {"json_path": "chart_id", "equals": "{chart_id_1}"},
                {"json_path": "phases", "min_length": 7},
                {"json_path": "phases[0].start_year", "equals": 1990},
            ],
        },
    ],
}
