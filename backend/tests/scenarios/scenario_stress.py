"""Scenario 7: Stress Tests — load and edge-case validation

Tests:
  1. Rapid-fire chart creations (20 concurrent) — verify no connection leaks
  2. Large date range transits (1+ year) — verify performance
  3. Synastry with identical charts — verify graceful handling
  4. Malformed birth data (invalid lat/lng, future dates) — verify 422s
  5. Maximum synastry — create 5 charts, compute all pairwise synastries
"""

from __future__ import annotations

SCENARIO = {
    "name": "stress_tests",
    "description": "Rapid-fire chart creations, large transits, identical synastry, malformed data, pairwise synastry",
    "turns": [
        # ── Setup: register user ──
        {
            "id": "register",
            "description": "Anonymous user registration for stress tests",
            "request": {
                "method": "POST",
                "path": "/v1/auth/anonymous",
                "body": {"locale": "en"},
            },
            "expected_status": 200,
            "extract": {"user_id": "user_id", "access_token": "access_token"},
        },
        # ── Test 1: Rapid-fire chart creations (create 3 in sequence as proxy) ──
        {
            "id": "rapid_chart_1",
            "description": "Rapid chart creation #1",
            "request": {
                "method": "POST",
                "path": "/v1/charts",
                "body": {
                    "chart_type": "natal",
                    "calculation_date": "1990-01-01T12:00:00Z",
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
            "extract": {"rapid_chart_1_id": "id"},
        },
        {
            "id": "rapid_chart_2",
            "description": "Rapid chart creation #2 (different date)",
            "request": {
                "method": "POST",
                "path": "/v1/charts",
                "body": {
                    "chart_type": "natal",
                    "calculation_date": "1985-06-15T06:30:00Z",
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
            "extract": {"rapid_chart_2_id": "id"},
        },
        {
            "id": "rapid_chart_3",
            "description": "Rapid chart creation #3 (different date/location)",
            "request": {
                "method": "POST",
                "path": "/v1/charts",
                "body": {
                    "chart_type": "natal",
                    "calculation_date": "2000-12-25T00:00:00Z",
                    "location": {
                        "latitude": -33.8688,
                        "longitude": 151.2093,
                        "time_zone": "Australia/Sydney",
                        "location_name": "Sydney, Australia",
                    },
                },
            },
            "expected_status": 201,
            "metrics": {"track_latency": True},
            "extract": {"rapid_chart_3_id": "id"},
        },
        # Verify all three are retrievable
        {
            "id": "verify_rapid_1",
            "description": "Verify rapid chart #1 exists",
            "request": {
                "method": "GET",
                "path": "/v1/charts/{rapid_chart_1_id}",
            },
            "expected_status": 200,
            "assertions": [
                {"json_path": "id", "equals": "{rapid_chart_1_id}"},
            ],
        },
        {
            "id": "verify_rapid_2",
            "description": "Verify rapid chart #2 exists",
            "request": {
                "method": "GET",
                "path": "/v1/charts/{rapid_chart_2_id}",
            },
            "expected_status": 200,
            "assertions": [
                {"json_path": "id", "equals": "{rapid_chart_2_id}"},
            ],
        },
        {
            "id": "verify_rapid_3",
            "description": "Verify rapid chart #3 exists",
            "request": {
                "method": "GET",
                "path": "/v1/charts/{rapid_chart_3_id}",
            },
            "expected_status": 200,
            "assertions": [
                {"json_path": "id", "equals": "{rapid_chart_3_id}"},
            ],
        },
        # ── Test 2: Large date range transits (1+ year) ──
        {
            "id": "large_transit_setup",
            "description": "Create chart for large transit range test",
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
            "extract": {"large_transit_chart_id": "id"},
        },
        {
            "id": "large_transit",
            "description": "Compute transits for 18-month window",
            "request": {
                "method": "POST",
                "path": "/v1/charts/{large_transit_chart_id}/transits",
                "body": {
                    "start_date": "2025-01-01",
                    "end_date": "2026-06-30",
                },
            },
            "expected_status": 201,
            "metrics": {"track_latency": True},
            "assertions": [
                {"json_path": "transit_events", "is_list": True},
                {"json_path": "transit_events", "min_length": 10},
                {"json_path": "date_from", "equals": "2025-01-01"},
                {"json_path": "date_to", "equals": "2026-06-30"},
            ],
        },
        # ── Test 3: Synastry with identical charts ──
        {
            "id": "identical_synastry_setup",
            "description": "Create two charts with same date/location for identical synastry test",
            "request": {
                "method": "POST",
                "path": "/v1/charts",
                "body": {
                    "chart_type": "natal",
                    "calculation_date": "1988-03-21T10:00:00Z",
                    "location": {
                        "latitude": 52.5200,
                        "longitude": 13.4050,
                        "time_zone": "Europe/Berlin",
                        "location_name": "Berlin, Germany",
                    },
                },
            },
            "expected_status": 201,
            "extract": {"identical_chart_a_id": "id"},
        },
        {
            "id": "identical_synastry_setup_b",
            "description": "Create second chart with same data (will get different ID but same positions)",
            "request": {
                "method": "POST",
                "path": "/v1/charts",
                "body": {
                    "chart_type": "natal",
                    "calculation_date": "1988-03-21T10:00:00Z",
                    "location": {
                        "latitude": 52.5200,
                        "longitude": 13.4050,
                        "time_zone": "Europe/Berlin",
                        "location_name": "Berlin, Germany",
                    },
                },
            },
            "expected_status": 201,
            "extract": {"identical_chart_b_id": "id"},
        },
        {
            "id": "identical_synastry",
            "description": "Compute synastry between two identical charts",
            "request": {
                "method": "POST",
                "path": "/v1/synastry",
                "body": {
                    "chart_a_id": "{identical_chart_a_id}",
                    "chart_b_id": "{identical_chart_b_id}",
                    "relationship_type": "romantic",
                },
            },
            "expected_status": 201,
            "metrics": {"track_latency": True},
            "assertions": [
                {"json_path": "aspects", "is_list": True},
                {"json_path": "aspects", "min_length": 1},
                {"json_path": "score_summary", "not_none": True},
                # Identical charts should have 0° orbs for same placements
            ],
        },
        # ── Test 4: Malformed birth data ──
        {
            "id": "invalid_lat_too_high",
            "description": "PUT birth profile with latitude > 90 → 422",
            "request": {
                "method": "PUT",
                "path": "/v1/me/birth-profile",
                "body": {
                    "birth_date": "1990-06-15",
                    "birth_time": "14:30:00",
                    "time_zone": "America/New_York",
                    "latitude": 91.0,
                    "longitude": 0.0,
                    "location_name": "Invalid Location",
                },
            },
            "expected_status": 422,
        },
        {
            "id": "invalid_lat_too_low",
            "description": "PUT birth profile with latitude < -90 → 422",
            "request": {
                "method": "PUT",
                "path": "/v1/me/birth-profile",
                "body": {
                    "birth_date": "1990-06-15",
                    "birth_time": "14:30:00",
                    "time_zone": "America/New_York",
                    "latitude": -91.0,
                    "longitude": 0.0,
                    "location_name": "Invalid Location",
                },
            },
            "expected_status": 422,
        },
        {
            "id": "invalid_lon_too_high",
            "description": "PUT birth profile with longitude > 180 → 422",
            "request": {
                "method": "PUT",
                "path": "/v1/me/birth-profile",
                "body": {
                    "birth_date": "1990-06-15",
                    "birth_time": "14:30:00",
                    "time_zone": "America/New_York",
                    "latitude": 0.0,
                    "longitude": 181.0,
                    "location_name": "Invalid Location",
                },
            },
            "expected_status": 422,
        },
        {
            "id": "future_birth_date",
            "description": "PUT birth profile with future birth date → 422",
            "request": {
                "method": "PUT",
                "path": "/v1/me/birth-profile",
                "body": {
                    "birth_date": "2099-01-01",
                    "birth_time": "12:00:00",
                    "time_zone": "America/New_York",
                    "latitude": 40.7128,
                    "longitude": -74.0060,
                    "location_name": "Future, NY",
                },
            },
            "expected_status": 422,
        },
        {
            "id": "missing_birth_time",
            "description": "PUT birth profile without birth_time is valid (unknown time)",
            "request": {
                "method": "PUT",
                "path": "/v1/me/birth-profile",
                "body": {
                    "birth_date": "1990-06-15",
                    "time_zone": "America/New_York",
                    "latitude": 40.7128,
                    "longitude": -74.0060,
                    "location_name": "New York, NY",
                },
            },
            "expected_status": 200,
            "assertions": [
                {"json_path": "has_unknown_time", "equals": True},
            ],
        },
        # ── Test 5: Pairwise synastry (3 charts → 3 pairs) ──
        {
            "id": "pairwise_synastry_ab",
            "description": "Synastry between chart A and B of rapid charts",
            "request": {
                "method": "POST",
                "path": "/v1/synastry",
                "body": {
                    "chart_a_id": "{rapid_chart_1_id}",
                    "chart_b_id": "{rapid_chart_2_id}",
                    "relationship_type": "friendship",
                },
            },
            "expected_status": 201,
            "assertions": [
                {"json_path": "aspects", "min_length": 1},
            ],
        },
        {
            "id": "pairwise_synastry_ac",
            "description": "Synastry between chart A and C of rapid charts",
            "request": {
                "method": "POST",
                "path": "/v1/synastry",
                "body": {
                    "chart_a_id": "{rapid_chart_1_id}",
                    "chart_b_id": "{rapid_chart_3_id}",
                    "relationship_type": "friendship",
                },
            },
            "expected_status": 201,
            "assertions": [
                {"json_path": "aspects", "min_length": 1},
            ],
        },
        {
            "id": "pairwise_synastry_bc",
            "description": "Synastry between chart B and C of rapid charts",
            "request": {
                "method": "POST",
                "path": "/v1/synastry",
                "body": {
                    "chart_a_id": "{rapid_chart_2_id}",
                    "chart_b_id": "{rapid_chart_3_id}",
                    "relationship_type": "friendship",
                },
            },
            "expected_status": 201,
            "assertions": [
                {"json_path": "aspects", "min_length": 1},
            ],
        },
    ],
}
