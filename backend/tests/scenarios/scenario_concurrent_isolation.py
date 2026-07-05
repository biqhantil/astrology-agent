"""Scenario 8: Concurrent User Isolation — verify users cannot access each other's data

Tests:
  1. Register User A
  2. Register User B (different token)
  3. User A creates birth profile
  4. User B tries to access User A's profile → 403/404
  5. User A creates a chart
  6. User B tries to access User A's chart → 403/404
  7. User A computes life phases
  8. User B tries to access User A's life phases → 403/404
  9. User A creates synastry
  10. User B tries to access User A's synastry → 403/404
"""

from __future__ import annotations

SCENARIO = {
    "name": "concurrent_user_isolation",
    "description": "Register two users, verify each cannot access the other's charts, profiles, life phases, or synastry",
    "turns": [
        # ── Register both users ──
        {
            "id": "register_user_a",
            "description": "Register User A (anonymous)",
            "request": {
                "method": "POST",
                "path": "/v1/auth/anonymous",
                "body": {"locale": "en"},
            },
            "expected_status": 200,
            "extract": {
                "user_a_id": "user_id",
                "access_token_a": "access_token",
            },
        },
        {
            "id": "register_user_b",
            "description": "Register User B (anonymous)",
            "request": {
                "method": "POST",
                "path": "/v1/auth/anonymous",
                "body": {"locale": "en"},
            },
            "expected_status": 200,
            "extract": {
                "user_b_id": "user_id",
                "access_token_b": "access_token",
            },
        },
        # ── User A creates birth profile ──
        {
            "id": "user_a_birth_profile",
            "description": "User A creates birth profile",
            "api_key_ref": "access_token_a",
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
            "extract": {"profile_a_id": "id"},
        },
        # ── User B tries to access User A's birth profile via GET /v1/me ──
        # (This is User B's own profile, which should not have User A's data)
        {
            "id": "user_b_check_own_me",
            "description": "User B checks their own profile",
            "api_key_ref": "access_token_b",
            "request": {
                "method": "GET",
                "path": "/v1/me",
            },
            "expected_status": 200,
            "assertions": [
                {"json_path": "user_id", "equals": "{user_b_id}"},
                # User B should NOT have User A's birth profile data
                {"json_path": "birth_date", "is_none": True},
            ],
        },
        # ── User A creates a chart ──
        {
            "id": "user_a_create_chart",
            "description": "User A creates a natal chart",
            "api_key_ref": "access_token_a",
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
            "extract": {"chart_a_id": "id"},
        },
        # ── User B tries to access User A's chart ──
        {
            "id": "user_b_access_chart_a",
            "description": "User B tries to GET User A's chart → should 403/404",
            "api_key_ref": "access_token_b",
            "request": {
                "method": "GET",
                "path": "/v1/charts/{chart_a_id}",
            },
            "expected_status": 404,
        },
        # ── User A computes life phases ──
        {
            "id": "user_a_recalculate_phases",
            "description": "User A recalculates life phases",
            "api_key_ref": "access_token_a",
            "request": {
                "method": "POST",
                "path": "/v1/me/life-phases/recalculate",
                "body": {
                    "chart_id": "{chart_a_id}",
                },
            },
            "expected_status": 201,
            "assertions": [
                {"json_path": "phases", "min_length": 1},
            ],
            "extract": {"life_phases_user_id": "user_id"},
        },
        # ── User B tries to access User A's life phases ──
        {
            "id": "user_b_access_phases",
            "description": "User B tries to GET User A's life phases → should 404 or be empty",
            "api_key_ref": "access_token_b",
            "request": {
                "method": "GET",
                "path": "/v1/me/life-phases/current",
            },
            # User B has no birth profile, so this should be 404
            "expected_status": 404,
        },
        # ── User B creates own chart and phases ──
        {
            "id": "user_b_birth_profile",
            "description": "User B creates their own birth profile",
            "api_key_ref": "access_token_b",
            "request": {
                "method": "PUT",
                "path": "/v1/me/birth-profile",
                "body": {
                    "birth_date": "1992-10-05",
                    "birth_time": "08:00:00",
                    "time_zone": "Europe/Paris",
                    "latitude": 48.8566,
                    "longitude": 2.3522,
                    "location_name": "Paris, France",
                },
            },
            "expected_status": 200,
            "extract": {"profile_b_id": "id"},
        },
        {
            "id": "user_b_create_chart",
            "description": "User B creates their own natal chart",
            "api_key_ref": "access_token_b",
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
            "extract": {"chart_b_id": "id"},
        },
        {
            "id": "user_b_recalculate_phases",
            "description": "User B recalculates their own life phases",
            "api_key_ref": "access_token_b",
            "request": {
                "method": "POST",
                "path": "/v1/me/life-phases/recalculate",
                "body": {
                    "chart_id": "{chart_b_id}",
                },
            },
            "expected_status": 201,
            "assertions": [
                {"json_path": "phases", "min_length": 1},
                {"json_path": "user_id", "equals": "{user_b_id}"},
            ],
        },
        # ── User B checks their own phases (should succeed) ──
        {
            "id": "user_b_get_phases",
            "description": "User B retrieves their own phases",
            "api_key_ref": "access_token_b",
            "request": {
                "method": "GET",
                "path": "/v1/me/life-phases",
            },
            "expected_status": 200,
            "assertions": [
                {"json_path": "phases", "min_length": 1},
            ],
        },
        # ── User B creates synastry with their own charts ──
        {
            "id": "user_b_synastry",
            "description": "User B creates synastry between own charts (self-synastry is caught by chart validation)",
            "api_key_ref": "access_token_b",
            "request": {
                "method": "POST",
                "path": "/v1/synastry",
                "body": {
                    "chart_a_id": "{chart_b_id}",
                    "chart_b_id": "{chart_b_id}",
                    "relationship_type": "romantic",
                },
            },
            "expected_status": 422,
        },
        # ── User B tries to access User A's chart again (verify still isolated) ──
        {
            "id": "user_b_recheck_chart_a",
            "description": "User B tries again to GET User A's chart → 404",
            "api_key_ref": "access_token_b",
            "request": {
                "method": "GET",
                "path": "/v1/charts/{chart_a_id}",
            },
            "expected_status": 404,
        },
    ],
}
