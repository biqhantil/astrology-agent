# Astrology Agent — Agent Guide

Multi-user conversational astrology platform: birth data → Swiss Ephemeris charts → SVG wheel + chat (SSE).

## Stack (truth)

| Layer | Tech | Local port |
|-------|------|------------|
| Backend | FastAPI + aiosqlite + pyswisseph | **8001** |
| Frontend | React 18 + Vite + Tailwind 3 | **5174** |
| LLM | OpenCode Go (`deepseek-v4-flash`) | `OPENCODE_API_KEY`, base `https://opencode.ai/zen/go/v1` |
| Auth | JWT; `AUTH_DEV_MODE_ENABLED=true` preset user | |
| Deploy | docker-compose: backend + nginx | 80 |

Ports **8000/5173** are used by OmniCanvas — do not bind them here.

Deep product/spec docs: `.meta/SPEC.md`. Agentic refactor plan: `.meta/AGENTIC_REFACTOR_PLAN.md`.

## Commands

```bash
# Install
cd backend && uv sync          # or: uv pip install -r requirements.txt -e .
cd frontend && npm install

# Dev (prefer tmux panes; tee to var/logs/)
cd backend && AUTH_DEV_MODE_ENABLED=true uvicorn app.main:app --reload --port 8001
cd frontend && npm run dev    # proxies /v1 → :8001

# Gate (must stay green)
make validate

# REST scenarios (needs live API)
make validate-scenarios BASE_URL=http://localhost:8001

# Multi-turn chat harness — REAL LLM, no frontend (needs funded OPENCODE_API_KEY)
#   LLM_MODE=live uvicorn app.main:app --port 8001
make validate-harness BASE_URL=http://localhost:8001
#   python -m tests.harness.multi_turn_runner --scenario mt_daily_forecast --timeout 180

# Docker
make up / make down
```

## Module map

### Backend (`backend/app/`)

| Path | Role |
|------|------|
| `main.py` | App factory, CORS, `/v1/health`, router mount |
| `config.py` | Pydantic settings (SQLITE_PATH, JWT, AUTH_DEV_*, OPENCODE_*) |
| `database.py` | aiosqlite pool + startup migrations |
| `core/auth.py` | JWT mint/verify, `require_user`, dev preset |
| `core/deps.py` | `get_conn` |
| `core/sse_manager.py` | In-process SSE queues (`register`/`publish`) |
| `routers/*.py` | HTTP domains (**schemas colocated in same file**) |
| `astro_engine/` | `compute_chart()` façade; ephemeris, aspects, serializers(+dignity), transit, synastry, life_phases |
| `llm/` | `chat_completion`, `build_system_prompt`, `TOOL_DEFINITIONS`, `execute_tool` |

**API prefixes (stable):** `/v1/auth`, `/v1/me`, `/v1/me/profile`, `/v1/charts`, `/v1/synastry`, `/v1/conversations`, `/v1/stream`.

### Frontend (`frontend/src/`)

| Path | Role |
|------|------|
| `components/Chart/ZodiacWheel.tsx` | **Deep** SVG wheel (segments, planets, aspects, constellations, center) |
| `components/Chart/ChartController.tsx` | View modes + data wiring |
| `components/Chart/ChartDetailPanel.tsx` | Side panel placements/aspects |
| `components/Chat/ChatPanel.tsx` | **Deep** chat UI (list + bubbles + input wiring) |
| `components/Chat/ChatInput.tsx` | Text input |
| `components/Chat/PresetPromptChips.tsx` | Quick prompts |
| `chat/session.ts` | SSE transport + session helpers |
| `context/*` | Auth, Chart, SSE React providers |
| `hooks/useConversation.ts` | Conversation lifecycle + send |
| `hooks/useAuth.ts` | Auth helpers |
| `api/client.ts` | Typed fetch + JWT headers |
| `components/Profile/BirthProfileForm.tsx` | Onboarding form |
| `types/` | Shared TS types mirroring API |

## SSE event catalog

| Event | Direction | Purpose |
|-------|-----------|---------|
| `chat.delta` | server→client | Token stream |
| `chat.done` | server→client | Turn complete |
| `chat.tool_call` | server→client | Tool invocation notice |
| `chart.data` | server→client | Full chart payload for wheel |
| `transit.data` | server→client | Transit snapshot |
| `synastry.data` | server→client | Compatibility payload |
| `component.render` | server→client | Named UI component request |
| `session.status` | server→client | Connection/session state |
| `error` | server→client | Recoverable error message |

## i18n (frontend)

- Locales: **`en-US`** (default), **`pt-BR`**
- Storage key: `astro_locale` in `localStorage`
- Catalog: `frontend/src/i18n/messages/{en-US,pt-BR}.ts`
- Hook: `useI18n()` → `{ locale, setLocale, t, formatDate, bcp47 }`
- Language switcher in `TopBar`

## Conventions

- **Named exports** preferred on new FE code; existing defaults OK until touched.
- **No ORM** — SQL in routers/`database.py`; no `app/models` package.
- **Do not change `/v1` paths** without updating scenarios + FE client.
- **Deep modules** — merge co-changing files; avoid new DI/event-bus layers.
- Read before write. One phase gate: `make validate`.

## Env (local)

```bash
# backend/.env or export
SQLITE_PATH=data/astrology.db
AUTH_DEV_MODE_ENABLED=true
JWT_SECRET_KEY=dev-secret-at-least-32-bytes-long!!
OPENCODE_API_KEY=          # optional for unit tests; required for live chat
```
