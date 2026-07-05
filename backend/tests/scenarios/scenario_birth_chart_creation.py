"""Scenario 1: Birth Chart Creation + Interpretation

Tests the core flow:
  1. Register user (POST /v1/auth/anonymous)
  2. Create birth profile (PUT /v1/me/birth-profile)
  3. Compute natal chart (POST /v1/charts)
  4. Verify chart body positions and aspect detection
  5. Fetch chart summary (GET /v1/charts/{id}/summary)
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

SCENARIO = {
    "name": "birth_chart_creation",
    "description": "Register user, create birth profile, compute natal chart, verify bodies+aspects",
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
            "id": "get_me",
            "description": "Fetch current user profile",
            "request": {
                "method": "GET",
                "path": "/v1/me",
            },
            "expected_status": 200,
            "assertions": [
                {"json_path": "locale", "equals": "en"},
                {"json_path": "display_name", "is_none": True},
            ],
        },
        {
            "id": "create_birth_profile",
            "description": "Create birth profile (Einstein's data)",
            "request": {
                "method": "PUT",
                "path": "/v1/me/birth-profile",
                "body": {
                    "birth_date": "1879-03-14",
                    "birth_time": "11:30:00",
                    "time_zone": "Europe/Berlin",
                    "latitude": 48.3984,
                    "longitude": 9.9916,
                    "location_name": "Ulm, Germany",
                },
            },
            "expected_status": 200,
            "assertions": [
                {"json_path": "sun_sign", "equals": "pisces"},
                {"json_path": "has_unknown_time", "equals": False},
            ],
            "extract": {"birth_profile_id": "id"},
        },
        {
            "id": "compute_natal_chart",
            "description": "Compute natal chart from birth data",
            "request": {
                "method": "POST",
                "path": "/v1/charts",
                "body": {
                    "chart_type": "natal",
                    "calculation_date": "1879-03-14T10:30:00Z",
                    "location": {
                        "latitude": 48.3984,
                        "longitude": 9.9916,
                        "time_zone": "Europe/Berlin",
                        "location_name": "Ulm, Germany",
                    },
                },
            },
            "expected_status": 201,
            "metrics": {
                "track_latency": True,
            },
            "assertions": [
                {"json_path": "chart_type", "equals": "natal"},
                {"json_path": "bodies", "is_list": True},
                {"json_path": "houses", "is_list": True, "min_length": 12},
                {"json_path": "aspects", "is_list": True},
            ],
            "extract": {"chart_id": "id"},
        },
        {
            "id": "verify_sun_sign",
            "description": "Verify Sun is in Pisces",
            "request": {
                "method": "GET",
                "path": "/v1/charts/{chart_id}",
            },
            "expected_status": 200,
            "assertions": [
                {
                    "json_query": "bodies[?body_key=='sun'].sign | [0]",
                    "equals": "pisces",
                },
                {
                    "json_query": "bodies[?body_key=='sun'].sign_degree | [0]",
                    "gt": 20,
                },
            ],
        },
        {
            "id": "verify_moon_sign",
            "description": "Verify Moon is in Sagittarius",
            "request": {
                "method": "GET",
                "path": "/v1/charts/{chart_id}",
            },
            "expected_status": 200,
            "assertions": [
                {
                    "json_query": "bodies[?body_key=='moon'].sign | [0]",
                    "equals": "sagittarius",
                },
            ],
        },
        {
            "id": "verify_aspects",
            "description": "Verify aspects were detected",
            "request": {
                "method": "GET",
                "path": "/v1/charts/{chart_id}",
            },
            "expected_status": 200,
            "assertions": [
                {"json_path": "aspects", "min_length": 5},
            ],
            "metrics": {
                "expected_min_aspects": 5,
            },
        },
        {
            "id": "chart_summary",
            "description": "Fetch chart summary",
            "request": {
                "method": "GET",
                "path": "/v1/charts/{chart_id}/summary",
            },
            "expected_status": 200,
            "assertions": [
                {"json_path": "sun", "not_none": True},
                {"json_path": "moon", "not_none": True},
                {"json_path": "rising", "not_none": True},
                {"json_path": "key_aspects", "is_list": True},
            ],
        },
    ],
}
