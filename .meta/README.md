# Astrology Agent

Multi-user conversational astrology platform with real-time SSE streaming, SVG chart rendering, and LLM-driven interpretation.

## Architecture

```
┌──────────────┐     SSE (chart.data, chat.delta)     ┌──────────────┐
│   React 18   │ ◄──────────────────────────────────► │  FastAPI      │
│  (Vite + TS)  │     (EventSource + JWT)             │  + asyncpg    │
│              │                                       │              │
│ ZodiacWheel  │                                       │  Swiss Eph.  │
│ TransitOvrly │                                       │  (pyswisseph)│
│ ChatPanel    │                                       │  LLM (pi.dev)│
└──────────────┘                                       └──────┬───────┘
                                                              │
                                                     ┌────────▼───────┐
                                                     │  PostgreSQL 15 │
                                                     │  + Redis 7     │
                                                     └────────────────┘
```

## Quick Start

```bash
# Start all services
make up

# Or manually:
docker compose up -d

# Run migrations
make migrate

# Seed test data
make seed

# Open API docs
open http://localhost:8000/docs
```

## Project Structure

```
/opt/astrology-agent/
├── backend/                    # FastAPI Python backend
│   ├── app/
│   │   ├── main.py            # App factory + health endpoint
│   │   ├── config.py          # Pydantic settings from env
│   │   ├── database.py        # asyncpg connection pool
│   │   ├── models/            # ORM models (Phase 2)
│   │   ├── schemas/           # Pydantic schemas (Phase 2)
│   │   ├── routers/           # API route handlers (Phase 2)
│   │   ├── core/              # Auth, rate limiting (Phase 2)
│   │   ├── astro_engine/      # Ephemeris calculations (Phase 2)
│   │   └── llm/               # LLM integration (Phase 2)
│   ├── migrations/            # SQL migration files
│   │   ├── 001_core_tables.sql
│   │   └── 002_remaining_tables.sql
│   ├── tests/                 # Pytest test suite
│   ├── run_migrations.py      # Migration runner
│   ├── seed.py                # Test data seeder
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/                  # React + Vite (Phase 3)
│   └── package.json
├── docker-compose.yml         # Postgres + Redis + API
├── Makefile                   # Developer commands
└── README.md
```

## Database — 12 Tables

| # | Table | Purpose |
|---|-------|---------|
| 1 | `users` | Multi-user root, lightweight auth |
| 2 | `birth_profiles` | Canonical birth data per user (1:1) |
| 3 | `charts` | Astrological snapshots (natal, transit, etc.) |
| 4 | `chart_bodies` | Planetary positions and angles |
| 5 | `chart_houses` | House cusp positions |
| 6 | `chart_aspects` | Intra-chart aspects |
| 7 | `synastry_pairs` | Two-chart compatibility links |
| 8 | `synastry_aspects` | Inter-chart aspects |
| 9 | `transit_snapshots` | Cached transit event windows |
| 10 | `life_phases` | Precomputed life phase timeline |
| 11 | `conversations` | Chat sessions |
| 12 | `messages` | Chat turns with tool payloads |

## Developer Commands

```bash
make up          # Start all services
make down        # Stop all services
make logs        # Follow service logs
make psql        # Open postgres shell
make migrate     # Run pending migrations
make seed        # Seed test data
make test        # Run tests
make lint        # Lint Python code
make db-reset    # Wipe and recreate database
```
