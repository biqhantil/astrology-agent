# Handoff Notes — Astrology Agent

## Project Overview

A multi-user conversational astrology platform where users submit birth data (DOB, TOB, location) and receive personalized astrological analysis through a chat interface with rich SVG chart visualizations.

- **Backend**: Python/FastAPI/SQLite/aiosqlite, port 8001
- **Frontend**: React 19/TypeScript/Vite/TailwindCSS 4, port 5174
- **LLM**: OpenCode Go API (deepseek-v4-flash) via SSE streaming
- **Ephemeris**: Swiss Ephemeris for chart calculation

---

## Architecture Decisions

### Authentication
- Dev mode auto-login: `AUTH_DEV_MODE_ENABLED=true` creates a fixed preset user (bypasses Google OAuth)
- Production path: Google OAuth via `POST /v1/auth/google` with id_token
- JWT stored in localStorage, sent as `Authorization: Bearer <token>`
- DB has `auth_provider` and `google_sub` columns for multi-provider support

### Ports
- Backend: 8001
- Frontend: 5174
- Ports 8000 and 5173 are occupied by OmniCanvas (sibling project)

### Styling Approach
- Esoteric aesthetic: deep black (`#0a0a0a`), zinc grays, beige/cream text, amber/orange accents (`#d97706`)
- TailwindCSS 4 with custom color tokens in `tailwind.config.js`
- Glass-morphism cards with backdrop blur
- Full-viewport animated starfield background (CelestialSystem component) for profile form
- Floating form card: `absolute right-4 top-4 bottom-4`, `w-[clamp(320px,40vw,520px)]`, `max-h-[80vh]`, `bg-black/50 backdrop-blur-2xl`
- Chart view: three-column layout (detail left | wheel center | chat right)

### API Patterns
- Birth profile: `GET /v1/me/profile` → `POST /v1/me/profile`
- Chart calculation: `POST /v1/charts` with `{ chart_type, calculation_date, location, house_system }`
- SSE streaming for chat: `POST /v1/messages` streams `chat.delta` events for tokens, `chat.done` for completion
- LLM function calling for chart data retrieval (natal, transit, synastry)

### Data Flow
1. User fills birth profile form → saved to backend
2. On save, natal chart auto-calculated via Swiss Ephemeris
3. Chart displayed as ZodiacWheel (SVG) + ChartDetailPanel
4. Chat messages sent via SSE, streaming tokens displayed in ChatPanel with thinking indicator
5. LLM can request additional chart data via tool calls (transits, synastry, etc.)

---

## Session Work: Zodiac Wheel Redesign (July 9, 2026)

### Objective
Redesign the ZodiacWheel component to match a reference image of an astral map/astrological chart with:
- Pie-chart style with 3 concentric rings
- Light orange lines throughout
- Sign symbols in portions
- Sign names in outer sections
- Constellation outlines inside the rings
- Geometric/sacred geometry pattern in center

### Files Changed

**Modified:**
- `frontend/src/components/Chart/SignSegment.tsx` — Complete rewrite from single-arc element-band to 3 concentric rings per 30° sign segment:
  - Outer ring: uppercase sign name (rotated, letter-spaced, 0.7 opacity)
  - Middle ring: astrological sign glyph (0.5 opacity, AstroGlyphs font)
  - Inner ring: degree range text (monospace, 0.35 opacity)
  - Divider lines at segment boundaries spanning all 3 rings
  - All in `#d97706` (amber/orange) with varying opacity

- `frontend/src/components/Chart/ZodiacWheel.tsx` — Restructured layout:
  - Defines 6 ring radii for the 3-band system
  - Planets repositioned to inner chart area (`outerRadius * 0.38`)
  - Removed HouseCuspLine dependency (house lines not in reference design)
  - Integrated `ConstellationLines` and `GeometricCenter` components
  - Streamlined defs (removed unused radialGradient)

**Created:**
- `frontend/src/components/Chart/ConstellationLines.tsx` — Stylized constellation patterns:
  - Seeded random generator for deterministic per-sign patterns
  - Each sign gets 3–5 "star" points within its 30° wedge
  - Faint orange polylines connecting stars, plus variable-size star dots
  - Placed between inner ring edge and geometric center area
  - 0.35 overall opacity for subtlety

- `frontend/src/components/Chart/GeometricCenter.tsx` — Sacred geometry mandala:
  - 4 concentric circles with increasing opacity outward
  - Two overlapping hexagrams forming a 12-pointed star
  - Inner 6-pointed star
  - 12 fine radial lines emanating from center
  - Center dot with 0.3 opacity glow

### Ring Radii Layout (for a 600px wheel with center=300, outerRadius=260)

| Ring | Outer | Inner | Content |
|------|-------|-------|---------|
| Ring 1 | 260 (100%) | 213 (82%) | Sign names |
| Ring 2 | 213 (82%) | 182 (70%) | Sign glyphs |
| Ring 3 | 182 (70%) | 156 (60%) | Degree text |
| Constellation area | 151 (58%) | 39 (15%) | Star patterns |
| Planet ring | 99 (38%) | — | Body markers |

### Design Decisions
- All lines/accents use `#d97706` (amber/orange) — unifies the astral map look
- No element-based coloring (removed fire/earth/air/water colors) — cleaner monochrome-orange aesthetic
- No background fills on rings — only strokes, keeping the dark background visible
- Constellation outlines are purely decorative (seeded random, not astronomically accurate)
- Planet connecting lines still point toward inner ring (not updated for new radii — acceptably short)

---

## Running the Project

```bash
# Backend (port 8001)
cd backend && uvicorn app.main:app --reload --port 8001

# Frontend (port 5174)
cd frontend && npm run dev

# Type check
cd frontend && npx tsc --noEmit

# Build
cd frontend && npx vite build
```

Environment: `AUTH_DEV_MODE_ENABLED=true` for dev auto-login.

---

## Known Issues / Future Work

- PlanetMarker connecting line at `radius * 0.85` points to old ring position — low priority visual nit
- House cusp lines removed from wheel — could be re-added as faint inner annotations if desired
- No mobile responsive layout for chart view (tracked in SPEC.md)
- Constellation patterns are decorative, not astronomical — could be replaced with real constellation data
