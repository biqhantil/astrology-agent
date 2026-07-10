# Agentic baseline — Astrology Agent

> Measured: 2026-07-09  
> Principles: `~/principles/agentic-coding.md`  
> Companion plan: `.meta/AGENTIC_REFACTOR_PLAN.md`

## Why this exists

AI coding agents pay **per file read** (latency + context). Layouts that feel fine in an IDE can still be expensive when every hop is a tool call. This document captures the measured state before any agentic refactor so later phases can re-measure and prove progress.

---

## Snapshot metrics

| Metric | Value |
|--------|------:|
| Backend `app/` Python modules | 42 |
| Frontend `src/` TS/TSX modules | ~40 |
| Backend LOC (app) | ~6.9k |
| Frontend LOC (src) | ~4.5k |
| Test / scenario Python LOC | ~5.7k |
| Empty / placeholder dirs | `app/models/` (5 LOC stub only) |
| Root `AGENTS.md` | **Missing** (moved to `.meta/AGENTS.md`) |
| Single validate gate | **Missing** (`make test` still Postgres/docker-oriented) |

### Largest files (agent “hot” reads)

| File | LOC | Role |
|------|----:|------|
| `frontend/.../BirthProfileForm.tsx` | 563 | Onboarding UI |
| `backend/app/database.py` | 531 | SQLite pool + migrations |
| `backend/app/llm/tools.py` | 519 | Tool schema + execution |
| `backend/app/routers/messages.py` | 517 | Chat + LLM + SSE publish |
| `backend/app/astro_engine/life_phases.py` | 458 | Life phase calc |
| `backend/tests/scenario_runner.py` | 1315 | Harness (keep deep) |

---

## Files-per-feature (agent cost proxy)

Rough count of distinct modules an agent must open to implement or debug a feature end-to-end:

| Feature | Typical files | Assessment |
|---------|--------------:|------------|
| Zodiac wheel visual change | 6–9 Chart/* + 3 utils + types | **High** — pure co-read cluster |
| Chat send + stream tokens | 5 Chat/* + hooks + contexts + api/sse + messages router + llm/* + sse_manager | **Very high** |
| Natal chart API change | router + schema + astro_engine (3–5) + serializers | **Medium–high** |
| Auth / JWT | auth router + schema + core/auth + frontend useAuth + AuthContext + client | **Medium–high** |
| Birth profile | router + schema + form (563) + chart auto-calc path | **Medium** |
| Transit / synastry / phases | router + schema + engine module (good 1:1) | **OK** if schema co-located |

**Target after refactor:** ≤3 files for wheel edits; ≤4 for chat stream path; ≤2 for a single domain API (router+schema collocated or domain package).

---

## Co-read / co-change clusters

### C1 — Chart SVG stack (highest frontend leverage)

Always loaded together for any wheel work:

```
ZodiacWheel → SignSegment, PlanetMarker, AspectLine,
              ConstellationLines, GeometricCenter
           → utils/coordinates, glyphs, aspectColors
           → types/chart
```

- **9 Chart components** (~886 LOC) + **3 utils** (~340 LOC) + chart types.
- `HouseCuspLine.tsx` is **orphaned** (not imported by ZodiacWheel after redesign) — dead weight still in tree.
- `ChartController` + `ChartDetailPanel` co-change with mode tray, not pure SVG internals.

### C2 — Chat + SSE session stack

```
POST messages → llm/{client,prompts,tools} → sse_manager.publish
GET stream    → sse_manager.register
Frontend: api/sse + useSSE + SSEContext + useConversation
          + ChatPanel/MessageList/MessageBubble/ChatInput
```

- Backend chat path already concentrated in `messages.py` (good).
- Frontend scatters the same concern across **api / hooks / context / components** (4 layers for one stream).

### C3 — Schema ↔ router 1:1 pairing

Every domain API is split across two directories:

| Router | Schema |
|--------|--------|
| `auth.py` | `auth.py` |
| `birth_profiles.py` | `birth_profile.py` |
| `charts.py` | `chart.py` |
| `conversations.py` | `conversation.py` |
| `messages.py` | `message.py` |
| `synastry.py` | `synastry.py` |
| `transits.py` | `transit.py` |
| `life_phases.py` | `life_phase.py` |
| `me.py` | `user.py` |

Adding one field always means **2 tool calls minimum** before logic. Schemas are small (most &lt;130 LOC) — classic shallow split.

### C4 — Astro engine pipeline (already deeper)

```
compute_chart()  [public barrel in __init__.py]
  → ephemeris → aspects → serializers(+dignity)
transit / synastry / life_phases sit beside pipeline
```

- **Keep** the deep `compute_chart()` façade — good agent API.
- `dignity.py` only consumed by serializers (+ unit tests) — merge candidate into serializers or aspects package interior.
- Transit/synastry/life_phases are legitimately separate deep modules; do not force-merge into one god file.

### C5 — LLM package

```
messages router → client + prompts + tools
tools → astro_engine (compute_chart, transit, synastry, life_phases)
```

- Three files always read for any tool/prompt change.
- `tools.py` (519 LOC) mixes JSON Schema definitions with DB/engine execution — deepen *inside* the file or split only if each half has a stable public surface.

---

## Patterns that help / hurt agents here

| Pattern | Status | Note |
|---------|--------|------|
| Explicit imports, short chains | Good | FastAPI routers import engine/schemas directly |
| Heavy DI / AOP | Absent | Prefer keeping it that way |
| Event-driven without map | Mild pain | SSE events; document event catalog in AGENTS |
| Empty `models/` ORM layer | Noise | Delete or document “no ORM” |
| Default vs named exports | Mixed FE | Prefer named exports for greppability |
| Documented barrels | Partial | `astro_engine/__init__.py` good; FE types barrel thin |
| Root AGENTS.md | **Gap** | Agents start in `.meta` or re-explore |
| `make validate` | **Gap** | No one-command green bar for local SQLite |
| Makefile / README truth | **Drift** | Still document Postgres, Redis, docker-only tests |
| conftest comments | Drift | Mentions PostgreSQL; runtime is SQLite |

---

## Doc inventory (context capture)

| Path | Purpose | Agent priority |
|------|---------|----------------|
| `.meta/AGENTS.md` | Product vision (short) | Promote to root + expand |
| `.meta/SPEC.md` | Full technical spec (~970 LOC) | Archive-ish; module map supersedes for day-to-day |
| `.meta/IMPLEMENTATION_PLAN.md` | 8-week original plan | Historical |
| `.meta/BUILD_PHASE3.md` | SSE/LLM build order | Done-ish; historical |
| `.meta/DB_MIGRATION.md` | PG → SQLite rationale | Keep until Makefile/README fixed |
| `.meta/DOCKERIZE.md` | Container notes | Keep for deploy |
| `.meta/workflow/*` | Session progress / handoff / todo | Living |
| `backend/tests/ENHANCE_TESTING.md` | Harness metrics backlog | Align with principles harness docs |
| `~/principles/*` | Universal agent workflow | Apply, don’t fork blindly |

### Port / stack truth (from handoffs + code)

| Concern | Truth |
|---------|--------|
| Backend | FastAPI + aiosqlite, local **8001** |
| Frontend | Vite React 18 + Tailwind 3, local **5174** |
| OmniCanvas conflict | 8000 / 5173 reserved |
| LLM | OpenCode Go (`deepseek-v4-flash`), SSE token stream |
| Ephemeris | pyswisseph via `astro_engine` |
| Auth | JWT; `AUTH_DEV_MODE_ENABLED` preset user |
| Deploy | docker-compose: backend + nginx (not PG/Redis) |

---

## Test surface

| Kind | Location | Notes |
|------|----------|-------|
| Unit / API | `tests/test_*.py` | Auth, charts engine, transits, synastry, life_phases, health |
| Scenarios | `tests/scenarios/scenario_*.py` | Multi-step API workflows + stress |
| Runner | `scenario_runner.py` | JSONL metrics; enhance plan in ENHANCE_TESTING.md |
| Frontend | No unit suite; Playwright dep present, not wired as gate |

**Gate requirement for refactor:** every phase must leave backend tests green. Frontend: `tsc --noEmit` + `vite build` until a real FE test suite exists.

---

## Non-goals (carry into plan)

- Do not introduce DI containers, event buses, or deep inheritance.
- Do not split large files into 20 micro-files (classitis).
- Do not rewrite FastAPI routing prefixes mid-flight (clients + scenarios depend on `/v1/...`).
- Do not re-Postgres until product needs multi-instance SSE/DB.
- Do not expand product features inside refactor phases unless blocking green tests.

---

## Re-measure checklist (end of each phase)

```text
[ ] File count backend app/ / frontend src/
[ ] Files-per-feature for wheel, chat, one domain API
[ ] Largest 10 files (LOC)
[ ] Root AGENTS.md module map updated
[ ] make validate (or documented equivalent) green
[ ] Append one line to .meta/workflow/progress.md
```

---

## After R0–R8 (2026-07-09 / 2026-07-10)

| Metric | Before | After |
|--------|-------:|------:|
| Backend `app/` modules | 42 | ~33 (schemas colocated; models removed; dignity re-export only) |
| Chart pure-SVG source files | 9 | **1** (`ZodiacWheel.tsx`) + Controller + DetailPanel |
| Chat UI files (list/bubble/panel) | 5 | **3** (ChatPanel deep + Input + Presets) |
| SSE transport | `api/sse` + `useSSE` + context | `chat/session.ts` + thin context |
| Root `AGENTS.md` | missing | **present** |
| `make validate` | missing / docker-PG | **unit + tsc + vite build** |
| Unit tests | 121 | **121 passed** |
| Scenario E2E | partial fails | **9/9 scenarios, 101/101 turns** |

### Files-per-feature (after)

| Feature | Files |
|---------|------:|
| Wheel visual | 1 (`ZodiacWheel.tsx`) + utils/types if needed |
| Domain API field | 1 router module (schemas colocated) |
| Chat stream protocol | `chat/session.ts` + `SSEContext` + backend stream/messages |

### Bonus product fixes (for green E2E)

- `GET /v1/charts` list endpoint
- Chart ownership isolation (404 for non-owners)
- House `degree` alias (`computed_field`)
- Future `birth_date` rejected (422)
- Transit date range validated before chart lookup
