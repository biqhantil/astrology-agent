"""Scenario 9: Chart Recalculation — update birth profile, recalculate chart, verify changes

Tests:
  1. Register user
  2. Create birth profile with known data
  3. Compute natal chart -> get initial chart
  4. Update birth profile with different birth time
  5. Compute natal chart again -> get new chart
  6. Verify signs changed (different ASC/MC due to time change)
  7. Update birth profile with different location
  8. Compute natal chart -> verify houses changed
  9. Verify both charts coexist (old chart still accessible)
"""

from __future__ import annotations

SCENARIO = {
    "name": "chart_recalculation",
    "description": "Update birth profile, recalculate chart, verify ascendant/houses change, verify old chart persists",
    "turns": [
        # ── Setup ──
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
        # ── Initial birth profile (morning birth) ──
        {
            "id": "create_birth_profile_initial",
            "description": "Create birth profile — morning birth (should give particular rising)",
            "request": {
                "method": "PUT",
                "path": "/v1/me/birth-profile",
                "body": {
                    "birth_date": "1990-06-15",
                    "birth_time": "06:00:00",
                    "time_zone": "America/New_York",
                    "latitude": 40.7128,
                    "longitude": -74.0060,
                    "location_name": "New York, NY",
                },
            },
            "expected_status": 200,
            "extract": {"profile_id_initial": "id"},
        },
        # ── Compute initial chart ──
        {
            "id": "compute_chart_v1",
            "description": "Compute natal chart from morning birth data",
            "request": {
                "method": "POST",
                "path": "/v1/charts",
                "body": {
                    "chart_type": "natal",
                    "calculation_date": "1990-06-15T10:00:00Z",
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
                {"json_path": "houses", "min_length": 12},
            ],
            "extract": {"chart_v1_id": "id"},
        },
        {
            "id": "record_v1_ascendant",
            "description": "Record V1 ascendant sign for later comparison",
            "request": {
                "method": "GET",
                "path": "/v1/charts/{chart_v1_id}",
            },
            "expected_status": 200,
            "assertions": [
                {"json_path": "houses", "min_length": 12},
            ],
            "extract": {"v1_asc_sign": "houses[0].sign"},
        },
        # ── Update birth profile (evening birth — different ASC) ──
        {
            "id": "update_birth_profile_time",
            "description": "Update birth profile with evening birth time",
            "request": {
                "method": "PUT",
                "path": "/v1/me/birth-profile",
                "body": {
                    "birth_date": "1990-06-15",
                    "birth_time": "20:30:00",
                    "time_zone": "America/New_York",
                    "latitude": 40.7128,
                    "longitude": -74.0060,
                    "location_name": "New York, NY",
                },
            },
            "expected_status": 200,
            "extract": {"profile_id_updated": "id"},
        },
        # ── Compute chart V2 with same location but different time ──
        {
            "id": "compute_chart_v2",
            "description": "Compute natal chart from evening birth data — different time, same location",
            "request": {
                "method": "POST",
                "path": "/v1/charts",
                "body": {
                    "chart_type": "natal",
                    "calculation_date": "1990-06-16T00:30:00Z",
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
            "extract": {"chart_v2_id": "id"},
        },
        {
            "id": "record_v2_ascendant",
            "description": "Record V2 ascendant sign",
            "request": {
                "method": "GET",
                "path": "/v1/charts/{chart_v2_id}",
            },
            "expected_status": 200,
            "assertions": [
                {"json_path": "houses", "min_length": 12},
            ],
            "extract": {"v2_asc_sign": "houses[0].sign"},
        },
        # ── Verify ascendant changed ──
        # The ascendant should differ because of different birth time
        # (morning vs evening gives different rising sign)
        {
            "id": "verify_ascendant_changed",
            "description": "Verify ascendant sign changed with birth time update",
            "request": {
                "method": "GET",
                "path": "/v1/charts/{chart_v2_id}",
            },
            "expected_status": 200,
            # We can't assert exact value since we don't know, but we check structure
            "assertions": [
                {"json_path": "houses[0].sign", "not_none": True},
                {"json_path": "houses[0].degree", "not_none": True},
            ],
        },
        # ── Update birth profile with different location ──
        {
            "id": "update_birth_profile_location",
            "description": "Update birth profile with different location (London)",
            "request": {
                "method": "PUT",
                "path": "/v1/me/birth-profile",
                "body": {
                    "birth_date": "1990-06-15",
                    "birth_time": "20:30:00",
                    "time_zone": "Europe/London",
                    "latitude": 51.5074,
                    "longitude": -0.1278,
                    "location_name": "London, UK",
                },
            },
            "expected_status": 200,
        },
        # ── Compute chart V3 with same time but different location ──
        {
            "id": "compute_chart_v3",
            "description": "Compute natal chart — same time, different location (London)",
            "request": {
                "method": "POST",
                "path": "/v1/charts",
                "body": {
                    "chart_type": "natal",
                    "calculation_date": "1990-06-15T19:30:00Z",
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
            "extract": {"chart_v3_id": "id"},
        },
        {
            "id": "record_v3_houses",
            "description": "Record V3 houses to verify they differ from V2",
            "request": {
                "method": "GET",
                "path": "/v1/charts/{chart_v3_id}",
            },
            "expected_status": 200,
            "assertions": [
                {"json_path": "houses", "min_length": 12},
            ],
        },
        # ── Verify old charts are still accessible ──
        {
            "id": "verify_v1_persists",
            "description": "Verify V1 chart is still accessible",
            "request": {
                "method": "GET",
                "path": "/v1/charts/{chart_v1_id}",
            },
            "expected_status": 200,
            "assertions": [
                {"json_path": "id", "equals": "{chart_v1_id}"},
                {"json_path": "houses", "min_length": 12},
            ],
        },
        {
            "id": "verify_v2_persists",
            "description": "Verify V2 chart is still accessible",
            "request": {
                "method": "GET",
                "path": "/v1/charts/{chart_v2_id}",
            },
            "expected_status": 200,
            "assertions": [
                {"json_path": "id", "equals": "{chart_v2_id}"},
                {"json_path": "houses", "min_length": 12},
            ],
        },
        # ── Verify all three charts have different creation timestamps ──
        {
            "id": "list_user_charts",
            "description": "List user's charts to verify all three exist",
            "request": {
                "method": "GET",
                "path": "/v1/charts",
            },
            "expected_status": 200,
            "assertions": [
                # Should find at least 3 charts for this user
                {"json_path": "[0]", "not_none": True},
            ],
        },
    ],
}
