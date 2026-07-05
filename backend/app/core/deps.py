"""Shared FastAPI dependencies: database session, pagination, etc."""

from __future__ import annotations

from typing import AsyncGenerator

from asyncpg import Connection

from app.database import db


async def get_conn() -> AsyncGenerator[Connection, None]:
    """Yield a database connection from the pool.

    Usage::

        @router.get("/items")
        async def list_items(conn: Connection = Depends(get_conn)):
            ...
    """
    if db._pool is None:
        raise RuntimeError("Database pool is not connected — did the app start correctly?")
    async with db._pool.acquire() as conn:
        yield conn
