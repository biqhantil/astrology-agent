# Progress

## Completed — Session: Agentic R0–R8 + full E2E (July 9–10, 2026)

- [x] **R0** Root `AGENTS.md` + `make validate` (unit + tsc + vite build)
- [x] **R1** Makefile/README/.env.example/conftest SQLite truth
- [x] **R2** Chart SVG deep merge → single `ZodiacWheel.tsx`
- [x] **R3** Chat panel deep merge + `chat/session.ts` SSE transport
- [x] **R4** Schemas colocated into router modules
- [x] **R5** `app.llm` public barrel; messages imports barrel
- [x] **R6** Dignity merged into serializers (dignity.py re-export)
- [x] **R7** Removed `models/`, orphaned Chart/Chat/sse/useSSE files
- [x] **R8** Baseline after-metrics; E2E product fixes for green suite
- [x] **E2E** 9/9 scenarios, 101/101 turns; 121 unit tests; `make validate` green

### E2E product fixes included
- GET `/v1/charts` list; chart owner isolation; house `degree` alias
- Reject future birth dates; transit date-range validation order

## Completed — Session: Agentic context capture + refactor plan (July 9, 2026)

- [x] Measured codebase (42 backend app modules, ~40 FE modules, files-per-feature clusters)
- [x] Wrote `.meta/AGENTIC_BASELINE.md` (metrics, co-read clusters, doc drift, non-goals)
- [x] Wrote `.meta/AGENTIC_REFACTOR_PLAN.md` (phases R0–R8, DAG, gates, risks)
- [x] Wrote `~/principles/astrology-agent/agentic-refactor.md` (project pointer)
- [x] Executed R0–R8 (see above)

## Completed — Session: Zodiac Wheel Redesign (July 9, 2026)

### Components Rewritten
- [x] **SignSegment.tsx** — Rewritten from single-arc element-colored bands to 3 concentric rings per sign:
  - Outer: uppercase sign name in orange
  - Middle: astrological glyph in orange
  - Inner: degree range text in orange
  - Divider lines at 30° boundaries spanning all rings
  - Consistent `#d97706` orange palette throughout

### Components Created
- [x] **ConstellationLines.tsx** — Stylized seeded-random constellation patterns within each sign wedge:
  - 3–5 star points per sign connected by faint polylines
  - Variable-size star dots
  - Placed between inner ring edge and geometric center

- [x] **GeometricCenter.tsx** — Sacred geometry mandala:
  - 4 concentric circles with graduated opacity/width
  - 12-pointed star (two overlapping hexagrams)
  - Inner 6-pointed star
  - 12 radial lines from center
  - Center dot with glow

### Architecture
- [x] **ZodiacWheel.tsx** — Restructured to 3-ring layout:
  - New ring radii definitions (6 values for 3 bands)
  - Planets repositioned to `outerRadius * 0.38`
  - Integrated ConstellationLines and GeometricCenter
  - Removed HouseCuspLine dependency
  - Cleaned up unused defs

### Previous Sessions — Completed (Summary)

#### Auth & Profile
- [x] Dev preset user auto-login via `AUTH_DEV_MODE_ENABLED`
- [x] Google Auth groundwork (`POST /v1/auth/google`, `auth_provider`/`google_sub` in DB)
- [x] Migration fix: `_ensure_auth_columns()` separated into individual try/except blocks to prevent SQLite lock hangs

#### Birth Profile Form
- [x] Floating card layout: `absolute right-4 top-4 bottom-4`, backdrop blur
- [x] Full-viewport CelestialSystem starfield background (SVG animated)
- [x] Month/year `<select>` dropdowns + day grid date picker with "Today" quick button
- [x] City search via Nominatim API (free, no key)
- [x] Thinking indicator during form submission

#### Chart System
- [x] Chart calculation via Swiss Ephemeris (`POST /v1/charts`)
- [x] Natal chart auto-calculation on profile save
- [x] Chart storage in SQLite, body/house/aspect tables

#### Chat & Streaming
- [x] SSE streaming with `on_token` async callback in LLM client
- [x] `chat.delta` events published via SSE manager
- [x] Thinking indicator in ChatPanel during streaming
- [x] LLM function calling for chart data retrieval

#### Layout
- [x] Three-column workspace: DetailPanel (left 200–300px) | Wheel (center flex) | Chat (right 280–380px)
- [x] Mode tray (Natal/Transits/Synastry) in ChartController
- [x] Esoteric styling for ChartDetailPanel (glyphs, dignity badges, aspect list)
