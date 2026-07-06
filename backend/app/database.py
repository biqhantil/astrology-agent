"""Async SQLite database management via aiosqlite.

Replaces the previous asyncpg PostgreSQL pool with a single aiosqlite
connection.  The public interface (DatabasePool) is kept identical so
that no router code needs to change.
"""

from __future__ import annotations

import json
import os
import re
import uuid
from contextlib import asynccontextmanager
from datetime import date, datetime, time, timezone
from decimal import Decimal
from typing import Any, AsyncGenerator

import aiosqlite

from app.config import settings

# ── Columns stored as JSON text that should be auto-parsed ─────

_JSON_COLUMNS = frozenset({
    "raw_ephemeris",
    "metadata",
    "score_summary",
    "transit_events",
    "dominant_transits",
    "payload",
    "house_overlay",
    "tool_calls",
})


# ── UUID detection helpers ─────────────────────────────────────

def _looks_like_uuid(s: str) -> bool:
    """Check whether a string matches standard UUID format (8-4-4-4-12)."""
    if len(s) == 36 and s[8] == "-" and s[13] == "-" and s[18] == "-" and s[23] == "-":
        # Quick check: groups of hex digits separated by dashes
        parts = s.split("-")
        return all(
            len(p) == n and all(c in "0123456789abcdefABCDEF" for c in p)
            for p, n in zip(parts, (8, 4, 4, 4, 12))
        )
    # Also accept 32-char hex without dashes
    if len(s) == 32:
        return all(c in "0123456789abcdefABCDEF" for c in s)
    return False


def _should_convert_uuid(col_name: str, value: str) -> bool:
    """Return True if the column stores a UUID and the value looks like one."""
    if col_name == "id" or col_name.endswith("_id"):
        return _looks_like_uuid(value)
    return False


# ── Row class ───────────────────────────────────────────────────

class Row:
    """Row object supporting both dict (``row["col"]``) and attribute access.

    - JSON columns are auto-parsed from text to Python dicts/lists when read.
    - TEXT columns storing UUIDs (``id`` / ``*_id`` columns) are auto-converted
      to ``uuid.UUID`` objects.
    """

    __slots__ = ("_data",)

    def __init__(self, data: dict[str, Any]) -> None:
        parsed: dict[str, Any] = {}
        for k, v in data.items():
            if v is None:
                parsed[k] = None
            elif k in _JSON_COLUMNS and isinstance(v, str):
                try:
                    parsed[k] = json.loads(v)
                except (json.JSONDecodeError, TypeError):
                    parsed[k] = v
            elif isinstance(v, str) and _should_convert_uuid(k, v):
                parsed[k] = uuid.UUID(v)
            else:
                parsed[k] = v
        object.__setattr__(self, "_data", parsed)

    # ── Dict-like access ────────────────────────────────────────

    def __getitem__(self, key: str) -> Any:
        return object.__getattribute__(self, "_data")[key]

    def __setitem__(self, key: str, value: Any) -> None:
        object.__getattribute__(self, "_data")[key] = value

    def __contains__(self, key: object) -> bool:
        return key in object.__getattribute__(self, "_data")

    def __iter__(self):
        return iter(object.__getattribute__(self, "_data"))

    def __len__(self) -> int:
        return len(object.__getattribute__(self, "_data"))

    def get(self, key: str, default: Any = None) -> Any:
        return object.__getattribute__(self, "_data").get(key, default)

    def keys(self):
        return object.__getattribute__(self, "_data").keys()

    def values(self):
        return object.__getattribute__(self, "_data").values()

    def items(self):
        return object.__getattribute__(self, "_data").items()

    # ── Attribute access ────────────────────────────────────────

    def __getattr__(self, name: str) -> Any:
        """Support ``row.column_name`` access."""
        if name.startswith("_"):
            raise AttributeError(name)
        try:
            return object.__getattribute__(self, "_data")[name]
        except KeyError:
            raise AttributeError(f"Row has no column '{name}'") from None

    def __repr__(self) -> str:
        return repr(object.__getattribute__(self, "_data"))


# ── Query helpers ───────────────────────────────────────────────

_PARAM_RE = re.compile(r"\$(\d+)")

# PostgreSQL type casts that should be stripped for SQLite
_PG_CAST_RE = re.compile(
    r"::(?:"
    r"text|timestamptz|timestamp|interval|date|time|uuid"
    r"|jsonb|decimal|bigint|smallint|boolean"
    r"|int|int2|int4|int8|float4|float8|numeric"
    r")\b",
    re.IGNORECASE,
)


def _convert_query(query: str) -> str:
    """Strip PostgreSQL type casts (``::text``, ``::timestamptz``, etc.).

    ``$1``, ``$2`` style placeholders are kept as-is — Python's sqlite3
    supports them natively (they are treated as named parameters).
    """
    return _PG_CAST_RE.sub("", query)


def _convert_params(args: tuple[Any, ...]) -> list[Any]:
    """Convert Python types to SQLite-compatible values.

    - ``UUID``       → ``str``
    - ``dict/list``   → JSON string
    - ``datetime``    → ISO-8601 string
    - ``date``        → ISO-8601 string
    - ``time``        → ISO-8601 string
    - ``bool``        → ``1`` / ``0``
    """
    result: list[Any] = []
    for arg in args:
        if arg is None:
            result.append(None)
        elif isinstance(arg, uuid.UUID):
            result.append(str(arg))
        elif isinstance(arg, bool):
            result.append(1 if arg else 0)
        elif isinstance(arg, (dict, list, tuple)):
            result.append(json.dumps(arg, default=str))
        elif isinstance(arg, datetime):
            result.append(arg.isoformat())
        elif isinstance(arg, date):
            result.append(arg.isoformat())
        elif isinstance(arg, time):
            result.append(arg.isoformat())
        elif isinstance(arg, Decimal):
            result.append(float(arg))
        elif isinstance(arg, (int, float, str, bytes)):
            result.append(arg)
        else:
            # Last resort: try string conversion
            result.append(str(arg))
    return result


# ── DatabasePool ────────────────────────────────────────────────

class DatabasePool:
    """Singleton-style wrapper around an aiosqlite connection.

    Public interface mirrors the previous asyncpg pool:

    - ``connect()`` / ``disconnect()``
    - ``execute(query, *args)``
    - ``fetch(query, *args)``
    - ``fetchrow(query, *args)``
    - ``fetchval(query, *args)``
    - ``transaction()``   (context manager)
    - ``check_connection()``
    """

    def __init__(self) -> None:
        self._conn: aiosqlite.Connection | None = None
        self._db_path: str = settings.SQLITE_PATH

    # ── Lifecycle ───────────────────────────────────────────────

    async def connect(self) -> None:
        """Open the SQLite database, enable WAL + foreign keys, and run migrations."""
        if self._conn is not None:
            return

        # Ensure the parent directory exists
        db_dir = os.path.dirname(self._db_path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)

        self._conn = await aiosqlite.connect(self._db_path)
        self._conn.row_factory = aiosqlite.Row

        # Performance & safety pragmas
        await self._conn.execute("PRAGMA journal_mode = WAL")
        await self._conn.execute("PRAGMA foreign_keys = ON")
        await self._conn.execute("PRAGMA busy_timeout = 5000")

        # Register SQL functions that the DDL and queries rely on
        def _gen_uuid() -> str:
            return str(uuid.uuid4())

        def _now() -> str:
            return datetime.now(timezone.utc).isoformat()

        await self._conn.create_function("gen_random_uuid", 0, _gen_uuid)
        await self._conn.create_function("now", 0, _now)

        # ── Run pending migrations ──────────────────────────────
        await self._run_migrations()

    async def disconnect(self) -> None:
        """Close the database connection."""
        if self._conn is None:
            return
        await self._conn.close()
        self._conn = None

    # ── Migrations ──────────────────────────────────────────────

    async def _run_migrations(self) -> None:
        """Execute ``003_sqlite.sql`` to create/update all tables."""
        migration_path = os.path.join(
            os.path.dirname(__file__), "..", "migrations", "003_sqlite.sql"
        )
        migration_path = os.path.abspath(migration_path)

        if not os.path.exists(migration_path):
            return  # No migration file yet — nothing to do

        with open(migration_path, "r", encoding="utf-8") as f:
            sql = f.read()
        # ``executescript`` handles multiple statements in one call
        await self._conn.executescript(sql)
        await self._conn.commit()

    # ── Access ──────────────────────────────────────────────────

    async def execute(self, query: str, *args: object) -> str:
        """Execute a single write query and return a command tag.

        Returns a string like ``"INSERT 0 1"``, ``"DELETE 2"``, etc.
        Auto-commits after the statement (suitable for one-off writes).
        """
        if self._conn is None:
            raise RuntimeError("Database is not connected")
        cursor = await self._conn.execute(
            _convert_query(query), _convert_params(args)
        )
        await self._conn.commit()
        rowcount = cursor.rowcount

        if rowcount < 0:
            return "OK"

        q = query.strip().upper()
        if q.startswith("INSERT"):
            return f"INSERT 0 {rowcount}"
        elif q.startswith("DELETE"):
            return f"DELETE {rowcount}"
        elif q.startswith("UPDATE"):
            return f"UPDATE {rowcount}"
        return "OK"

    async def fetch(self, query: str, *args: object) -> list[Row]:
        """Fetch multiple rows as ``Row`` objects."""
        if self._conn is None:
            raise RuntimeError("Database is not connected")
        cursor = await self._conn.execute(
            _convert_query(query), _convert_params(args)
        )
        rows = await cursor.fetchall()
        if not rows or not cursor.description:
            return []
        columns = [col[0] for col in cursor.description]
        return [Row(dict(zip(columns, row))) for row in rows]

    async def fetchrow(self, query: str, *args: object) -> Row | None:
        """Fetch a single row or ``None``."""
        rows = await self.fetch(query, *args)
        return rows[0] if rows else None

    async def fetchval(self, query: str, *args: object) -> Any:
        """Fetch a single value (first column of the first row)."""
        row = await self.fetchrow(query, *args)
        if row is None:
            return None
        data = object.__getattribute__(row, "_data")
        return next(iter(data.values())) if data else None

    @asynccontextmanager
    async def transaction(self) -> AsyncGenerator["ConnectionWrapper", None]:
        """Provide a transactional scope.

        Yields a ``ConnectionWrapper`` that does **not** auto-commit.
        The context manager commits on success, rolls back on exception.

        Usage::

            async with db.transaction() as conn:
                await conn.execute("INSERT INTO users ...")
                await conn.execute("INSERT INTO profiles ...")
        """
        if self._conn is None:
            raise RuntimeError("Database is not connected")
        await self._conn.execute("BEGIN")
        try:
            yield ConnectionWrapper(self._conn, autocommit=False)
            await self._conn.commit()
        except Exception:
            await self._conn.rollback()
            raise

    # ── Health ──────────────────────────────────────────────────

    async def check_connection(self) -> bool:
        """Return ``True`` if the database is connected and functional."""
        try:
            val = await self.fetchval("SELECT 1")
            return val == 1
        except Exception:
            return False


# ── Connection wrapper (used by ``transaction``) ────────────────

class ConnectionWrapper:
    """Thin wrapper around an aiosqlite connection used inside ``transaction()``.

    Exposes the same ``fetch`` / ``fetchrow`` / ``fetchval`` / ``execute``
    interface, but **does not auto-commit** when ``autocommit=False``
    (the default inside transactions).
    """

    def __init__(self, conn: aiosqlite.Connection, *, autocommit: bool = True) -> None:
        self._conn = conn
        self._autocommit = autocommit

    async def execute(self, query: str, *args: object) -> str:
        """Execute a write query and return a command tag.

        Commits after the statement only if ``autocommit`` is ``True``.
        """
        cursor = await self._conn.execute(
            _convert_query(query), _convert_params(args)
        )
        if self._autocommit:
            await self._conn.commit()
        rowcount = cursor.rowcount
        if rowcount < 0:
            return "OK"
        q = query.strip().upper()
        if q.startswith("INSERT"):
            return f"INSERT 0 {rowcount}"
        elif q.startswith("DELETE"):
            return f"DELETE {rowcount}"
        elif q.startswith("UPDATE"):
            return f"UPDATE {rowcount}"
        return "OK"

    async def fetch(self, query: str, *args: object) -> list[Row]:
        """Fetch multiple rows as ``Row`` objects."""
        cursor = await self._conn.execute(
            _convert_query(query), _convert_params(args)
        )
        rows = await cursor.fetchall()
        if not rows or not cursor.description:
            return []
        columns = [col[0] for col in cursor.description]
        return [Row(dict(zip(columns, row))) for row in rows]

    async def fetchrow(self, query: str, *args: object) -> Row | None:
        """Fetch a single row or ``None``."""
        rows = await self.fetch(query, *args)
        return rows[0] if rows else None

    async def fetchval(self, query: str, *args: object) -> Any:
        """Fetch a single value (first column of the first row)."""
        row = await self.fetchrow(query, *args)
        if row is None:
            return None
        data = object.__getattribute__(row, "_data")
        return next(iter(data.values())) if data else None


# ── Global singleton ────────────────────────────────────────────

db = DatabasePool()

# Alias for backward compatibility with deps.py
SQLiteConnection = ConnectionWrapper
