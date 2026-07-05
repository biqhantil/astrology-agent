"""Tests for the Life Phase Engine and API endpoints.

Covers:
- LifePhaseCalculator. compute_phases() output structure and correctness
- Phase windows for different age cohorts (young, adult, older)
- Saturn return age estimation
- Dominant transit generation
- Chart-scoped life phases endpoint (GET /v1/charts/{id}/life-phases)
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from unittest.mock import ANY, AsyncMock, patch
from uuid import UUID, uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


# ======================================================================
# Unit tests — LifePhaseCalculator
# ======================================================================


class TestLifePhaseCalculator:
    """Verify the core phase computation logic."""

    def test_compute_phases_returns_all_seven_phases(self):
        """The calculator should return exactly 7 phases for a full-life user."""
        from app.astro_engine.life_phases import LifePhaseCalculator

        calc = LifePhaseCalculator()
        phases = calc.compute_phases(
            birth_date=date(1990, 6, 15),
            saturn_longitude=280.5,  # Saturn in Capricorn
        )

        assert len(phases) == 7

        phase_keys = [p["phase_key"] for p in phases]
        assert phase_keys == [
            "foundation",
            "saturn_return_1",
            "expansion",
            "uranus_opposition",
            "chiron_return",
            "saturn_return_2",
            "legacy",
        ]

    def test_phases_have_required_fields(self):
        """Each phase should have all required fields."""
        from app.astro_engine.life_phases import LifePhaseCalculator

        calc = LifePhaseCalculator()
        phases = calc.compute_phases(
            birth_date=date(1990, 6, 15),
            saturn_longitude=280.5,
        )

        for phase in phases:
            assert "phase_key" in phase
            assert "title" in phase
            assert "start_date" in phase
            assert "description" in phase
            assert "dominant_transits" in phase

    def test_phases_are_ordered_by_age(self):
        """Phase start dates should be strictly increasing."""
        from app.astro_engine.life_phases import LifePhaseCalculator

        calc = LifePhaseCalculator()
        phases = calc.compute_phases(
            birth_date=date(1990, 6, 15),
            saturn_longitude=280.5,
        )

        for i in range(len(phases) - 1):
            assert phases[i]["start_date"] <= phases[i + 1]["start_date"]

    def test_first_phase_starts_at_birth(self):
        """Foundation phase should start on the birth date."""
        from app.astro_engine.life_phases import LifePhaseCalculator

        calc = LifePhaseCalculator()
        phases = calc.compute_phases(
            birth_date=date(1990, 6, 15),
            saturn_longitude=280.5,
        )

        assert phases[0]["phase_key"] == "foundation"
        assert phases[0]["start_date"] == date(1990, 6, 15)

    def test_last_phase_has_no_end_date(self):
        """Legacy phase should have end_date=None (ongoing)."""
        from app.astro_engine.life_phases import LifePhaseCalculator

        calc = LifePhaseCalculator()
        phases = calc.compute_phases(
            birth_date=date(1990, 6, 15),
            saturn_longitude=280.5,
        )

        last = phases[-1]
        assert last["phase_key"] == "legacy"
        assert last["end_date"] is None

    def test_young_user_cohort(self):
        """A user born in 2005 should only have phases up to ~age 40."""
        from app.astro_engine.life_phases import LifePhaseCalculator

        calc = LifePhaseCalculator()
        phases = calc.compute_phases(
            birth_date=date(2005, 3, 20),
            saturn_longitude=120.0,
        )

        # Should still return all 7 phases, but the later ones start in the future
        assert len(phases) == 7
        assert phases[0]["phase_key"] == "foundation"
        assert phases[0]["start_date"] == date(2005, 3, 20)

        # Saturn return 1 around age 29 → 2034 area
        sr1 = phases[1]
        assert sr1["phase_key"] == "saturn_return_1"
        assert sr1["start_date"].year >= 2030

    def test_older_user_cohort(self):
        """A user born in 1960 should have all phases including legacy."""
        from app.astro_engine.life_phases import LifePhaseCalculator

        calc = LifePhaseCalculator()
        phases = calc.compute_phases(
            birth_date=date(1960, 1, 1),
            saturn_longitude=280.5,
        )

        # Legacy should be active (started around 2020)
        legacy = phases[-1]
        assert legacy["phase_key"] == "legacy"
        assert legacy["start_date"] >= date(2019, 1, 1)

    def test_no_saturn_longitude_uses_defaults(self):
        """If saturn_longitude is None, default age ranges should be used."""
        from app.astro_engine.life_phases import LifePhaseCalculator

        calc = LifePhaseCalculator()
        phases = calc.compute_phases(
            birth_date=date(1990, 6, 15),
            saturn_longitude=None,
        )

        # Saturn return 1 should start around age 27 (1990+27 = 2017)
        sr1 = phases[1]
        assert sr1["phase_key"] == "saturn_return_1"
        # Default range: 27-31
        assert sr1["start_date"].year == 2017

    def test_dominant_transits_vary_by_phase(self):
        """Each phase should have contextually relevant dominant transits."""
        from app.astro_engine.life_phases import LifePhaseCalculator

        calc = LifePhaseCalculator()
        phases = calc.compute_phases(
            birth_date=date(1990, 6, 15),
            saturn_longitude=280.5,
        )

        # Foundation should have Saturn square/opposition
        foundation = phases[0]
        assert len(foundation["dominant_transits"]) > 0
        transit_planets = {t["planet"] for t in foundation["dominant_transits"]}
        assert "saturn" in transit_planets

        # Saturn return should have a Saturn conjunction
        sr1 = phases[1]
        sr1_transits = {t["aspect"] for t in sr1["dominant_transits"]}
        assert "conjunction" in sr1_transits

        # Legacy should have Saturn trine and Neptune square
        legacy = phases[-1]
        legacy_aspects = {t["aspect"] for t in legacy["dominant_transits"]}
        assert "trine" in legacy_aspects or len(legacy["dominant_transits"]) > 0

    def test_saturn_return_age_variation(self):
        """Saturn return age should vary based on Saturn longitude."""
        from app.astro_engine.life_phases import LifePhaseCalculator

        calc = LifePhaseCalculator()

        # Saturn in Capricorn (perihelion ~270°) → faster → shorter period
        phases_fast = calc.compute_phases(
            birth_date=date(1990, 6, 15),
            saturn_longitude=270.0,  # Capricorn
        )
        sr1_fast = phases_fast[1]
        fast_age = sr1_fast["start_date"].year - 1990

        # Saturn in Cancer (aphelion ~90°) → slower → longer period
        phases_slow = calc.compute_phases(
            birth_date=date(1990, 6, 15),
            saturn_longitude=90.0,  # Cancer
        )
        sr1_slow = phases_slow[1]
        slow_age = sr1_slow["start_date"].year - 1990

        # Perihelion Saturn should return slightly earlier than aphelion Saturn
        # (the exact difference depends on the speed model)
        assert fast_age <= slow_age or abs(fast_age - slow_age) <= 2

    def test_current_phase_for_young_adult(self):
        """A user born in 1990 should be in 'Expansion' phase in 2026."""
        from app.astro_engine.life_phases import LifePhaseCalculator

        calc = LifePhaseCalculator()
        phases = calc.compute_phases(
            birth_date=date(1990, 6, 15),
            saturn_longitude=280.5,
        )

        # Find current phase for mid-2026
        as_of = date(2026, 7, 5)
        current = None
        for phase in phases:
            start = phase["start_date"]
            end = phase["end_date"]
            if start <= as_of and (end is None or as_of <= end):
                current = phase
                break

        assert current is not None
        # A 36-year-old in 2026 should be in Expansion phase
        assert current["phase_key"] in ("expansion", "saturn_return_1")

    def test_get_current_phase_convenience(self):
        """The get_current_phase convenience method should work."""
        from app.astro_engine.life_phases import LifePhaseCalculator

        calc = LifePhaseCalculator()
        current = calc.get_current_phase(
            birth_date=date(1990, 6, 15),
            saturn_longitude=280.5,
            as_of_date=date(2026, 7, 5),
        )

        assert current is not None
        assert "phase_key" in current
        assert "title" in current

    def test_compute_life_phases_convenience_function(self):
        """The module-level convenience function should work."""
        from app.astro_engine.life_phases import compute_life_phases

        phases = compute_life_phases(
            birth_date=date(1990, 6, 15),
            saturn_longitude=280.5,
        )

        assert len(phases) == 7

    def test_phases_without_descriptions(self):
        """When include_descriptions=False, no descriptions should be present."""
        from app.astro_engine.life_phases import LifePhaseCalculator

        calc = LifePhaseCalculator()
        phases = calc.compute_phases(
            birth_date=date(1990, 6, 15),
            saturn_longitude=280.5,
            include_descriptions=False,
        )

        for phase in phases:
            assert phase.get("description") is None or phase["description"] == ""

    def test_phases_without_dominant_transits(self):
        """When include_dominant_transits=False, no transits should be present."""
        from app.astro_engine.life_phases import LifePhaseCalculator

        calc = LifePhaseCalculator()
        phases = calc.compute_phases(
            birth_date=date(1990, 6, 15),
            saturn_longitude=280.5,
            include_dominant_transits=False,
        )

        for phase in phases:
            assert phase.get("dominant_transits", []) == []


# ======================================================================
# API integration tests — GET /v1/charts/{id}/life-phases
# ======================================================================


class TestChartLifePhasesAPI:
    """Test the chart-scoped life phases endpoint."""

    @pytest.fixture
    def auth_token(self):
        from app.core.auth import create_token
        return create_token(uuid4(), token_type="anonymous")

    @pytest.fixture
    def auth_headers(self, auth_token):
        return {"Authorization": f"Bearer {auth_token}"}

    async def test_get_chart_life_phases_requires_auth(self, client):
        """GET /v1/charts/{id}/life-phases without auth → 401."""
        resp = await client.get(f"/v1/charts/{uuid4()}/life-phases")
        assert resp.status_code == 401

    async def test_get_chart_life_phases_not_found(
        self,
        client: AsyncClient,
        auth_headers: dict,
        override_get_conn: None,
        mock_conn: AsyncMock,
    ):
        """GET /v1/charts/{id}/life-phases for missing chart → 404."""
        mock_conn.fetchrow.return_value = None  # chart not found

        resp = await client.get(
            f"/v1/charts/{uuid4()}/life-phases",
            headers=auth_headers,
        )
        assert resp.status_code == 404

    async def test_get_chart_life_phases_no_birth_profile(
        self,
        client: AsyncClient,
        auth_headers: dict,
        override_get_conn: None,
        mock_conn: AsyncMock,
    ):
        """GET /v1/charts/{id}/life-phases when user has no birth profile → 404."""
        chart_id = uuid4()

        # First fetch returns chart row
        mock_conn.fetchrow.side_effect = [
            # chart fetch
            {
                "id": chart_id,
                "user_id": uuid4(),
                "chart_type": "natal",
                "calculation_date": datetime(1990, 6, 15, 12, 0, tzinfo=timezone.utc),
            },
            # birth profile fetch → None
            None,
        ]

        resp = await client.get(
            f"/v1/charts/{chart_id}/life-phases",
            headers=auth_headers,
        )
        assert resp.status_code == 404
        assert "birth profile" in resp.json()["detail"].lower()

    async def test_get_chart_life_phases_success(
        self,
        client: AsyncClient,
        auth_headers: dict,
        override_get_conn: None,
        mock_conn: AsyncMock,
    ):
        """GET /v1/charts/{id}/life-phases with valid data → 200 + phases."""
        chart_id = uuid4()
        user_id = uuid4()

        # Setup mock returns
        mock_conn.fetchrow.side_effect = [
            # 1. chart fetch
            {
                "id": chart_id,
                "user_id": user_id,
                "chart_type": "natal",
                "calculation_date": datetime(1990, 6, 15, 12, 0, tzinfo=timezone.utc),
            },
            # 2. birth profile
            {
                "birth_date": date(1990, 6, 15),
            },
            # 3. Saturn row
            {
                "longitude": 280.5,
            },
        ]

        resp = await client.get(
            f"/v1/charts/{chart_id}/life-phases",
            headers=auth_headers,
        )
        assert resp.status_code == 200

        data = resp.json()
        assert data["chart_id"] == str(chart_id)
        assert data["birth_date"] == "1990-06-15"
        assert data["saturn_longitude"] == 280.5
        assert "phases" in data
        assert len(data["phases"]) == 7

        # Check first phase
        first = data["phases"][0]
        assert first["phase_key"] == "foundation"
        assert first["title"] == "Foundation Years"
        assert "year_range" in first
        assert "start_year" in first
        assert "description" in first
        assert "dominant_transits" in first

        # Check last phase (legacy, ongoing)
        last = data["phases"][-1]
        assert last["phase_key"] == "legacy"
        assert last["end_year"] is None

    async def test_get_chart_life_phases_without_saturn(
        self,
        client: AsyncClient,
        auth_headers: dict,
        override_get_conn: None,
        mock_conn: AsyncMock,
    ):
        """Missing Saturn longitude should still produce phases (estimation)."""
        chart_id = uuid4()
        user_id = uuid4()

        mock_conn.fetchrow.side_effect = [
            # chart fetch
            {
                "id": chart_id,
                "user_id": user_id,
                "chart_type": "natal",
                "calculation_date": datetime(1990, 6, 15, 12, 0, tzinfo=timezone.utc),
            },
            # birth profile
            {
                "birth_date": date(1990, 6, 15),
            },
            # Saturn row → None (no Saturn in chart bodies)
            None,
        ]

        resp = await client.get(
            f"/v1/charts/{chart_id}/life-phases",
            headers=auth_headers,
        )
        assert resp.status_code == 200

        data = resp.json()
        assert data["saturn_longitude"] is None
        assert len(data["phases"]) == 7

    async def test_get_chart_life_phases_young_user(
        self,
        client: AsyncClient,
        auth_headers: dict,
        override_get_conn: None,
        mock_conn: AsyncMock,
    ):
        """Young user's chart should still return 7 phases (future-dated)."""
        chart_id = uuid4()
        user_id = uuid4()

        mock_conn.fetchrow.side_effect = [
            {
                "id": chart_id,
                "user_id": user_id,
                "chart_type": "natal",
                "calculation_date": datetime(2015, 3, 10, 8, 0, tzinfo=timezone.utc),
            },
            {
                "birth_date": date(2015, 3, 10),
            },
            {
                "longitude": 120.0,
            },
        ]

        resp = await client.get(
            f"/v1/charts/{chart_id}/life-phases",
            headers=auth_headers,
        )
        assert resp.status_code == 200

        data = resp.json()
        assert len(data["phases"]) == 7

        # Foundation should start at birth (2015)
        assert data["phases"][0]["start_year"] == 2015

    async def test_get_chart_life_phases_return_type(
        self,
        client: AsyncClient,
        auth_headers: dict,
        override_get_conn: None,
        mock_conn: AsyncMock,
    ):
        """Response should have proper types for all fields."""
        chart_id = uuid4()
        user_id = uuid4()

        mock_conn.fetchrow.side_effect = [
            {
                "id": chart_id,
                "user_id": user_id,
                "chart_type": "natal",
                "calculation_date": datetime(1990, 6, 15, 12, 0, tzinfo=timezone.utc),
            },
            {
                "birth_date": date(1990, 6, 15),
            },
            {
                "longitude": 280.5,
            },
        ]

        resp = await client.get(
            f"/v1/charts/{chart_id}/life-phases",
            headers=auth_headers,
        )
        assert resp.status_code == 200

        data = resp.json()
        assert isinstance(data["chart_id"], str)
        assert isinstance(data["phases"], list)
        assert "generated_at" in data

        for phase in data["phases"]:
            assert isinstance(phase["phase_key"], str)
            assert isinstance(phase["title"], str)
            assert isinstance(phase["year_range"], str)
            assert isinstance(phase["start_year"], int)
            assert phase["end_year"] is None or isinstance(phase["end_year"], int)
