"""Tests for the transit engine and API endpoints.

Tests the TransitCalculator class and the POST/GET transit endpoints.
"""

from __future__ import annotations

from datetime import date, datetime, timezone, timedelta
from unittest.mock import AsyncMock, patch
from uuid import UUID, uuid4

import pytest
from httpx import AsyncClient

from app.astro_engine.transit import TransitCalculator, SLOW_PLANETS


# ── Sample natal data (Einstein's chart) ────────────────────────

EINSTEIN_CHART_ID = UUID("00000000-0000-0000-0000-000000000001")

EINSTEIN_NATAL_BODIES = [
    {"body_key": "sun", "longitude": 353.535, "sign": "pisces", "sign_degree": 23.53, "house": 8, "speed": 0.95},
    {"body_key": "moon", "longitude": 254.912, "sign": "sagittarius", "sign_degree": 24.91, "house": 5, "speed": 13.2},
    {"body_key": "mercury", "longitude": 347.123, "sign": "pisces", "sign_degree": 17.12, "house": 8, "speed": 1.5},
    {"body_key": "venus", "longitude": 12.456, "sign": "aries", "sign_degree": 12.46, "house": 9, "speed": 1.2},
    {"body_key": "mars", "longitude": 100.789, "sign": "cancer", "sign_degree": 10.79, "house": 12, "speed": 0.7},
    {"body_key": "jupiter", "longitude": 190.123, "sign": "libra", "sign_degree": 10.12, "house": 3, "speed": 0.1},
    {"body_key": "saturn", "longitude": 280.456, "sign": "capricorn", "sign_degree": 10.46, "house": 6, "speed": -0.05},
    {"body_key": "uranus", "longitude": 150.789, "sign": "virgo", "sign_degree": 0.79, "house": 1, "speed": 0.02},
    {"body_key": "neptune", "longitude": 60.123, "sign": "taurus", "sign_degree": 0.12, "house": 10, "speed": -0.01},
    {"body_key": "pluto", "longitude": 40.456, "sign": "taurus", "sign_degree": 10.46, "house": 10, "speed": 0.005},
    {"body_key": "asc", "longitude": 109.671, "sign": "cancer", "sign_degree": 19.67, "house": 1, "speed": 0.0},
    {"body_key": "mc", "longitude": 353.685, "sign": "pisces", "sign_degree": 23.68, "house": 10, "speed": 0.0},
]

EINSTEIN_NATAL_HOUSES = [
    {"house_number": 1, "cusps_longitude": 109.671, "sign": "cancer", "sign_degree": 19.67},
    {"house_number": 2, "cusps_longitude": 139.2, "sign": "leo", "sign_degree": 19.2},
    {"house_number": 3, "cusps_longitude": 173.5, "sign": "virgo", "sign_degree": 23.5},
    {"house_number": 4, "cusps_longitude": 203.8, "sign": "libra", "sign_degree": 23.8},
    {"house_number": 5, "cusps_longitude": 230.1, "sign": "scorpio", "sign_degree": 20.1},
    {"house_number": 6, "cusps_longitude": 256.4, "sign": "sagittarius", "sign_degree": 16.4},
    {"house_number": 7, "cusps_longitude": 289.671, "sign": "capricorn", "sign_degree": 19.67},
    {"house_number": 8, "cusps_longitude": 319.2, "sign": "aquarius", "sign_degree": 19.2},
    {"house_number": 9, "cusps_longitude": 353.5, "sign": "pisces", "sign_degree": 23.5},
    {"house_number": 10, "cusps_longitude": 23.8, "sign": "aries", "sign_degree": 23.8},
    {"house_number": 11, "cusps_longitude": 50.1, "sign": "taurus", "sign_degree": 20.1},
    {"house_number": 12, "cusps_longitude": 76.4, "sign": "gemini", "sign_degree": 16.4},
]


# ======================================================================
# Unit tests — TransitCalculator
# ======================================================================


class TestTransitCalculator:
    """Verify the TransitCalculator computes aspects correctly."""

    def setup_method(self):
        self.calc = TransitCalculator(orb_major=8.0, orb_minor=2.0)

    def test_significant_transits_filters_major_only(self):
        """get_significant_transits with major_only=True filters minor aspects."""
        events = [
            {"date": date(2026, 1, 1), "transiting_body": "jupiter", "natal_body": "sun",
             "aspect_type": "conjunction", "orb": 1.0, "is_applying": True},
            {"date": date(2026, 1, 2), "transiting_body": "jupiter", "natal_body": "moon",
             "aspect_type": "quincunx", "orb": 0.5, "is_applying": True},
        ]
        significant = TransitCalculator.get_significant_transits(events, major_only=True)
        assert len(significant) == 1
        assert significant[0]["aspect_type"] == "conjunction"

    def test_significant_transits_slow_only(self):
        """get_significant_transits with slow_only=True filters fast planets."""
        events = [
            {"date": date(2026, 1, 1), "transiting_body": "jupiter", "natal_body": "sun",
             "aspect_type": "conjunction", "orb": 1.0, "is_applying": True},
            {"date": date(2026, 1, 2), "transiting_body": "mercury", "natal_body": "sun",
             "aspect_type": "square", "orb": 0.5, "is_applying": True},
        ]
        significant = TransitCalculator.get_significant_transits(
            events, major_only=False, slow_only=True,
        )
        assert len(significant) == 1
        assert significant[0]["transiting_body"] == "jupiter"

    def test_slow_planets_constant(self):
        """SLOW_PLANETS should contain the outer planets."""
        assert "jupiter" in SLOW_PLANETS
        assert "saturn" in SLOW_PLANETS
        assert "uranus" in SLOW_PLANETS
        assert "neptune" in SLOW_PLANETS
        assert "pluto" in SLOW_PLANETS
        assert "mercury" not in SLOW_PLANETS
        assert "venus" not in SLOW_PLANETS

    def test_find_house(self):
        """_find_house should correctly assign a house number."""
        cusps = [h["cusps_longitude"] for h in EINSTEIN_NATAL_HOUSES]
        # Sun at 353.5° falls in house 9 (cusp 353.5 → wraps to 23.8)
        house = TransitCalculator._find_house(353.5, cusps)
        assert house == 9, f"Expected 9, got {house}"

        # Mars at 100.8° falls in house 12 (cusp 76.4-109.7)
        house = TransitCalculator._find_house(100.8, cusps)
        assert house == 12, f"Expected 12, got {house}"

        # At 200°: cusp[2]=173.5 (house 3), cusp[3]=203.8 (house 4) → 200 falls between → house 3
        house = TransitCalculator._find_house(200.0, cusps)
        assert house == 3, f"Expected 3, got {house}"

    def test_find_house_wrap_around(self):
        """_find_house handles 0°/360° wrap correctly."""
        # House 9 cusp is 353.5, house 10 cusp is 23.8 (wraps around)
        # At 0°: cusp[8]=353.5 (house 9 start), cusp[9]=23.8 (house 10 start)
        # 0 >= 353.5? No. 0 < 23.8? Yes → falls in house 9
        cusps = [h["cusps_longitude"] for h in EINSTEIN_NATAL_HOUSES]
        house = TransitCalculator._find_house(0.0, cusps)
        assert house == 9, f"Expected 9, got {house}"

        # At 30°: cusp[9]=23.8 (house 10 start), cusp[10]=50.1 (house 11 start)
        house = TransitCalculator._find_house(30.0, cusps)
        assert house == 10, f"Expected 10, got {house}"


# ======================================================================
# Mock transit calculator for integration tests
# ======================================================================


class TestTransitAPI:
    """Test the transit REST endpoints with mocked database."""

    @pytest.fixture
    def auth_token(self):
        from app.core.auth import create_token
        return create_token(uuid4(), token_type="anonymous")

    @pytest.fixture
    def auth_headers(self, auth_token):
        return {"Authorization": f"Bearer {auth_token}"}

    # ── POST /v1/charts/{chart_id}/transits ─────────────────────

    async def test_create_transits_requires_auth(self, client: AsyncClient):
        """POST without auth → 401."""
        resp = await client.post(f"/v1/charts/{uuid4()}/transits", json={})
        assert resp.status_code == 401

    async def test_create_transits_chart_not_found(
        self, client: AsyncClient, auth_headers: dict,
        override_get_conn: None, mock_conn: AsyncMock,
    ):
        """POST with non-existent chart → 404."""
        mock_conn.fetchrow.return_value = None

        resp = await client.post(
            f"/v1/charts/{uuid4()}/transits",
            json={},
            headers=auth_headers,
        )
        assert resp.status_code == 404

    async def test_create_transits_no_bodies(
        self, client: AsyncClient, auth_headers: dict,
        override_get_conn: None, mock_conn: AsyncMock,
    ):
        """POST when chart has no bodies → 404."""
        mock_conn.fetchrow.return_value = {
            "id": uuid4(), "user_id": uuid4(), "chart_type": "natal",
            "latitude": 40.7, "longitude": -74.0, "time_zone": "America/New_York",
            "house_system": "P", "raw_ephemeris": "{}",
        }
        mock_conn.fetch.side_effect = [  # first fetch = bodies (empty), second = houses
            [],
            [],
        ]

        resp = await client.post(
            f"/v1/charts/{uuid4()}/transits",
            json={},
            headers=auth_headers,
        )
        assert resp.status_code == 404

    async def test_get_transits_requires_auth(self, client: AsyncClient):
        """GET without auth → 401."""
        resp = await client.get(f"/v1/charts/{uuid4()}/transits")
        assert resp.status_code == 401

    async def test_get_transits_no_snapshots(
        self, client: AsyncClient, auth_headers: dict,
        override_get_conn: None, mock_conn: AsyncMock,
    ):
        """GET when no snapshots exist → 404."""
        mock_conn.fetch.return_value = []

        resp = await client.get(
            f"/v1/charts/{uuid4()}/transits",
            headers=auth_headers,
        )
        assert resp.status_code == 404

    async def test_get_transits_summary_no_snapshots(
        self, client: AsyncClient, auth_headers: dict,
        override_get_conn: None, mock_conn: AsyncMock,
    ):
        """GET /transits/summary when no snapshots exist → 404."""
        mock_conn.fetch.return_value = []

        chart_id = uuid4()
        resp = await client.get(
            f"/v1/charts/{chart_id}/transits/summary",
            headers=auth_headers,
        )
        assert resp.status_code == 404

    async def test_get_transits_with_data(
        self, client: AsyncClient, auth_headers: dict,
        override_get_conn: None, mock_conn: AsyncMock,
    ):
        """GET /transits returns cached snapshot data."""
        snapshot_id = uuid4()
        chart_id = uuid4()
        now = datetime.now(timezone.utc)

        mock_conn.fetch.return_value = [
            {
                "id": snapshot_id,
                "natal_chart_id": chart_id,
                "date_from": date(2026, 1, 1),
                "date_to": date(2026, 1, 3),
                "transit_events": [
                    {
                        "date": "2026-01-01",
                        "transiting_body": "jupiter",
                        "natal_body": "sun",
                        "aspect_type": "conjunction",
                        "orb": 1.5,
                        "is_applying": True,
                        "transit_house": 9,
                        "natal_house": 8,
                    }
                ],
                "created_at": now,
                "expires_at": now + timedelta(days=7),
            }
        ]

        resp = await client.get(
            f"/v1/charts/{chart_id}/transits",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["natal_chart_id"] == str(chart_id)
        assert len(data[0]["transit_events"]) == 1
        assert data[0]["transit_events"][0]["transiting_body"] == "jupiter"

    async def test_get_transits_summary(
        self, client: AsyncClient, auth_headers: dict,
        override_get_conn: None, mock_conn: AsyncMock,
    ):
        """GET /transits/summary returns condensed data."""
        chart_id = uuid4()
        now = datetime.now(timezone.utc)

        mock_conn.fetch.return_value = [
            {
                "id": uuid4(),
                "natal_chart_id": chart_id,
                "date_from": date(2026, 1, 1),
                "date_to": date(2026, 1, 31),
                "transit_events": [
                    {
                        "date": "2026-01-15",
                        "transiting_body": "saturn",
                        "natal_body": "moon",
                        "aspect_type": "square",
                        "orb": 0.5,
                        "is_applying": True,
                        "transit_house": 6,
                        "natal_house": 5,
                    },
                    {
                        "date": "2026-01-20",
                        "transiting_body": "mercury",
                        "natal_body": "venus",
                        "aspect_type": "sextile",
                        "orb": 2.0,
                        "is_applying": False,
                        "transit_house": 3,
                        "natal_house": 9,
                    },
                ],
                "created_at": now,
                "expires_at": now + timedelta(days=7),
            }
        ]

        resp = await client.get(
            f"/v1/charts/{chart_id}/transits/summary",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["natal_chart_id"] == str(chart_id)
        assert data["total_events"] == 2
        assert len(data["major_events"]) == 2  # both are major
        assert len(data["slow_planets"]) == 1  # saturn only
        assert data["slow_planets"][0]["transiting_body"] == "saturn"
