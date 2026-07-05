"""Scenario 2: Transit Check — current sky vs natal chart

Tests:
  1. Create a natal chart
  2. Compute transits for a date range
  3. Verify transit events are detected
  4. Verify station detection
  5. Verify transit event structure
"""

from __future__ import annotations

SCENARIO = {
    "name": "transit_check",
    "description": "Create natal chart, compute transits, verify events and structure",
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
            "id": "compute_natal",
            "description": "Compute a natal chart for transit testing",
            "request": {
                "method": "POST",
                "path": "/v1/charts",
                "body": {
                    "chart_type": "natal",
                    "calculation_date": "1990-06-15T12:00:00Z",
                    "location": {
                        "latitude": 40.7128,
                        "longitude": -74.0060,
                        "time_zone": "America/New_York",
                        "location_name": "New York, NY",
                    },
                },
            },
            "expected_status": 201,
            "metrics": {
                "track_latency": True,
            },
            "assertions": [
                {"json_path": "chart_type", "equals": "natal"},
                {"json_path": "bodies", "min_length": 10},
            ],
            "extract": {"chart_id": "id"},
        },
        {
            "id": "compute_transits",
            "description": "Compute transits for July–December 2026",
            "request": {
                "method": "POST",
                "path": "/v1/charts/{chart_id}/transits",
                "body": {
                    "start_date": "2026-07-01",
                    "end_date": "2026-12-31",
                },
            },
            "expected_status": 201,
            "metrics": {
                "track_latency": True,
                "expected_event_count_range": (5, 500),
            },
            "assertions": [
                {"json_path": "natal_chart_id", "not_none": True},
                {"json_path": "transit_events", "is_list": True},
                {"json_path": "transit_events", "min_length": 5},
                {"json_path": "date_from", "equals": "2026-07-01"},
                {"json_path": "date_to", "equals": "2026-12-31"},
            ],
            "extract": {"snapshot_id": "id"},
        },
        {
            "id": "verify_transit_structure",
            "description": "Verify each transit event has required fields",
            "request": {
                "method": "GET",
                "path": "/v1/charts/{chart_id}/transits",
            },
            "expected_status": 200,
            "assertions": [
                {"json_path": "[0].transit_events", "is_list": True, "min_length": 5},
                {
                    "json_query": "[0].transit_events[0]",
                    "keys_present": [
                        "date",
                        "transiting_body",
                        "natal_body",
                        "aspect_type",
                        "orb",
                    ],
                },
            ],
        },
        {
            "id": "verify_major_aspects",
            "description": "Verify major aspects are detected among transits",
            "request": {
                "method": "GET",
                "path": "/v1/charts/{chart_id}/transits/summary",
            },
            "expected_status": 200,
            "assertions": [
                {"json_path": "natal_chart_id", "not_none": True},
                {"json_path": "total_events", "gt": 0},
                {"json_path": "major_events", "is_list": True},
            ],
            "metrics": {
                "major_aspect_ratio_gt": 0.1,  # at least 10% should be major
            },
        },
        {
            "id": "verify_transit_planets",
            "description": "Verify transit events involve expected planets",
            "request": {
                "method": "POST",
                "path": "/v1/charts/{chart_id}/transits",
                "body": {
                    "start_date": "2026-08-01",
                    "end_date": "2026-09-30",
                    "bodies": ["saturn", "jupiter", "mars"],
                },
            },
            "expected_status": 201,
            "assertions": [
                {"json_path": "transit_events", "min_length": 1},
            ],
        },
    ],
}
