"""Shared FastAPI dependencies: database session, pagination, etc."""

from __future__ import annotations

from typing import AsyncGenerator

from app.database import db


async def get_conn():
    """Yield the DatabasePool singleton for the current request.

    Usage::

        @router.get("/items")
        async def list_items(conn = Depends(get_conn)):
            ...
    """
    if db._conn is None:
        raise RuntimeError("Database is not connected — did the app start correctly?")
    yield db
