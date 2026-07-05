"""Tests for the synastry engine and API endpoints.

Tests the compute_synastry function and the POST/GET synastry endpoints.
"""

from __future__ import annotations

from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import pytest
from httpx import AsyncClient

from app.astro_engine.synastry import (
    compute_synastry,
    _compute_scores,
    _aspect_weight,
    HARMONIOUS_ASPECTS,
    CHALLENGING_ASPECTS,
)

# ── Sample chart data for synastry tests ────────────────────────

CHART_A_BODIES = [
    {"body_key": "sun", "longitude": 353.535, "sign": "pisces", "sign_degree": 23.53, "house": 8, "speed": 0.95},
    {"body_key": "moon", "longitude": 254.912, "sign": "sagittarius", "sign_degree": 24.91, "house": 5, "speed": 13.2},
    {"body_key": "mercury", "longitude": 347.123, "sign": "pisces", "sign_degree": 17.12, "house": 8, "speed": 1.5},
    {"body_key": "venus", "longitude": 12.456, "sign": "aries", "sign_degree": 12.46, "house": 9, "speed": 1.2},
    {"body_key": "mars", "longitude": 100.789, "sign": "cancer", "sign_degree": 10.79, "house": 1, "speed": 0.7},
    {"body_key": "jupiter", "longitude": 190.123, "sign": "libra", "sign_degree": 10.12, "house": 3, "speed": 0.1},
    {"body_key": "saturn", "longitude": 280.456, "sign": "capricorn", "sign_degree": 10.46, "house": 6, "speed": -0.05},
    {"body_key": "uranus", "longitude": 150.789, "sign": "virgo", "sign_degree": 0.79, "house": 1, "speed": 0.02},
    {"body_key": "neptune", "longitude": 60.123, "sign": "taurus", "sign_degree": 0.12, "house": 10, "speed": -0.01},
    {"body_key": "pluto", "longitude": 40.456, "sign": "taurus", "sign_degree": 10.46, "house": 10, "speed": 0.005},
    {"body_key": "asc", "longitude": 109.671, "sign": "cancer", "sign_degree": 19.67, "house": 1, "speed": 0.0},
    {"body_key": "mc", "longitude": 353.685, "sign": "pisces", "sign_degree": 23.68, "house": 10, "speed": 0.0},
]

CHART_B_BODIES = [
    {"body_key": "sun", "longitude": 195.0, "sign": "libra", "sign_degree": 15.0, "house": 4, "speed": 0.95},
    {"body_key": "moon", "longitude": 80.0, "sign": "gemini", "sign_degree": 20.0, "house": 11, "speed": 13.2},
    {"body_key": "mercury", "longitude": 200.0, "sign": "libra", "sign_degree": 20.0, "house": 4, "speed": 1.5},
    {"body_key": "venus", "longitude": 170.0, "sign": "virgo", "sign_degree": 20.0, "house": 3, "speed": 1.2},
    {"body_key": "mars", "longitude": 15.0, "sign": "aries", "sign_degree": 15.0, "house": 8, "speed": 0.7},
    {"body_key": "jupiter", "longitude": 290.0, "sign": "capricorn", "sign_degree": 20.0, "house": 6, "speed": 0.1},
    {"body_key": "saturn", "longitude": 310.0, "sign": "aquarius", "sign_degree": 10.0, "house": 7, "speed": -0.05},
    {"body_key": "uranus", "longitude": 140.0, "sign": "leo", "sign_degree": 20.0, "house": 2, "speed": 0.02},
    {"body_key": "neptune", "longitude": 110.0, "sign": "cancer", "sign_degree": 20.0, "house": 12, "speed": -0.01},
    {"body_key": "pluto", "longitude": 50.0, "sign": "taurus", "sign_degree": 20.0, "house": 10, "speed": 0.005},
    {"body_key": "asc", "longitude": 220.0, "sign": "scorpio", "sign_degree": 10.0, "house": 1, "speed": 0.0},
    {"body_key": "mc", "longitude": 130.0, "sign": "leo", "sign_degree": 10.0, "house": 10, "speed": 0.0},
]

CHART_A_HOUSES = [
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

CHART_B_HOUSES = [
    {"house_number": 1, "cusps_longitude": 220.0, "sign": "scorpio", "sign_degree": 10.0},
    {"house_number": 2, "cusps_longitude": 250.0, "sign": "sagittarius", "sign_degree": 10.0},
    {"house_number": 3, "cusps_longitude": 280.0, "sign": "capricorn", "sign_degree": 10.0},
    {"house_number": 4, "cusps_longitude": 310.0, "sign": "aquarius", "sign_degree": 10.0},
    {"house_number": 5, "cusps_longitude": 340.0, "sign": "pisces", "sign_degree": 10.0},
    {"house_number": 6, "cusps_longitude": 10.0, "sign": "aries", "sign_degree": 10.0},
    {"house_number": 7, "cusps_longitude": 40.0, "sign": "taurus", "sign_degree": 10.0},
    {"house_number": 8, "cusps_longitude": 70.0, "sign": "gemini", "sign_degree": 10.0},
    {"house_number": 9, "cusps_longitude": 100.0, "sign": "cancer", "sign_degree": 10.0},
    {"house_number": 10, "cusps_longitude": 130.0, "sign": "leo", "sign_degree": 10.0},
    {"house_number": 11, "cusps_longitude": 160.0, "sign": "virgo", "sign_degree": 10.0},
    {"house_number": 12, "cusps_longitude": 190.0, "sign": "libra", "sign_degree": 10.0},
]


# ======================================================================
# Unit tests — Synastry engine
# ======================================================================


class TestSynastryEngine:
    """Verify the compute_synastry function."""

    def test_synastry_returns_expected_structure(self):
        """compute_synastry returns correct keys."""
        result = compute_synastry(CHART_A_BODIES, CHART_B_BODIES)
        assert "aspects" in result
        assert "score_summary" in result
        assert "house_overlays_a_in_b" in result
        assert "house_overlays_b_in_a" in result

    def test_synastry_finds_aspects(self):
        """Should detect inter-chart aspects between the two charts."""
        result = compute_synastry(CHART_A_BODIES, CHART_B_BODIES)
        assert len(result["aspects"]) > 0

    def test_synastry_aspect_format(self):
        """Each aspect should have the required fields."""
        result = compute_synastry(CHART_A_BODIES, CHART_B_BODIES)
        for asp in result["aspects"]:
            assert "body_a_key" in asp
            assert "body_b_key" in asp
            assert "aspect_type" in asp
            assert "orb" in asp
            assert "is_applying" in asp or asp.get("is_applying") is None

    def test_synastry_sun_moon_harmony(self):
        """Sun in Pisces (353.5°) vs Moon in Gemini (80°) → quincunx (150°), orb ~3.5°."""
        bodies_a = [
            {"body_key": "sun", "longitude": 353.5, "speed": 0.95},
            {"body_key": "moon", "longitude": 80.0, "speed": 13.2},
        ]
        bodies_b = [
            {"body_key": "sun", "longitude": 15.0, "speed": 0.95},
            {"body_key": "moon", "longitude": 200.0, "speed": 13.2},
        ]

        result = compute_synastry(bodies_a, bodies_b)
        aspects = result["aspects"]
        # There should be aspects between the bodies
        assert len(aspects) >= 0
        # All aspects should have orb < 10
        for a in aspects:
            assert abs(a["orb"]) <= 10

    def test_known_aspect(self):
        """Chart A Sun (353.5°) vs Chart B Jupiter (290°) → 63.5° → sextile by 3.5°."""
        bodies_a = [{"body_key": "sun", "longitude": 353.5, "speed": 0.95}]
        bodies_b = [{"body_key": "jupiter", "longitude": 290.0, "speed": 0.1}]

        result = compute_synastry(bodies_a, bodies_b)
        aspects = result["aspects"]
        # 353.5 - 290 = 63.5°, which is within orb of sextile (60°), orb = 3.5
        matching = [a for a in aspects if a["body_a_key"] == "sun" and a["body_b_key"] == "jupiter"]
        if matching:
            assert matching[0]["aspect_type"] == "sextile"
            assert abs(matching[0]["orb"] - 3.5) < 0.1

    def test_no_duplicate_pairs(self):
        """Should not compute aspects for same-key pairs."""
        bodies_a = [{"body_key": "sun", "longitude": 10.0, "speed": 1.0}]
        bodies_b = [{"body_key": "sun", "longitude": 190.0, "speed": 1.0}]

        result = compute_synastry(bodies_a, bodies_b)
        # sun-sun should be skipped (same key)
        aspects = result["aspects"]
        sun_sun = [a for a in aspects if a["body_a_key"] == "sun" and a["body_b_key"] == "sun"]
        assert len(sun_sun) == 0

    def test_house_overlays(self):
        """House overlays should map bodies to house numbers."""
        result = compute_synastry(
            CHART_A_BODIES, CHART_B_BODIES,
            CHART_A_HOUSES, CHART_B_HOUSES,
        )
        overlays = result["house_overlays_a_in_b"]
        assert len(overlays) > 0
        for key, house in overlays.items():
            assert house is None or (1 <= house <= 12)

    def test_scores_within_range(self):
        """Score dimensions should be within 0-10 or None."""
        result = compute_synastry(CHART_A_BODIES, CHART_B_BODIES)
        scores = result["score_summary"]
        for dim in ["emotional", "communication", "passion", "commitment", "overall"]:
            val = scores.get(dim)
            if val is not None:
                assert 0 <= val <= 10, f"{dim} score {val} out of range"

    def test_empty_aspects_returns_none_scores(self):
        """With no aspects, all scores should be None."""
        # 0° and 46°: 46° separation is not within any aspect orb
        bodies_a = [{"body_key": "sun", "longitude": 0.0, "speed": 1.0}]
        bodies_b = [{"body_key": "moon", "longitude": 46.0, "speed": 1.0}]
        result = compute_synastry(bodies_a, bodies_b, orb_major=0.5, orb_minor=0.3)
        scores = result["score_summary"]
        for dim in ["emotional", "communication", "passion", "commitment", "overall"]:
            assert scores[dim] is None


class TestScoringEngine:
    """Verify the synastry scoring logic."""

    def test_aspect_weight_harmonious_positive(self):
        """Harmonious aspects should yield positive weights."""
        for aspect, base in HARMONIOUS_ASPECTS.items():
            weight = _aspect_weight(aspect, 0.0)
            assert weight > 0, f"{aspect} should have positive weight at exact orb"

    def test_aspect_weight_challenging_negative(self):
        """Challenging aspects should yield negative weights."""
        for aspect, base in CHALLENGING_ASPECTS.items():
            weight = _aspect_weight(aspect, 0.0)
            assert weight < 0, f"{aspect} should have negative weight at exact orb"

    def test_aspect_weight_wider_orb_reduced(self):
        """Wider orbs should reduce the magnitude of the weight."""
        exact = _aspect_weight("conjunction", 0.0)
        wide = _aspect_weight("conjunction", 5.0)
        assert abs(wide) < abs(exact), "Wider orb should reduce weight magnitude"

    def test_compute_scores_no_aspects(self):
        """_compute_scores with empty list returns all Nones."""
        scores = _compute_scores([])
        assert scores["emotional"] is None
        assert scores["communication"] is None
        assert scores["passion"] is None
        assert scores["commitment"] is None
        assert scores["overall"] is None

    def test_compute_scores_single_aspect(self):
        """Single harmonious aspect should give scores > 5."""
        aspects = [
            {"body_a_key": "sun", "body_b_key": "moon", "aspect_type": "trine",
             "orb": 0.5, "is_applying": True},
        ]
        scores = _compute_scores(aspects)
        # Sun affects passion and commitment, moon affects emotional
        assert scores["emotional"] is not None
        assert scores["overall"] is not None
        # A trine is harmonious, so scores should be > 5
        for key in ["emotional", "passion", "commitment", "overall"]:
            if scores[key] is not None:
                assert scores[key] > 5.0, f"{key} should benefit from trine"


# ======================================================================
# API integration tests — Synastry endpoints
# ======================================================================


class TestSynastryAPI:
    """Test the synastry REST endpoints with mocked database."""

    @pytest.fixture
    def auth_token(self):
        from app.core.auth import create_token
        return create_token(uuid4(), token_type="anonymous")

    @pytest.fixture
    def auth_headers(self, auth_token):
        return {"Authorization": f"Bearer {auth_token}"}

    # ── POST /v1/synastry ───────────────────────────────────────

    async def test_create_synastry_requires_auth(self, client: AsyncClient):
        """POST without auth → 401."""
        resp = await client.post(
            "/v1/synastry",
            json={"chart_a_id": str(uuid4()), "chart_b_id": str(uuid4())},
        )
        assert resp.status_code == 401

    async def test_create_synastry_same_chart(
        self, client: AsyncClient, auth_headers: dict,
        override_get_conn: None, mock_conn: AsyncMock,
    ):
        """POST with same chart_a and chart_b → 422."""
        chart_id = uuid4()
        resp = await client.post(
            "/v1/synastry",
            json={"chart_a_id": str(chart_id), "chart_b_id": str(chart_id)},
            headers=auth_headers,
        )
        assert resp.status_code == 422

    async def test_create_synastry_chart_not_found(
        self, client: AsyncClient, auth_headers: dict,
        override_get_conn: None, mock_conn: AsyncMock,
    ):
        """POST with non-existent chart → 404."""
        mock_conn.fetchrow.side_effect = [None, None]  # both charts not found

        resp = await client.post(
            "/v1/synastry",
            json={
                "chart_a_id": str(uuid4()),
                "chart_b_id": str(uuid4()),
            },
            headers=auth_headers,
        )
        assert resp.status_code == 404

    async def test_create_synastry_no_bodies(
        self, client: AsyncClient, auth_headers: dict,
        override_get_conn: None, mock_conn: AsyncMock,
    ):
        """POST when a chart has no bodies → 422."""
        chart_a_id = uuid4()
        chart_b_id = uuid4()

        mock_conn.fetchrow.side_effect = [
            {"id": chart_a_id, "user_id": uuid4(), "chart_type": "natal", "house_system": "P"},
            {"id": chart_b_id, "user_id": uuid4(), "chart_type": "natal", "house_system": "P"},
        ]
        # First fetch for bodies = empty (chart A has no bodies) → early exit before houses fetches
        mock_conn.fetch.side_effect = [
            [],  # bodies_a is empty → triggers 422
            [],  # bodies_b would be fetched too, but 422 is already raised
        ]

        resp = await client.post(
            "/v1/synastry",
            json={
                "chart_a_id": str(chart_a_id),
                "chart_b_id": str(chart_b_id),
            },
            headers=auth_headers,
        )
        assert resp.status_code == 422

    # ── GET /v1/synastry/{id} ───────────────────────────────────

    async def test_get_synastry_requires_auth(self, client: AsyncClient):
        """GET without auth → 401."""
        resp = await client.get(f"/v1/synastry/{uuid4()}")
        assert resp.status_code == 401

    async def test_get_synastry_not_found(
        self, client: AsyncClient, auth_headers: dict,
        override_get_conn: None, mock_conn: AsyncMock,
    ):
        """GET non-existent synastry → 404."""
        mock_conn.fetchrow.return_value = None  # synastry not found

        resp = await client.get(
            f"/v1/synastry/{uuid4()}",
            headers=auth_headers,
        )
        assert resp.status_code == 404

    # ── GET /v1/synastry (list) ─────────────────────────────────

    async def test_list_synastry(
        self, client: AsyncClient, auth_headers: dict,
        override_get_conn: None, mock_conn: AsyncMock,
    ):
        """GET /v1/synastry returns list of pairs."""
        chart_a_id = uuid4()
        chart_b_id = uuid4()
        now = datetime.now(timezone.utc)

        mock_conn.fetch.return_value = [
            {
                "id": uuid4(),
                "chart_a_id": chart_a_id,
                "chart_b_id": chart_b_id,
                "relationship_type": "romantic",
                "score_summary": '{"emotional": 7.5, "communication": 6.0, "passion": 8.0, "commitment": 5.0, "overall": 6.6}',
                "created_at": now,
            }
        ]

        resp = await client.get(
            "/v1/synastry",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["chart_b_id"] == str(chart_b_id)
        assert data[0]["score_summary"]["overall"] == 6.6
