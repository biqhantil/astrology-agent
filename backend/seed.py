#!/usr/bin/env python3
"""Seed the database with one test user + birth profile for development."""

from __future__ import annotations

import asyncio
import os
from datetime import date, time

import asyncpg

DB_CONFIG = {
    "host": os.getenv("POSTGRES_HOST", "localhost"),
    "port": int(os.getenv("POSTGRES_PORT", "5432")),
    "user": os.getenv("POSTGRES_USER", "astrology"),
    "password": os.getenv("POSTGRES_PASSWORD", "astrology_dev"),
    "database": os.getenv("POSTGRES_DB", "astrology_agent"),
}


async def seed() -> None:
    conn = await asyncpg.connect(**DB_CONFIG)
    try:
        # Check if test user already exists
        existing = await conn.fetchrow(
            "SELECT id FROM users WHERE email = 'test@example.com'"
        )
        if existing:
            print(f"Test user already exists (id={existing['id']}). Skipping seed.")
            return

        # Create test user
        user_id = await conn.fetchval(
            """
            INSERT INTO users (email, display_name, locale)
            VALUES ('test@example.com', 'Test User', 'en')
            RETURNING id
            """
        )
        print(f"Created user: {user_id}")

        # Create birth profile (Einstein's birth data for a known test chart)
        birth_profile_id = await conn.fetchval(
            """
            INSERT INTO birth_profiles (
                user_id, birth_date, birth_time, time_zone,
                latitude, longitude, location_name, house_system,
                sun_sign, moon_sign, rising_sign
            ) VALUES (
                $1, '1879-03-14', '11:30:00', 'Europe/Berlin',
                48.3984, 9.9916, 'Ulm, Germany', 'P',
                'pisces', 'virgo', 'libra'
            )
            RETURNING id
            """,
            user_id,
        )
        print(f"Created birth_profile: {birth_profile_id}")

        # Verify FK relationships
        count = await conn.fetchval("SELECT COUNT(*) FROM users")
        print(f"Total users: {count}")

        bp_check = await conn.fetchval(
            "SELECT has_unknown_time FROM birth_profiles WHERE id = $1",
            birth_profile_id,
        )
        print(f"has_unknown_time (should be FALSE): {bp_check}")

        print("\n✓ Seed completed successfully.")

    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(seed())
