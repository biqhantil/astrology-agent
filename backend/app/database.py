"""Async PostgreSQL connection pool management via asyncpg."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncGenerator

import asyncpg

from app.config import settings


class DatabasePool:
    """Singleton-style wrapper around an asyncpg connection pool."""

    def __init__(self) -> None:
        self._pool: asyncpg.Pool | None = None

    # ── Lifecycle ────────────────────────────────────────────────

    async def connect(self) -> None:
        """Create the connection pool."""
        if self._pool is not None:
            return
        self._pool = await asyncpg.create_pool(
            host=settings.POSTGRES_HOST,
            port=settings.POSTGRES_PORT,
            user=settings.POSTGRES_USER,
            password=settings.POSTGRES_PASSWORD,
            database=settings.POSTGRES_DB,
            min_size=settings.POSTGRES_MIN_CONNECTIONS,
            max_size=settings.POSTGRES_MAX_CONNECTIONS,
            command_timeout=30,
        )

    async def disconnect(self) -> None:
        """Close all connections in the pool."""
        if self._pool is None:
            return
        await self._pool.close()
        self._pool = None

    # ── Access ───────────────────────────────────────────────────

    async def execute(self, query: str, *args: object) -> str:
        """Execute a single query and return the command tag."""
        if self._pool is None:
            raise RuntimeError("Database pool is not connected")
        return await self._pool.execute(query, *args)

    async def fetch(self, query: str, *args: object) -> list[asyncpg.Record]:
        """Fetch multiple rows."""
        if self._pool is None:
            raise RuntimeError("Database pool is not connected")
        return await self._pool.fetch(query, *args)

    async def fetchrow(self, query: str, *args: object) -> asyncpg.Record | None:
        """Fetch a single row or None."""
        if self._pool is None:
            raise RuntimeError("Database pool is not connected")
        return await self._pool.fetchrow(query, *args)

    async def fetchval(self, query: str, *args: object) -> object:
        """Fetch a single value."""
        if self._pool is None:
            raise RuntimeError("Database pool is not connected")
        return await self._pool.fetchval(query, *args)

    @asynccontextmanager
    async def transaction(self) -> AsyncGenerator[asyncpg.Connection, None]:
        """Provide a transactional scope."""
        if self._pool is None:
            raise RuntimeError("Database pool is not connected")
        async with self._pool.acquire() as conn:
            async with conn.transaction():
                yield conn

    # ── Health ───────────────────────────────────────────────────

    async def check_connection(self) -> bool:
        """Return True if the pool is connected and can execute a simple query."""
        try:
            val = await self.fetchval("SELECT 1")
            return val == 1
        except Exception:
            return False


# Global singleton accessible throughout the application.
db = DatabasePool()


async def run_migration(sql: str) -> None:
    """Execute a raw SQL migration file against the database."""
    if db._pool is None:
        await db.connect()
    await db.execute(sql)
