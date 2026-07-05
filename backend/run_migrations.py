#!/usr/bin/env python3
"""Execute all SQL migration files against the PostgreSQL database.

Usage:
    python run_migrations.py            # Run all pending migrations
    python run_migrations.py --check    # Only check which migrations would run
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

import asyncpg

# Allow running from project root or backend directory
BACKEND_DIR = Path(__file__).resolve().parent
MIGRATIONS_DIR = BACKEND_DIR / "migrations"

# Database connection params (mirrors config.py defaults)
DB_CONFIG = {
    "host": os.getenv("POSTGRES_HOST", "localhost"),
    "port": int(os.getenv("POSTGRES_PORT", "5432")),
    "user": os.getenv("POSTGRES_USER", "astrology"),
    "password": os.getenv("POSTGRES_PASSWORD", "astrology_dev"),
    "database": os.getenv("POSTGRES_DB", "astrology_agent"),
}


async def get_applied_migrations(conn: asyncpg.Connection) -> set[str]:
    """Return the set of already-applied migration filenames."""
    await conn.execute(
        """
        CREATE TABLE IF NOT EXISTS _migrations (
            filename    VARCHAR(255) PRIMARY KEY,
            applied_at  TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    rows = await conn.fetch("SELECT filename FROM _migrations ORDER BY filename")
    return {row["filename"] for row in rows}


async def run() -> None:
    conn = await asyncpg.connect(**DB_CONFIG)
    try:
        applied = await get_applied_migrations(conn)
        migration_files = sorted(
            f for f in os.listdir(MIGRATIONS_DIR) if f.endswith(".sql")
        )

        pending = [f for f in migration_files if f not in applied]

        if "--check" in sys.argv:
            print(f"Applied: {len(applied)} migrations")
            print(f"Pending: {len(pending)} migrations")
            for name in pending:
                print(f"  ⏳ {name}")
            return

        if not pending:
            print("All migrations already applied. Nothing to do.")
            return

        for filename in pending:
            path = MIGRATIONS_DIR / filename
            sql = path.read_text()
            print(f"Applying: {filename} ...")
            async with conn.transaction():
                await conn.execute(sql)
                await conn.execute(
                    "INSERT INTO _migrations (filename) VALUES ($1)", filename
                )
            print(f"  ✓ {filename} applied.")

        print(f"\nDone. {len(pending)} migration(s) applied.")

    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(run())
