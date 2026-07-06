"""Verify that migration SQL files are syntactically valid by parsing them.

These tests do NOT require a running PostgreSQL instance — they check
that the SQL files contain the expected table definitions.
"""

from __future__ import annotations

import os
from pathlib import Path

MIGRATIONS_DIR = Path(__file__).resolve().parent.parent / "migrations"

# The current SQLite-compatible migration (replaces 001/002)
SQLITE_MIGRATION = "003_sqlite.sql"


def test_migration_file_exists() -> None:
    """The SQLite migration file must be present."""
    files = sorted(os.listdir(MIGRATIONS_DIR))
    assert SQLITE_MIGRATION in files


def test_migration_files_not_empty() -> None:
    """The migration file must contain meaningful SQL."""
    content = (MIGRATIONS_DIR / SQLITE_MIGRATION).read_text()
    assert len(content) > 500, f"{SQLITE_MIGRATION} is too short"
    assert "CREATE TABLE" in content, f"{SQLITE_MIGRATION} has no CREATE TABLE"


def test_all_12_tables_present() -> None:
    """003_sqlite.sql must define all 12 tables."""
    tables_seen = set()
    content = (MIGRATIONS_DIR / SQLITE_MIGRATION).read_text()
    for line in content.splitlines():
        line = line.strip()
        if line.upper().startswith("CREATE TABLE IF NOT EXISTS"):
            # Line format: CREATE TABLE IF NOT EXISTS tablename (
            parts = line.split()
            if len(parts) >= 6:
                tables_seen.add(parts[5].rstrip("("))

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
