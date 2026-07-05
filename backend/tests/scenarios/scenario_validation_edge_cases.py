"""Scenario 6: Validation & Edge Cases — error handling and boundary conditions

Tests:
  1. Invalid auth token → 401
  2. Missing required fields → 422
  3. Self-synastry → 422
  4. Unknown chart → 404
  5. Date range validation (transits start > end) → 422
  6. Invalid chart_type → 422
  7. Missing birth profile → 404
"""

from __future__ import annotations

SCENARIO = {
    "name": "validation_edge_cases",
    "description": "Test input validation, error handling, and boundary conditions across all endpoints",
    "turns": [
        {
            "id": "no_auth_health",
            "description": "Health endpoint should work without auth",
            "request": {
                "method": "GET",
                "path": "/v1/health",
            },
            "expected_status": 200,
            "assertions": [
                {"json_path": "status", "equals": "ok"},
            ],
        },
        {
            "id": "no_auth_me",
            "description": "GET /v1/me without auth should return 401",
            "request": {
                "method": "GET",
                "path": "/v1/me",
            },
            "expected_status": 401,
        },
        {
            "id": "invalid_token",
            "description": "Invalid JWT should return 401",
            "request": {
                "method": "GET",
                "path": "/v1/me",
            },
            "expected_status": 401,
            "custom_headers": {"Authorization": "Bearer invalid.jwt.token"},
        },
        {
            "id": "register_anon",
            "description": "Register anonymous user for subsequent tests",
            "request": {
                "method": "POST",
                "path": "/v1/auth/anonymous",
                "body": {"locale": "en"},
            },
            "expected_status": 200,
            "extract": {"user_id": "user_id", "access_token": "access_token"},
        },
        {
            "id": "missing_chart_type",
            "description": "POST /v1/charts without required chart_type → 422",
            "request": {
                "method": "POST",
                "path": "/v1/charts",
                "body": {
                    "calculation_date": "1990-06-15T12:00:00Z",
                    "location": {
                        "latitude": 40.7128,
                        "longitude": -74.0060,
                        "time_zone": "America/New_York",
                    },
                },
            },
            "expected_status": 422,
        },
        {
            "id": "invalid_chart_type",
            "description": "POST /v1/charts with invalid chart_type pattern → 422",
            "request": {
                "method": "POST",
                "path": "/v1/charts",
                "body": {
                    "chart_type": "invalid_type_here",
                    "calculation_date": "1990-06-15T12:00:00Z",
                    "location": {
                        "latitude": 40.7128,
                        "longitude": -74.0060,
                        "time_zone": "America/New_York",
                    },
                },
            },
            "expected_status": 422,
        },
        {
            "id": "missing_location",
            "description": "POST /v1/charts without location → 422",
            "request": {
                "method": "POST",
                "path": "/v1/charts",
                "body": {
                    "chart_type": "natal",
                    "calculation_date": "1990-06-15T12:00:00Z",
                },
            },
            "expected_status": 422,
        },
        {
            "id": "nonexistent_chart",
            "description": "GET /v1/charts/:id for unknown ID → 404",
            "request": {
                "method": "GET",
                "path": "/v1/charts/00000000-0000-0000-0000-000000000000",
            },
            "expected_status": 404,
        },
        {
            "id": "self_synastry",
            "description": "POST /v1/synastry with same chart twice → 422",
            "request": {
                "method": "POST",
                "path": "/v1/synastry",
                "body": {
                    "chart_a_id": "00000000-0000-0000-0000-000000000000",
                    "chart_b_id": "00000000-0000-0000-0000-000000000000",
                    "relationship_type": "romantic",
                },
            },
            "expected_status": 422,
        },
        {
            "id": "transit_date_range_invalid",
            "description": "POST transits with start_date > end_date → 422",
            "request": {
                "method": "POST",
                "path": "/v1/charts/00000000-0000-0000-0000-000000000000/transits",
                "body": {
                    "start_date": "2026-12-31",
                    "end_date": "2026-01-01",
                },
            },
            "expected_status": 422,
        },
        {
            "id": "life_phases_without_birth_profile",
            "description": "POST /v1/me/life-phases/recalculate without birth profile → 404",
            "request": {
                "method": "POST",
                "path": "/v1/me/life-phases/recalculate",
                "body": {},
            },
            "expected_status": 404,
            "assertions": [
                {"json_path": "detail", "contains": "birth profile"},
            ],
        },
        {
            "id": "get_life_phases_without_recalculation",
            "description": "GET /v1/me/life-phases without precomputing → 404",
            "request": {
                "method": "GET",
                "path": "/v1/me/life-phases",
            },
            "expected_status": 404,
        },
        {
            "id": "invalid_birth_profile_lat",
            "description": "PUT birth profile with invalid latitude → 422",
            "request": {
                "method": "PUT",
                "path": "/v1/me/birth-profile",
                "body": {
                    "birth_date": "1990-06-15",
                    "time_zone": "America/New_York",
                    "latitude": 100.0,
                    "longitude": 0.0,
                },
            },
            "expected_status": 422,
        },
    ],
}
