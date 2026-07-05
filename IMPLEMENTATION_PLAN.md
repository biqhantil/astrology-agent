# Implementation Plan — Astrology Agent (Phase 2)

> **8-week build** · broken into ~2-day chunks · shipping every week  
> Generated: 2026-07-05 · Based on SPEC.md & AGENTS.md

---

## Structure

Each **week** has a clear **ship goal**. Within each week, work is divided into **chunks** (~1–3 working days each, ≈2 days on average). Each chunk produces a concrete, testable artifact: a working API endpoint, a rendered component, a passing test suite.

**Legend:** 🔧 Backend · 🎨 Frontend · 🔗 Integration · 🧪 Test/Polish

---

## Week 1 — Project Foundation & Data Model

> **Ship:** FastAPI project skeleton + all 12 PostgreSQL tables + anonymous JWT auth + health check

### Chunk 1.1 — Scaffold & Schema (2 days)

| Day | Area | Deliverable |
|-----|------|-------------|
| 1 | 🔧 | `fastapi` project with `uvicorn`, `alembic`, `asyncpg`, `pydantic` v2. Directory structure: `app/` (routers, models, schemas, core). `docker-compose.yml` with `postgres:15` + `redis:7`. |
| 1 | 🔧 | Alembic initial migration: `users`, `birth_profiles`, `charts`, `chart_bodies`, `chart_houses`, `chart_aspects` tables with all columns, constraints, indexes from §2.2. |
| 2 | 🔧 | Second migration: remaining tables — `synastry_pairs`, `synastry_aspects`, `transit_snapshots`, `life_phases`, `conversations`, `messages`. |
| 2 | 🧪 | Seed script with one test user + birth profile. Verify all FK relationships, cascade deletes, generated columns. |

**Check:** `alembic upgrade head` runs clean. All tables exist in `psql`. No FK violations on seed.

### Chunk 1.2 — Auth & Health (2 days)

| Day | Area | Deliverable |
|-----|------|-------------|
| 3 | 🔧 | JWT auth module: `POST /v1/auth/anonymous` minting JWTs with `sub=anonymous:<uuid>`. `GET /v1/health`. Middleware extracting `user_id` from Bearer token. |
| 3 | 🧪 | Integration test: `/health` returns 200. `/auth/anonymous` returns JWT. `/me` with valid JWT returns user object. |
| 4 | 🔧 | `GET /v1/me` + `PUT /v1/me` endpoints. Auto-provision user row on first anonymous JWT mint. |
| 4 | 🔧 | Redis session pub/sub skeleton — `redis_client` dependency, basic `set/get` for rate limiter counter. |

**Check:** `curl /v1/auth/anonymous` returns JWT. `curl -H "Authorization: Bearer <jwt>" /v1/me` returns user. Rate limiter rejects > limit.

### Chunk 1.3 — Wrap & Test (1 day)

| Day | Area | Deliverable |
|-----|------|-------------|
| 5 | 🧪 | Full integration test suite for auth flow: anonymous → JWT → `/me` → update display_name. Test invalid/expired JWT rejection. |
| 5 | 🧪 | CI config (GitHub Actions or local `Makefile`): `make test` runs `pytest`, `make lint` runs `ruff`, `make db-up` starts Postgres. |

**Week 1 Ship:** Project boots with `docker compose up`. All DB migrations applied. JWT auth round-trip works. Tests pass.

---

## Week 2 — Chart Calculation Engine

> **Ship:** Natal chart computation API returning full bodies + houses + aspects serialized per SPEC schema

### Chunk 2.1 — Swiss Ephemeris Integration (2 days)

| Day | Area | Deliverable |
|-----|------|-------------|
| 6 | 🔧 | Install `pyswisseph` + `immanuel` in Docker. Write `app/astro_engine/__init__.py` — thin wrapper: `compute_chart(dt_utc, lat, lon, house_system='P', bodies=[...])`. |
| 6 | 🔧 | **Step 1–2 of pipeline (§5.2):** Time normalization (UTC → Julian Day via `swisseph.julday`). Ephemeris positions for all requested bodies (longitude, speed, latitude, retrograde flag). |
| 7 | 🔧 | **Step 2 continued:** House cusps via `swisseph.houses`. Ascendant, MC, DSC, IC. Nodes, Lilith, Part of Fortune. Return raw dict matching `raw_ephemeris` JSONB shape. |
| 7 | 🧪 | Unit test against known birth chart (e.g., Einstein: Mar 14 1879, 11:30, Ulm). Verify Sun in Pisces, Moon in Virgo, Asc in Libra. Hard-code ±0.5° tolerance. |

**Check:** `compute_chart()` for a known person returns correct Sun/Moon/Asc. Raw ephemeris dict is well-structured.

### Chunk 2.2 — Aspect & Dignity Engine (2 days)

| Day | Area | Deliverable |
|-----|------|-------------|
| 8 | 🔧 | **Step 3 (§5.2):** Aspect engine — iterate body pairs, compute angular separation, test against established orbs (§10.C), classify major/minor, determine applying/separating via speed differential. |
| 8 | 🔧 | **Step 4 (§5.2):** Dignity engine — domicile/exaltation/detriment/fall lookup per body-sign matrix (§10.D). Attach `dignity` field to each body. |
| 9 | 🔧 | **Step 5 (§5.2):** Serialization layer — transform raw ephemeris + aspects + dignities into `chart_bodies[]`, `chart_houses[]`, `chart_aspects[]` matching SPEC §3.2 GET response shape. |
| 9 | 🧪 | Test aspect detection: verify Moon trine Sun (orb 2.1°) is caught. Test dignity: Sun in Leo → "domicile", Moon in Capricorn → "detriment". |

**Check:** Aspect engine finds all Ptolemaic aspects for test chart. Dignity assignments correct. Serialized output matches OpenAPI spec.

### Chunk 2.3 — Chart API Endpoints (1 day)

| Day | Area | Deliverable |
|-----|------|-------------|
| 10 | 🔧 | `POST /v1/charts` — accepts chart_type, calculation_date, location, options → calls `astro_engine.compute_chart()` → persists to `charts`, `chart_bodies`, `chart_houses`, `chart_aspects` → returns full chart JSON. |
| 10 | 🔧 | `GET /v1/charts/:id` — fetches chart with joined bodies/houses/aspects. `GET /v1/charts/:id/summary` — lightweight (just signs, key aspects). |
| 10 | 🧪 | Integration test: POST → receive chart_id → GET returns identical body positions. Verify NaN/Inf handling. |

**Week 2 Ship:** `POST /v1/charts` with a birth datetime returns full chart JSON. Aspect detection works. Dignities assigned. Tests cover known chart.

---

## Week 3 — Frontend Skeleton & SSE Streaming

> **Ship:** React app with SSE connected to backend, receiving chart.data events and rendering a ZodiacWheel

### Chunk 3.1 — React Project Setup (2 days)

| Day | Area | Deliverable |
|-----|------|-------------|
| 11 | 🎨 | `npm create vite@latest frontend -- --template react-ts`. TailwindCSS v4. `src/types/` mirroring all backend API types (`Chart`, `ChartBody`, `ChartHouse`, `ChartAspect`, `TransitSnapshot`, etc.). |
| 11 | 🎨 | `src/api/client.ts` — typed fetch wrapper: `get(endpoint)`, `post(endpoint, body)`. JWT storage in `sessionStorage`. Base URL from env. |
| 12 | 🔗 | `src/hooks/useSSE.ts` — connect to `/v1/stream?conversation_id=...` with JWT in header (polyfill via `EventSource` with `fetch` for header support). Parse events: `chat.delta`, `chart.data`, `component.render`, `session.status`. |
| 12 | 🧪 | Test SSE connection with a simple backend event emitter. Verify events dispatched to React context. |

**Check:** Vite dev server runs. SSE connects to backend. Events flow into React context.

### Chunk 3.2 — ZodiacWheel SVG Component (2 days)

| Day | Area | Deliverable |
|-----|------|-------------|
| 13 | 🎨 | `ZodiacWheel` component (§4.2): SVG container, 12 sign segments with element-colored arcs. Sign labels (glyphs). Degree tick marks. |
| 13 | 🎨 | Body layer — `PlanetMarker` at polar coordinates. SVG glyphs for all 19 bodies. Degree label. Retrograde badge (small "℞" or underline). |
| 14 | 🎨 | House ring — `HouseCuspLine` × 12, house numbers. Aspect layer — SVG lines between body positions (color-coded: blue=trine, red=square, green=sextile, purple=conjunction, orange=opposition). |
| 14 | 🧪 | Storybook-style test: render ZodiacWheel with known chart data, snapshot test. Verify planet at correct polar angle for Sun=84.5° (Gemini ~84°, should be ~84° around wheel). |

**Check:** ZodiacWheel renders with all planets, houses, aspects on a test chart. Clicking a body logs its key. Snapshot matches.

### Chunk 3.3 — SSE → Chart Rendering Pipeline (1 day)

| Day | Area | Deliverable |
|-----|------|-------------|
| 15 | 🔗 | Backend: SSE `/v1/stream` endpoint. On `chart.data` event emit, push full chart payload as SSE event. Wire `POST /v1/charts` to return chart + optionally emit over SSE for active conversation. |
| 15 | 🔗 | Frontend: `ChartWorkspace` container listens to `chart.data` events, deserializes, mounts `ZodiacWheel` with payload. `ChartController` state machine picks view type from `render_mode`. |
| 15 | 🧪 | End-to-end: start SSE, POST new chart, verify `chart.data` event fires, ZodiacWheel appears in browser. |

**Week 3 Ship:** SSE connection → POST chart → chart appears as SVG wheel in browser. Two-way data flow verified.

---

## Week 4 — Chat MVP with LLM Integration

> **Ship:** Full conversational loop: user types message → LLM streams chat.delta → tool_call renders chart → chart appears

### Chunk 4.1 — Conversations API & ChatPanel (2 days)

| Day | Area | Deliverable |
|-----|------|-------------|
| 16 | 🔧 | `POST /v1/conversations`, `GET /v1/conversations`, `GET /v1/conversations/:id`, `POST /v1/conversations/:id/messages`. Messages stored with role, content, tool info. |
| 16 | 🎨 | `ChatPanel` component: `MessageList` (virtualized via `react-window` for >100 messages), `MessageBubble` (markdown rendering via `react-markdown`), `ChatInput` (auto-grow textarea + send). |
| 17 | 🎨 | `PresetPromptChips` component — row of quick-tap buttons: "Daily forecast", "Weekly forecast", "My chart", "Saturn return", "Compatibility". `BirthDataPrompt` shown if user lacks birth_profile. |
| 17 | 🔗 | Wire chat UI to backend: send message → POST to conversations/:id/messages → receive chat.delta via SSE. |

**Check:** Sending a message stores it. SSE streams response. Messages appear in chat bubble.

### Chunk 4.2 — LLM Integration with pi.dev SDK (2 days)

| Day | Area | Deliverable |
|-----|------|-------------|
| 18 | 🔧 | Integrate `pi-dev` SDK: `app/llm/client.py`. Function `stream_chat(messages, tools)` yields token deltas. System prompt template from §6.1 injected with chart context. |
| 18 | 🔧 | **Context injection:** When conversation has `chart_context_id`, load chart, serialize compact context block (§6.1), prepend to system prompt. |
| 19 | 🔧 | **Tool handling (§6.2):** Parse LLM tool calls from response. Map to backend functions (compute transits, fetch synastry). Emit `chat.tool_call` + `chart.data` / `component.render` events over SSE. |
| 19 | 🔗 | **Streaming flow (§6.3):** Client SSE message → backend orchestrates LLM → streams `chat.delta` tokens → tool calls pause stream, execute, emit `chart.data`, resume. |

**Check:** "Show my chart" in chat → LLM emits `render_natal_chart` tool call → backend returns chart data → ZodiacWheel mounts. Streaming text appears word-by-word.

### Chunk 4.3 — Birth Profile Onboarding (1 day)

| Day | Area | Deliverable |
|-----|------|-------------|
| 20 | 🔧 | `PUT /v1/me/birth-profile` — upsert birth data. On save, async-queue natal chart calculation (`POST /v1/charts` internally with chart_type=natal). `GET /v1/me/birth-profile`. `POST /v1/me/birth-profile/validate` — geocode + tz resolution. |
| 20 | 🎨 | Birth data collection form: date picker, time input (optional), location autocomplete (Nominatim or OpenCage), timezone selector. Validates + shows preview (sun sign, rising if time known). |
| 20 | 🔗 | On birth profile save → auto-calculate natal chart → push `chart.data` via SSE → ZodiacWheel renders. Chat panel shows "Your chart is ready!" message. |

**Check:** New user lands, sees birth data form, fills it, sees their natal chart render in the workspace.

**Week 4 Ship:** Full chat loop. Birth data collection → natal chart renders. Chat with LLM streams responses. Tool calls produce chart renders.

---

## Week 5 — Transit Calculation & Timeline

> **Ship:** Transit engine working. TransitTimeline and TransitOverlay components rendering. "Daily forecast" preset produces transit chart.

### Chunk 5.1 — Transit Calculation Engine (2 days)

| Day | Area | Deliverable |
|-----|------|-------------|
| 21 | 🔧 | `astro_engine/compute_transits(natal_chart_id, date_from, date_to, granularity)` — §5.3 pipeline. Iterate date range, compute transiting positions, compare to natal, record events. |
| 21 | 🔧 | Station detection: track speed sign changes → detect retrograde/direct stations. Sign ingress detection. House ingress (requires natal houses). |
| 22 | 🔧 | `POST /v1/charts/:id/transits` — compute + cache transit snapshot. `GET /v1/charts/:id/transits?from=...&to=...` — retrieve cached. Caching with `expires_at` TTL (24h for past/future, 1h for today). |
| 22 | 🧪 | Test transit events for known date: verify Saturn opposition Sun matches expected date range, orb, and exact datetime. Test station detection: Mercury retrograde shadow periods. |

**Check:** Transit engine finds known transit events. Cache hit/miss works. API returns correct shape.

### Chunk 5.2 — TransitTimeline Component (2 days)

| Day | Area | Deliverable |
|-----|------|-------------|
| 23 | 🎨 | `TransitTimeline` (§4.2): horizontal time axis (scalable from weeks to years). `TransitBarRow` per major transiting body (Saturn, Uranus, Neptune, Pluto, Jupiter). `TransitSegment` colored bands with exact date markers. |
| 23 | 🎨 | Retrograde shading bands. Tooltip popovers on click with transit details. `DateScrubber` — radial or linear selector for date navigation. |
| 24 | 🎨 | `TransitOverlay` (§4.2): composes two `ZodiacWheel` instances — inner natal, outer transit (dashed ring, different glyph palette). Transit aspect lines crossing between rings. |
| 24 | 🔗 | Wire `transit.data` SSE event → TransitOverlay mounts. Wire preset "Daily forecast" → POST /charts/:id/transits → emit transit.data → TransitTimeline renders. |

**Check:** Timeline renders with transit bands. Bi-wheel overlay shows transiting planets outside natal. Date scrubber updates positions.

### Chunk 5.3 — Daily/Weekly/Monthly Presets (1 day)

| Day | Area | Deliverable |
|-----|------|-------------|
| 25 | 🔗 | Wire preset prompt chips: "Daily forecast" → LLM prompt "Analyze today's transits for {NAME}" with transit context injected. "This week" → 7-day transit window. "This month" → 30-day window. |
| 25 | 🎨 | `MiniZodiacWheel` inline component (200px) for embedding in message bubbles alongside transit analysis text. |
| 25 | 🧪 | E2E test: click "Daily forecast" → chat shows transit analysis → transit timeline renders below message. |

**Week 5 Ship:** "What's happening this week?" → transit timeline renders + text analysis. Bi-wheel overlay shows current sky vs natal.

---

## Week 6 — Life Phases & Aspect Table

> **Ship:** Life phase timeline rendering. Year-ahead trajectory analysis. AspectTable matrix view.

### Chunk 6.1 — Life Phase Engine (2 days)

| Day | Area | Deliverable |
|-----|------|-------------|
| 26 | 🔧 | `astro_engine/compute_life_phases(birth_profile)` — §5.2 pipeline applied longitudinally. Calculate Saturn return (~29yr), Uranus opposition (~42yr), Neptune square (~41yr), Chiron return (~50yr), nodal returns (~18yr). |
| 26 | 🔧 | Phase timeline generation: map natal placements to age-based milestones. `life_phases` table precomputation with start/end dates, dominant transits. Handle edge: user < 29 has only "foundation" + "expansion" phases. |
| 27 | 🔧 | `POST /v1/me/life-phases/recalculate`, `GET /v1/me/life-phases`, `GET /v1/me/life-phases/current`. Life phase endpoint returns ordered timeline with dominant transit highlights. |
| 27 | 🧪 | Test: user born 1990 → Saturn return 2019-2021 phase correct. User born 2005 → only foundation + pre-Saturn phases. |

**Check:** Life phases computed correctly for different age cohorts. API returns structured timeline.

### Chunk 6.2 — LifePhaseTimeline Component (2 days)

| Day | Area | Deliverable |
|-----|------|-------------|
| 28 | 🎨 | `LifePhaseTimeline` (§4.2): horizontal segmented track. `PhaseSegment` width proportional to phase duration. Phase labels, dominant transit badges. Current date marker line. |
| 28 | 🎨 | Phase detail panel: click a phase → shows description, dominant transits list, key dates. Expandable for LLM-generated interpretation (fetched when available). |
| 29 | 🎨 | `LifePhaseView` container: integrates timeline + detail panel. Responsive: horizontal timeline on desktop, vertical scroll on mobile. |
| 29 | 🔗 | Wire `component.render` SSE with `component="LifePhaseTimeline"` → mounts LifePhaseView. Preset "Life trajectory" triggers compute + render. |

**Check:** Life phase timeline renders for test user. Current phase highlighted. Clicking expands details. Preset works.

### Chunk 6.3 — AspectTable & Year Ahead (1 day)

| Day | Area | Deliverable |
|-----|------|-------------|
| 30 | 🎨 | `AspectTable` (§4.2): fixed matrix grid with body glyphs row/column headers. `AspectCell` colored by aspect type (green=trine, red=square, etc.), orb badge. Hover tooltip with exact degrees + applying/separating. |
| 30 | 🎨 | `YearAheadView`: combines TransitTimeline (12-month span) + AspectTable for key transits + LLM-generated year-ahead narrative. |
| 30 | 🔗 | Preset "Year ahead" → compute 12-month transits → render TransitTimeline + AspectTable + LLM analysis. |

**Week 6 Ship:** "Show my life phases" → timeline renders. "Year ahead" → transit timeline + aspect table + narrative. AspectTable full matrix interactive.

---

## Week 7 — Synastry & Compatibility

> **Ship:** Synastry pair creation. Bi-wheel rendering. Compatibility scoring. "Compatibility" preset.

### Chunk 7.1 — Synastry Computation Engine (2 days)

| Day | Area | Deliverable |
|-----|------|-------------|
| 31 | 🔧 | `astro_engine/compute_synastry(chart_a_id, chart_b_id)` — §5.4 pipeline. Inter-chart aspect engine (cross-body sets between Chart A and Chart B). House overlays (B bodies in A houses, vice versa). |
| 31 | 🔧 | `synastry_pairs` + `synastry_aspects` persistence. `POST /v1/synastry` creates pair, computes inter-aspects, stores. `GET /v1/synastry/:id` returns both charts + aspects + overlays. |
| 32 | 🔧 | Composite chart option: average lat/lon/date → compute new chart. Davison chart option: average datetime + midpoint geo → compute new chart. Score heuristics (§5.4 step 6): emotional/communication/passion/commitment/overall from 0-100. |
| 32 | 🧪 | Test: two known charts, verify inter-aspects detected (e.g., Person A Venus trine Person B Mars). Score heuristics produce reasonable 0-100 values. |

**Check:** Synastry creates inter-aspects. House overlays correct. Composite chart computes. Scores > 0 and < 100.

### Chunk 7.2 — SynastryBiWheel Component (2 days)

| Day | Area | Deliverable |
|-----|------|-------------|
| 33 | 🎨 | `SynastryBiWheel` (§4.2): inner `ZodiacWheel` (Chart A, no aspects), outer `ZodiacWheel` (Chart B, larger radius, dashed zodiac ring, different body palette). |
| 33 | 🎨 | `InterAspectLayer` — SVG lines connecting Chart A bodies to Chart B bodies across rings. Color-coded by aspect type. `HouseOverlayLegend` — table showing which outer planets fall in which inner house. |
| 34 | 🎨 | Composite chart view mode: single wheel with composite bodies. Aspect table comparison mode side-by-side. View mode toggle. |
| 34 | 🔗 | Wire `synastry.data` SSE event → SynastryBiWheel mounts. Preset "Compatibility" → prompts user to select second chart → renders bi-wheel. |

**Check:** Two charts rendered as bi-wheel. Inter-aspect lines visible. House overlays correct. Toggling view modes works.

### Chunk 7.3 — Synastry API & Preset (1 day)

| Day | Area | Deliverable |
|-----|------|-------------|
| 35 | 🔧 | `DELETE /v1/synastry/:id`. `GET /v1/synastry/:id/aspects` — filtered by major/minor/type. `GET /v1/synastry/:id/composite`. |
| 35 | 🎨 | Chart selection UI for synastry: search user's charts, or enter second birth profile for new chart. |
| 35 | 🔗 | "Compatibility" preset: if user has ≥2 charts → select two → compute synastry → render bi-wheel + scores. If only 1 chart → prompt to enter partner's birth data. |

**Week 7 Ship:** "How compatible are we?" → enter second birth data → bi-wheel + scores render. Full synastry flow end-to-end.

---

## Week 8 — Polish, Multi-User & Mobile

> **Ship:** Multi-user session support. Chart export (SVG/PNG). Mobile responsive layout. Production deployment ready.

### Chunk 8.1 — Multi-User & Session Management (2 days)

| Day | Area | Deliverable |
|-----|------|-------------|
| 36 | 🔧 | Anonymous-to-authenticated upgrade: magic link email verification. On email claim, merge anonymous user's birth_profile + charts to authenticated user row. |
| 36 | 🎨 | `TopBar` user switcher — avatar, display name, logout. Login/signup dialog. Session persistence (JWT in `localStorage`, auto-refresh before expiry). |
| 37 | 🎨 | Conversation list sidebar: shows all conversations for user, sorted by `updated_at desc`. Click to switch context. Archive action. New conversation button. |
| 37 | 🔧 | Data isolation verification pass: ensure all queries are scoped to `user_id` from JWT. Write integration test that user A cannot access user B's charts. |

**Check:** Anonymous user enters birth data → claims email → data persists. User A cannot access User B's charts. Conversation history loads.

### Chunk 8.2 — Chart Export & Mobile (2 days)

| Day | Area | Deliverable |
|-----|------|-------------|
| 38 | 🎨 | SVG export: `SVG.toSVG()` on ZodiacWheel element → download as `.svg`. PNG export: render SVG to `<canvas>` via `canvas.toBlob()` → download as `.png`. PDF export: use `jsPDF` to embed SVG + chat text. |
| 38 | 🎨 | Export button on ChartWorkspace toolbar. Context: "Share this chart", "Download for later". |
| 39 | 🎨 | Mobile responsive layout: `flex-col` on <768px (stacked chart/chat). `ChartWorkspace` becomes scrollable card. `ChatPanel` full width. Bottom sheet for chart detail panel. Touch-friendly planet markers (larger hit targets). |
| 39 | 🔗 | Test mobile layout in browser dev tools (iPhone 14, Pixel 7). Verify ZodiacWheel scales to 320px width. Verify chat input not obscured by keyboard. |

**Check:** Export chart as SVG downloads valid file. Mobile view renders chat + chart stacked. Touch interactions work.

### Chunk 8.3 — Hardening, Deployment & Docs (1 day)

| Day | Area | Deliverable |
|-----|------|-------------|
| 40 | 🔧 | Rate limiting: Redis sliding window per user/IP. 60 SSE conns/hr, 20 chart calcs/hr. Graceful error responses (429 with Retry-After). |
| 40 | 🔧 | Security: CORS restricted to production domain. PII encryption at rest for birth_profiles (pgcrypto or app-level AES-256). Audit log for chart calculations. |
| 40 | 🧪 | Load test: 10 concurrent SSE connections, 5 concurrent chart calculations. Verify compute time < 2s per chart. Memory profile stable. |
| 40 | 📋 | Final docs pass: API docs (FastAPI auto-generated OpenAPI), README with architecture diagram, deployment guide (docker compose + Caddy/nginx reverse proxy). |

**Week 8 Ship:** Multi-user with session management. Export buttons download charts. Mobile responsive passes. Rate limited, encrypted, documented.

---

## Appendix A — Dependency Risk & Mitigations

| Risk | Mitigation |
|------|-----------|
| Swiss Ephemeris C extension fails to compile in Docker | Pin `pyswisseph==2.10.03.1`. Fallback: use `flatlib` (pure Python, slower but works). |
| SSE polyfill issues with EventSource headers | Use `fetch`-based SSE client (`eventsource-parser` npm package) that supports custom headers. |
| LLM tool calling unreliable | Log all raw LLM responses. Implement retry logic (2 attempts). Fallback: if tool call fails, respond with text-only analysis + static chart link. |
| PostgreSQL JSONB query performance on `chart_bodies` | Index on `(chart_id, body_key)`. For full-text sign queries, use GIN index on `(body_key, sign)`. |
| VPS resource constraints (CX23 = 2 vCPU, 4GB RAM) | Keep ephemeris cache in Redis. Limit concurrent chart calculations (queue via Redis). Use `asyncpg` connection pooling. |

## Appendix B — Key Dependencies

| Layer | Package | Version | Purpose |
|-------|---------|---------|---------|
| Backend | `fastapi` | 0.115+ | API framework |
| Backend | `pyswisseph` | 2.10.03 | Swiss Ephemeris binding |
| Backend | `immanuel` | 1.2+ | High-level chart objects |
| Backend | `asyncpg` | 0.30+ | Async PostgreSQL driver |
| Backend | `redis-py` | 5.2+ | Session pub/sub, rate limiting |
| Backend | `pyjwt` | 2.9+ | JWT auth |
| Frontend | `react` | 18.3+ | UI framework |
| Frontend | `vite` | 6+ | Build tool |
| Frontend | `tailwindcss` | 4+ | Styling |
| Frontend | `react-markdown` | 9+ | Chat markdown rendering |
| Frontend | `react-window` | 1.8+ | Virtualized message list |
| Infrastructure | `postgres` | 15 | Database |
| Infrastructure | `redis` | 7 | Cache + pub/sub |

## Appendix C — File Tree (Target)

```
/opt/astrology-agent/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py               # FastAPI app factory
│   │   ├── config.py             # Settings from env
│   │   ├── database.py           # asyncpg engine + sessions
│   │   ├── models/               # SQLAlchemy ORM models
│   │   │   ├── user.py
│   │   │   ├── birth_profile.py
│   │   │   ├── chart.py
│   │   │   ├── chart_body.py
│   │   │   ├── chart_house.py
│   │   │   ├── chart_aspect.py
│   │   │   ├── synastry.py
│   │   │   ├── transit.py
│   │   │   ├── life_phase.py
│   │   │   ├── conversation.py
│   │   │   └── message.py
│   │   ├── schemas/              # Pydantic request/response schemas
│   │   ├── routers/              # FastAPI route handlers
│   │   │   ├── auth.py
│   │   │   ├── me.py
│   │   │   ├── charts.py
│   │   │   ├── transits.py
│   │   │   ├── synastry.py
│   │   │   ├── life_phases.py
│   │   │   ├── conversations.py
│   │   │   └── stream.py         # SSE streaming
│   │   ├── core/                 # Cross-cutting concerns
│   │   │   ├── auth.py           # JWT encode/decode, middleware
│   │   │   ├── rate_limit.py
│   │   │   └── security.py       # Encryption helpers
│   │   ├── astro_engine/         # Ephemeris & chart computation
│   │   │   ├── __init__.py
│   │   │   ├── ephemeris.py      # Swiss Ephemeris wrapper
│   │   │   ├── aspects.py        # Aspect detection
│   │   │   ├── dignity.py        # Dignity lookup
│   │   │   ├── transit.py        # Transit computation
│   │   │   ├── synastry.py       # Inter-chart aspects
│   │   │   ├── life_phases.py    # Life phase milestones
│   │   │   └── serializers.py    # DB serialization
│   │   └── llm/
│   │       ├── client.py         # pi.dev SDK integration
│   │       ├── prompts.py        # System prompt templates
│   │       └── tools.py          # Tool definition registry
│   ├── alembic/
│   │   ├── versions/
│   │   └── env.py
│   ├── tests/
│   │   ├── test_auth.py
│   │   ├── test_charts.py
│   │   ├── test_astro_engine.py
│   │   ├── test_transits.py
│   │   ├── test_synastry.py
│   │   ├── test_life_phases.py
│   │   └── test_conversations.py
│   ├── requirements.txt
│   ├── Dockerfile
│   └── pyproject.toml
├── frontend/
│   ├── src/
│   │   ├── main.tsx
│   │   ├── App.tsx
│   │   ├── types/
│   │   │   ├── chart.ts
│   │   │   ├── conversation.ts
│   │   │   ├── user.ts
│   │   │   └── events.ts         # SSE event types
│   │   ├── api/
│   │   │   ├── client.ts
│   │   │   └── sse.ts
│   │   ├── hooks/
│   │   │   ├── useSSE.ts
│   │   │   ├── useAuth.ts
│   │   │   └── useChart.ts
│   │   ├── context/
│   │   │   ├── AuthContext.tsx
│   │   │   ├── ChartContext.tsx
│   │   │   └── SSEContext.tsx
│   │   ├── components/
│   │   │   ├── Layout/
│   │   │   │   ├── AppShell.tsx
│   │   │   │   ├── TopBar.tsx
│   │   │   │   ├── Workspace.tsx
│   │   │   │   └── MobileDrawer.tsx
│   │   │   ├── Chart/
│   │   │   │   ├── ZodiacWheel.tsx
│   │   │   │   ├── SignSegment.tsx
│   │   │   │   ├── PlanetMarker.tsx
│   │   │   │   ├── AspectLine.tsx
│   │   │   │   ├── HouseCuspLine.tsx
│   │   │   │   ├── TransitOverlay.tsx
│   │   │   │   ├── SynastryBiWheel.tsx
│   │   │   │   ├── AspectTable.tsx
│   │   │   │   ├── TransitTimeline.tsx
│   │   │   │   ├── LifePhaseTimeline.tsx
│   │   │   │   ├── ChartController.tsx
│   │   │   │   └── ChartDetailPanel.tsx
│   │   │   ├── Chat/
│   │   │   │   ├── ChatPanel.tsx
│   │   │   │   ├── MessageList.tsx
│   │   │   │   ├── MessageBubble.tsx
│   │   │   │   ├── ChatInput.tsx
│   │   │   │   ├── PresetPromptChips.tsx
│   │   │   │   └── BirthDataPrompt.tsx
│   │   │   └── Shared/
│   │   │       ├── Avatar.tsx
│   │   │       ├── Toast.tsx
│   │   │       ├── Modal.tsx
│   │   │       └── LoadingSpinner.tsx
│   │   └── utils/
│   │       ├── coordinates.ts    # Polar math for wheel
│   │       ├── aspectColors.ts
│   │       └── glyphs.ts
│   ├── public/
│   │   └── fonts/                # Astrological glyph font
│   ├── index.html
│   ├── vite.config.ts
│   ├── tailwind.config.ts
│   ├── tsconfig.json
│   ├── package.json
│   └── Dockerfile
├── docker-compose.yml
├── Makefile
└── README.md
```
