# DB Migration: PostgreSQL → SQLite

## Why
The app is single-user (anon auth) and doesn't need a full PG server. SQLite eliminates the DB dependency entirely.

## What to Do

### 1. Install deps
```
pip install aiosqlite
```

### 2. Rewrite backend/app/database.py
Replace the asyncpg pool with aiosqlite. Keep the same public interface:
- `db.connect()` - open SQLite file at a configurable path (default: data/astrology.db)
- `db.disconnect()` - close connection
- `db.execute(query, *args)` - execute write query
- `db.fetch(query, *args)` - return list of rows (list of dicts or Record-like objects)
- `db.fetchrow(query, *args)` - return single row or None
- `db.fetchval(query, *args)` - return single value
- `db.check_connection()` - return True/False
- `db.transaction()` - context manager for transactions

Each row returned should behave like asyncpg.Record (support `row["column"]` and `row.column` access). Use `sqlite3.Row` or wrap with a simple class.

### 3. Update backend/app/config.py
- Change POSTGRES_* settings to SQLITE_*
- Add `SQLITE_PATH: str = "data/astrology.db"`
- Remove/deprecate the PG connection string property

### 4. Update backend/app/main.py
- Remove the POSTGRES env vars from the CORS_ORIGINS or any unrelated legacy

### 5. Update SQL for SQLite compatibility
SQLite doesn't support:
- `gen_random_uuid()` → use `python UUID` or sqlite `(lower(hex(randomblob(16))))`
- `UUID` type → store as TEXT
- `DECIMAL` → use REAL
- `INTERVAL` → use TEXT or INTEGER (seconds)
- `GENERATED ALWAYS AS ... STORED` → remove or simplify
- `JSONB` → use TEXT (JSON stored as text)
- `TIMESTAMPTZ` → use TEXT (ISO format)
- `BIGSERIAL` → use INTEGER PRIMARY KEY AUTOINCREMENT
- `SMALLINT` → use INTEGER
- Custom CHECK constraints → keep but test

### 6. Create the DB on startup
In `db.connect()`, read the SQL migration files and execute them to create tables if they don't exist. The migration files are at `backend/migrations/001_core_tables.sql` and `002_remaining_tables.sql`.

Port these SQL files to SQLite-compatible syntax. The simplest approach: create a new migration file `backend/migrations/003_sqlite.sql` that contains ALL tables in SQLite-compatible DDL.

### 7. Update UUID handling
- In auth.py and other routers, generate UUIDs in Python: `uuid.uuid4()`
- Pass them as strings to SQLite
- Return them as UUID objects from queries

### 8. Update ENV
Create a `.env.sqlite` or update `.env` with:
```
DATABASE_URL=sqlite:///data/astrology.db
```
Or just use SQLITE_PATH.

## Implementation Order
1. Install aiosqlite
2. Create migration file 003_sqlite.sql with all tables ported to SQLite syntax
3. Rewrite database.py for aiosqlite
4. Update config.py 
5. Test: start backend, run E2E test (auth → conversation → message)
6. Commit and push

## Key Design Decision
Keep the DatabasePool interface IDENTICAL so NO router code needs to change. The only thing that changes is the underlying implementation of how execute/fetch/fetchrow/fetchval work.

For UUID columns: store as TEXT in SQLite, convert to/from Python UUID objects in the pool wrapper.
