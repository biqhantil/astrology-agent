# Astrology Agent

Conversational astrology platform: birth data → Swiss Ephemeris natal charts → SVG zodiac wheel + LLM chat over SSE.

## Quick start (local)

```bash
# Backend (port 8001)
cd backend
uv sync   # or create .venv and install deps
AUTH_DEV_MODE_ENABLED=true uvicorn app.main:app --reload --port 8001

# Frontend (port 5174) — proxies /v1 → backend
cd frontend && npm install && npm run dev
```

Open http://localhost:5174. Dev auth auto-logs in when `AUTH_DEV_MODE_ENABLED=true`.

## Validate

```bash
make validate              # unit tests + frontend build
make validate-scenarios    # E2E scenarios (API must be running)
```

## Docker

```bash
cp .env.example .env   # set OPENCODE_API_KEY, BASIC_AUTH_*
make up                # nginx :80 + backend + SQLite volume
```

## Docs

| Doc | Contents |
|-----|----------|
| [AGENTS.md](./AGENTS.md) | Agent landing: stack, module map, commands, SSE events |
| [.meta/SPEC.md](./.meta/SPEC.md) | Full technical specification |
| [.meta/AGENTIC_REFACTOR_PLAN.md](./.meta/AGENTIC_REFACTOR_PLAN.md) | Agentic refactor phases |

## Layout

```
backend/app/     FastAPI, astro_engine, llm, routers
frontend/src/    React UI (Chart, Chat, Profile)
nginx/           Production reverse proxy + static SPA
.meta/           Specs, plans, workflow notes
```
