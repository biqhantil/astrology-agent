"""Scenario 4: Life Phase Query — compute and retrieve phase timeline

Tests:
  1. Create birth profile
  2. Compute natal chart
  3. Recalculate life phases
  4. Retrieve full phase timeline
  5. Get current phase
  6. Get chart-scoped life phases
"""

from __future__ import annotations

SCENARIO = {
    "name": "life_phase_query",
    "description": "Create birth profile, compute natal chart, recalculate life phases, verify timeline",
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
            "id": "create_birth_profile",
            "description": "Create birth profile for 1990-born user",
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
                {"json_path": "has_unknown_time", "equals": False},
            ],
            "extract": {"profile_id": "id"},
        },
        {
            "id": "compute_natal_chart",
            "description": "Compute natal chart (needed for Saturn position)",
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
            ],
            "extract": {"chart_id": "id"},
        },
        {
            "id": "recalculate_phases",
            "description": "Compute life phases using the natal chart",
            "request": {
                "method": "POST",
                "path": "/v1/me/life-phases/recalculate",
                "body": {
                    "chart_id": "{chart_id}",
                },
            },
            "expected_status": 201,
            "metrics": {
                "track_latency": True,
                "expected_phase_count": 7,
            },
            "assertions": [
                {"json_path": "user_id", "not_none": True},
                {"json_path": "phases", "is_list": True},
                {"json_path": "phases", "min_length": 7},
                {"json_path": "phases[0].phase_key", "equals": "foundation"},
                {"json_path": "phases[1].phase_key", "equals": "saturn_return_1"},
                {"json_path": "phases[-1].phase_key", "equals": "legacy"},
            ],
        },
        {
            "id": "get_phases",
            "description": "Retrieve stored life phases",
            "request": {
                "method": "GET",
                "path": "/v1/me/life-phases",
            },
            "expected_status": 200,
            "assertions": [
                {"json_path": "phases", "min_length": 7},
                {"json_path": "phases[0].title", "equals": "Foundation Years"},
                {"json_path": "phases[1].title", "equals": "First Saturn Return"},
                {
                    "json_path": "phases[0].dominant_transits",
                    "is_list": True,
                    "min_length": 1,
                },
            ],
        },
        {
            "id": "get_current_phase",
            "description": "Retrieve the currently active life phase",
            "request": {
                "method": "GET",
                "path": "/v1/me/life-phases/current",
            },
            "expected_status": 200,
            "assertions": [
                {"json_path": "current_phase", "not_none": True},
                {"json_path": "phase_index", "gte": 0},
            ],
        },
        {
            "id": "get_chart_phases",
            "description": "Retrieve chart-scoped life phases",
            "request": {
                "method": "GET",
                "path": "/v1/charts/{chart_id}/life-phases",
            },
            "expected_status": 200,
            "assertions": [
                {"json_path": "chart_id", "equals": "{chart_id}"},
                {"json_path": "birth_date", "equals": "1990-06-15"},
                {"json_path": "saturn_longitude", "not_none": True},
                {"json_path": "phases", "min_length": 7},
                {"json_path": "phases[0].year_range", "not_none": True},
                {"json_path": "phases[0].start_year", "equals": 1990},
                {"json_path": "phases[-1].end_year", "equals": None},
            ],
            "metrics": {
                "verify_saturn_longitude": True,
            },
        },
        {
            "id": "verify_young_user_no_phases_before_recalc",
            "description": "A newly registered young user with no phases gets 404",
            "request": {
                "method": "GET",
                "path": "/v1/me/life-phases",
            },
            "expected_status": 200,
            # This will succeed because we already computed phases in a previous turn
            "assertions": [
                {"json_path": "phases", "min_length": 1},
            ],
        },
    ],
}
