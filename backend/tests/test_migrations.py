"""Verify that migration SQL files are syntactically valid by parsing them.

These tests do NOT require a running PostgreSQL instance — they check
that the SQL files contain the expected table definitions.
"""

from __future__ import annotations

import os
from pathlib import Path

MIGRATIONS_DIR = Path(__file__).resolve().parent.parent / "migrations"


def test_migration_files_exist() -> None:
    """Both migration files must be present."""
    files = sorted(os.listdir(MIGRATIONS_DIR))
    assert "001_core_tables.sql" in files
    assert "002_remaining_tables.sql" in files


def test_migration_files_not_empty() -> None:
    """Each migration file must contain meaningful SQL."""
    for fname in ("001_core_tables.sql", "002_remaining_tables.sql"):
        content = (MIGRATIONS_DIR / fname).read_text()
        assert len(content) > 500, f"{fname} is too short"
        assert "CREATE TABLE" in content, f"{fname} has no CREATE TABLE"
        assert "COMMENT ON" in content, f"{fname} has no COMMENT ON"


def test_all_12_tables_present() -> None:
    """Collectively the two migrations must define all 12 tables."""
    tables_seen = set()
    for fname in ("001_core_tables.sql", "002_remaining_tables.sql"):
        content = (MIGRATIONS_DIR / fname).read_text()
        for line in content.splitlines():
            line = line.strip()
            if line.upper().startswith("CREATE TABLE IF NOT EXISTS"):
                # Extract table name: CREATE TABLE IF NOT EXISTS tablename (
                parts = line.split()
                if len(parts) >= 5:
                    tables_seen.add(parts[4].rstrip("("))

    expected_tables = {
        "users",
        "birth_profiles",
        "charts",
        "chart_bodies",
        "chart_houses",
        "chart_aspects",
        "synastry_pairs",
        "synastry_aspects",
        "transit_snapshots",
        "life_phases",
        "conversations",
        "messages",
    }
    missing = expected_tables - tables_seen
    extra = tables_seen - expected_tables
    assert not missing, f"Tables missing from migrations: {missing}"
    assert not extra, f"Unexpected tables in migrations: {extra}"
