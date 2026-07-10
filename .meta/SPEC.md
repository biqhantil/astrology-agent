# Astrology Agent — Technical Specification (Phase 2)

> Version: 0.1  
> Date: 2026-07-05  
> Status: Draft  
> Based on: AGENTS.md (Phase 1 PRD)

---

## 1. Overview

This spec translates the Phase 1 product vision into concrete architecture: a multi-user conversational astrology platform with real-time SSE streaming, SVG chart rendering, and LLM-driven interpretation.

**Key architectural bets:**
- **Backend:** Python (FastAPI) — Swiss Ephemeris (`pyswisseph`, `flatlib`, `immanuel`) ecosystem, native async/SSE support.
- **Database:** PostgreSQL 15+ with JSONB for ephemeris snapshots; Redis for SSE session pub/sub.
- **Frontend:** React 18+ (Vite), SVG-first chart engine, no canvas libraries (DOM-over-SVG for accessibility and interactivity).
- **LLM Integration:** OpenCode Go via pi.dev SDK; system prompts injected with serialized chart context.
- **Pattern:** Canvas/MCP hybrid — agent pushes structured `chart.*` and `component.*` events over SSE; frontend renders parametrically.

---

## 2. Data Model

### 2.1 Entity Relationship Summary

```
users ─┬──► birth_profiles (1:1)
       ├──► charts (1:N)        ──┬──► chart_bodies (1:N)
       │                          ├──► chart_houses (1:N)
       │                          └──► chart_aspects (1:N)
       ├──► conversations (1:N) ──► messages (1:N)
       └──► synastry_pairs (1:N, self-ref FK on charts)

transit_runs (ephemeral / cached) ──► transit_events (1:N)

life_phases (reference / precomputed per user)
```

### 2.2 Schema Definitions

#### `users`
Multi-user root. Authentication is lightweight (magic link or anonymous session with optional email claim).

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `id` | UUID | PK, gen_random_uuid() | |
| `email` | VARCHAR(255) | NULL, UNIQUE | Optional identity |
| `display_name` | VARCHAR(100) | NULL | User-facing name |
| `locale` | VARCHAR(10) | DEFAULT 'en' | i18n |
| `created_at` | TIMESTAMPTZ | DEFAULT now() | |
| `last_active_at` | TIMESTAMPTZ | DEFAULT now() | |

#### `birth_profiles`
Canonical birth data per user. All charts derive from this unless overridden (e.g., synastry partner, event chart).

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `id` | UUID | PK | |
| `user_id` | UUID | FK → users.id, UNIQUE, ON DELETE CASCADE | 1:1 |
| `birth_date` | DATE | NOT NULL | Local calendar date |
| `birth_time` | TIME | NULL | Allow unknown TOB |
| `time_zone` | VARCHAR(50) | NOT NULL | IANA tz (e.g., `America/New_York`) |
| `utc_offset` | INTERVAL | NULL | Cached offset at birth time |
| `latitude` | DECIMAL(8,6) | NOT NULL | -90 to 90 |
| `longitude` | DECIMAL(9,6) | NOT NULL | -180 to 180 |
| `location_name` | VARCHAR(255) | NULL | Human-readable geo label |
| `house_system` | VARCHAR(10) | DEFAULT 'P' | Placidus ('P'), Whole Sign ('W'), etc. |
| `has_unknown_time` | BOOLEAN | GENERATED | `birth_time IS NULL` |
| `sun_sign` | VARCHAR(20) | NULL | Denormalized for quick listing |
| `moon_sign` | VARCHAR(20) | NULL | Denormalized |
| `rising_sign` | VARCHAR(20) | NULL | Denormalized; NULL if unknown time |
| `updated_at` | TIMESTAMPTZ | DEFAULT now() | |

#### `charts`
A computed astrological snapshot. Natal charts are auto-created when a `birth_profile` is saved. Additional charts support synastry, progressions, solar returns, and event charts.

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `id` | UUID | PK | |
| `user_id` | UUID | FK → users.id, ON DELETE CASCADE | Owner |
| `chart_type` | VARCHAR(20) | NOT NULL | `natal`, `transit`, `progressed`, `solar_return`, `synastry_composite`, `event` |
| `reference_chart_id` | UUID | FK → charts.id, NULL | For transit/progressed (base natal) |
| `title` | VARCHAR(100) | NULL | User label e.g., "My 2025 Solar Return" |
| `calculation_date` | TIMESTAMPTZ | NOT NULL | Moment the chart is calculated for |
| `house_system` | VARCHAR(10) | NOT NULL | Copy from profile at calc time |
| `location_name` | VARCHAR(255) | NULL | Geo context for this chart |
| `latitude` | DECIMAL(8,6) | NOT NULL | |
| `longitude` | DECIMAL(9,6) | NOT NULL | |
| `time_zone` | VARCHAR(50) | NOT NULL | |
| `raw_ephemeris` | JSONB | NOT NULL | Full Swiss Ephemeris output snapshot |
| `metadata` | JSONB | DEFAULT '{}' | Calc params, version, library version |
| `created_at` | TIMESTAMPTZ | DEFAULT now() | |
| `expires_at` | TIMESTAMPTZ | NULL | Cache TTL for transit charts |

#### `chart_bodies`
Planetary positions, angles, nodes, Lilith, Part of Fortune, etc. Normalized for fast querying ("show all charts with Moon in Scorpio").

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `id` | BIGSERIAL | PK | |
| `chart_id` | UUID | FK → charts.id, ON DELETE CASCADE | |
| `body_key` | VARCHAR(20) | NOT NULL | `sun`, `moon`, `mercury`, `venus`, `mars`, `jupiter`, `saturn`, `uranus`, `neptune`, `pluto`, `north_node`, `south_node`, `chiron`, `asc`, `mc`, `dsc`, `ic`, `lilith`, `part_of_fortune` |
| `longitude` | DECIMAL(10,7) | NOT NULL | 0–360 ecliptic |
| `latitude` | DECIMAL(10,7) | DEFAULT 0 | |
| `speed` | DECIMAL(10,7) | NOT NULL | Degrees/day; negative = retrograde |
| `sign` | VARCHAR(20) | NOT NULL | `aries` … `pisces` |
| `sign_degree` | DECIMAL(5,2) | NOT NULL | 0.00–29.99 within sign |
| `house` | SMALLINT | NULL | 1–12; NULL if unknown time / no houses |
| `is_retrograde` | BOOLEAN | GENERATED | `speed < 0` |
| `dignity` | VARCHAR(20) | NULL | `domicile`, `exaltation`, `detriment`, `fall`, `peregrine` |

#### `chart_houses`
House cusps for a given chart.

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `id` | BIGSERIAL | PK | |
| `chart_id` | UUID | FK → charts.id, ON DELETE CASCADE | |
| `house_number` | SMALLINT | NOT NULL | 1–12 |
| `cusps_longitude` | DECIMAL(10,7) | NOT NULL | |
| `sign` | VARCHAR(20) | NOT NULL | |
| `sign_degree` | DECIMAL(5,2) | NOT NULL | |

#### `chart_aspects`
Precomputed Ptolemaic and minor aspects between bodies in a single chart. Also used for synastry by pointing two charts into the query.

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `id` | BIGSERIAL | PK | |
| `chart_id` | UUID | FK → charts.id, ON DELETE CASCADE | For intra-chart |
| `body_a_key` | VARCHAR(20) | NOT NULL | |
| `body_b_key` | VARCHAR(20) | NOT NULL | |
| `aspect_type` | VARCHAR(20) | NOT NULL | `conjunction`, `sextile`, `square`, `trine`, `opposition`, `quincunx`, `semi_sextile`, `semi_square`, `sesquiquadrate` |
| `orb` | DECIMAL(5,2) | NOT NULL | Degrees of separation from exact |
| `is_applying` | BOOLEAN | NULL | Directional; NULL if stationing |
| `is_major` | BOOLEAN | NOT NULL | True for conj/sextile/square/trine/opp |

#### `synastry_pairs` (Synastry / Compatibility)
Links two charts and stores composite / Davison metadata. Inter-chart aspects are stored in `chart_aspects` with a compound key convention or a separate `synastry_aspects` table.

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `id` | UUID | PK | |
| `user_id` | UUID | FK → users.id | Initiator |
| `chart_a_id` | UUID | FK → charts.id | Typically natal A |
| `chart_b_id` | UUID | FK → charts.id | Typically natal B |
| `relationship_type` | VARCHAR(30) | NULL | `romantic`, `friendship`, `business`, `family` |
| `composite_chart_id` | UUID | FK → charts.id, NULL | Optional composite wheel |
| `davison_chart_id` | UUID | FK → charts.id, NULL | Optional Davison chart |
| `score_summary` | JSONB | NULL | Aggregated compatibility metrics |
| `created_at` | TIMESTAMPTZ | DEFAULT now() | |

#### `synastry_aspects`
Inter-chart aspects (Chart A body vs Chart B body). Kept separate from `chart_aspects` to avoid ambiguity.

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `id` | BIGSERIAL | PK | |
| `synastry_id` | UUID | FK → synastry_pairs.id | |
| `chart_a_id` | UUID | FK → charts.id | Denorm for partition pruning |
| `chart_b_id` | UUID | FK → charts.id | |
| `body_a_key` | VARCHAR(20) | NOT NULL | |
| `body_b_key` | VARCHAR(20) | NOT NULL | |
| `aspect_type` | VARCHAR(20) | NOT NULL | |
| `orb` | DECIMAL(5,2) | NOT NULL | |
| `is_applying` | BOOLEAN | NULL | |
| `house_overlay` | JSONB | NULL | `{body_a: 'mars', in_house_b: 7}` |

#### `transit_snapshots`
Time-series cache of transits against a natal chart. Computed on demand, cached with TTL.

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `id` | UUID | PK | |
| `natal_chart_id` | UUID | FK → charts.id | Base chart |
| `date_from` | DATE | NOT NULL | Range start |
| `date_to` | DATE | NOT NULL | Range end |
| `transit_events` | JSONB | NOT NULL | Array of `{date, transiting_body, natal_body, aspect_type, orb, exact_date, station_direct/retro}` |
| `created_at` | TIMESTAMPTZ | DEFAULT now() | |
| `expires_at` | TIMESTAMPTZ | NOT NULL | Eviction timestamp |

#### `life_phases`
Precomputed major life phases derived from Saturn returns, Uranus opposition, nodal returns, etc.

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `id` | BIGSERIAL | PK | |
| `user_id` | UUID | FK → users.id | |
| `phase_key` | VARCHAR(30) | NOT NULL | `foundation`, `saturn_return_1`, `expansion`, `chiron_return`, `saturn_return_2`, `uranus_opposition`, `legacy` |
| `title` | VARCHAR(100) | NOT NULL | Human label |
| `start_date` | DATE | NOT NULL | |
| `end_date` | DATE | NULL | Open-ended for current phase |
| `dominant_transits` | JSONB | NULL | `[{planet, aspect, natal_body, date}]` |
| `description` | TEXT | NULL | LLM-generated or templated |

#### `conversations`
Chat sessions. One active conversation per user at a time; historicals archived.

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `id` | UUID | PK | |
| `user_id` | UUID | FK → users.id, ON DELETE CASCADE | |
| `chart_context_id` | UUID | FK → charts.id, NULL | Chart loaded into prompt |
| `synastry_context_id` | UUID | FK → synastry_pairs.id, NULL | If comparing two charts |
| `title` | VARCHAR(200) | NULL | Auto-generated from first query |
| `status` | VARCHAR(20) | DEFAULT 'active' | `active`, `archived` |
| `model_version` | VARCHAR(50) | NULL | LLM snapshot |
| `created_at` | TIMESTAMPTZ | DEFAULT now() | |
| `updated_at` | TIMESTAMPTZ | DEFAULT now() | |

#### `messages`
Individual chat turns. Stores both visible text and hidden structured tool payloads.

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `id` | BIGSERIAL | PK | |
| `conversation_id` | UUID | FK → conversations.id, ON DELETE CASCADE | |
| `role` | VARCHAR(20) | NOT NULL | `system`, `user`, `assistant`, `tool` |
| `content` | TEXT | NOT NULL | Visible text or JSON string for tool |
| `tool_call_id` | VARCHAR(50) | NULL | Links assistant tool_use to tool result |
| `tool_name` | VARCHAR(50) | NULL | `render_chart`, `render_transit`, `render_synastry` |
| `payload` | JSONB | NULL | Structured data for tool renders |
| `created_at` | TIMESTAMPTZ | DEFAULT now() | |

### 2.3 Indexes

```sql
CREATE INDEX idx_charts_user_type ON charts(user_id, chart_type);
CREATE INDEX idx_chart_bodies_chart ON chart_bodies(chart_id);
CREATE INDEX idx_chart_bodies_sign ON chart_bodies(sign);
CREATE INDEX idx_chart_aspects_chart ON chart_aspects(chart_id);
CREATE INDEX idx_synastry_aspects_pair ON synastry_aspects(synastry_id);
CREATE INDEX idx_transit_snapshots_natal ON transit_snapshots(natal_chart_id, date_from, date_to);
CREATE INDEX idx_conversations_user ON conversations(user_id, status, updated_at DESC);
CREATE INDEX idx_messages_conversation ON messages(conversation_id, created_at);
```

---

## 3. API Contracts

### 3.1 Base URL & Transport
- **REST:** `https://api.astrology.agent/v1`
- **SSE:** `https://api.astrology.agent/v1/stream`
- **Format:** JSON. Dates ISO-8601. Longitudes 0–360 decimal.
- **Auth:** Bearer token (`Authorization: Bearer <session_jwt>`). Anonymous sessions minted on first visit.

### 3.2 REST Endpoints

#### Authentication & Users
| Method | Path | Description |
|--------|------|-------------|
| POST | `/auth/anonymous` | Mint anonymous session JWT |
| POST | `/auth/magic-link` | Request email link |
| GET | `/me` | Current user + birth_profile |
| PUT | `/me` | Update display_name, locale |

#### Birth Profile
| Method | Path | Description |
|--------|------|-------------|
| PUT | `/me/birth-profile` | Upsert birth data; triggers natal chart recalculation |
| GET | `/me/birth-profile` | Retrieve with `has_unknown_time` flag |
| POST | `/me/birth-profile/validate` | Validate geo + tz resolution from location string |

#### Charts
| Method | Path | Description |
|--------|------|-------------|
| POST | `/charts` | Calculate a new chart (event, solar return, etc.) |
| GET | `/charts/:id` | Full chart with bodies, houses, aspects |
| GET | `/charts/:id/summary` | Lightweight summary (signs, key aspects) |
| DELETE | `/charts/:id` | Soft or hard delete non-natal charts |
| GET | `/users/:user_id/charts` | List charts for a user |

**`POST /charts` Request Body:**
```json
{
  "chart_type": "natal | transit | progressed | solar_return | event",
  "reference_chart_id": "uuid|null",
  "calculation_date": "2026-07-05T12:00:00Z",
  "location": {
    "latitude": 40.7128,
    "longitude": -74.0060,
    "time_zone": "America/New_York",
    "location_name": "New York, NY"
  },
  "house_system": "P",
  "options": {
    "bodies": ["sun", "moon", "mercury", "venus", "mars", "jupiter", "saturn", "uranus", "neptune", "pluto", "north_node", "chiron", "asc", "mc"],
    "aspects": ["conjunction", "sextile", "square", "trine", "opposition"],
    "orb_major": 8.0,
    "orb_minor": 2.0
  }
}
```

**`GET /charts/:id` Response:**
```json
{
  "id": "uuid",
  "chart_type": "natal",
  "calculation_date": "1990-06-15T08:30:00-04:00",
  "location": { ... },
  "bodies": [
    {
      "body_key": "sun",
      "longitude": 84.5210,
      "sign": "gemini",
      "sign_degree": 24.52,
      "house": 12,
      "speed": 0.98,
      "is_retrograde": false,
      "dignity": "domicile"
    }
  ],
  "houses": [
    {
      "house_number": 1,
      "cusps_longitude": 120.40,
      "sign": "leo",
      "sign_degree": 0.40
    }
  ],
  "aspects": [
    {
      "body_a_key": "sun",
      "body_b_key": "moon",
      "aspect_type": "trine",
      "orb": 2.10,
      "is_applying": true,
      "is_major": true
    }
  ],
  "metadata": {
    "ephemeris_version": "swisseph-2.10.03",
    "calculation_library": "immanuel-1.2.0",
    "house_system": "Placidus"
  }
}
```

#### Transits
| Method | Path | Description |
|--------|------|-------------|
| POST | `/charts/:id/transits` | Calculate transits against natal chart |
| GET | `/charts/:id/transits?from=YYYY-MM-DD&to=YYYY-MM-DD` | Retrieve cached transit window |

**`POST /charts/:id/transits` Request:**
```json
{
  "date_from": "2026-07-01",
  "date_to": "2026-12-31",
  "granularity": "daily | weekly | monthly | eventful_only",
  "bodies": ["saturn", "uranus", "neptune", "pluto", "jupiter"],
  "include_retrograde_shadow": true
}
```

**Response (same as transit snapshot stored):**
```json
{
  "natal_chart_id": "uuid",
  "date_from": "2026-07-01",
  "date_to": "2026-12-31",
  "events": [
    {
      "date": "2026-08-14",
      "exact_date": "2026-08-14T09:22:00Z",
      "transiting_body": "saturn",
      "natal_body": "sun",
      "aspect_type": "opposition",
      "orb": 0.05,
      "is_stationing": false,
      "is_entering_sign": false
    }
  ],
  "retrograde_periods": [
    {
      "body": "mercury",
      "station_retrograde": "2026-08-05",
      "station_direct": "2026-08-28",
      "affected_natal_houses": [3, 6]
    }
  ]
}
```

#### Synastry
| Method | Path | Description |
|--------|------|-------------|
| POST | `/synastry` | Create synastry pair + compute inter-aspects |
| GET | `/synastry/:id` | Full synastry data with both charts |
| GET | `/synastry/:id/aspects` | Inter-chart aspect table |
| GET | `/synastry/:id/composite` | Composite chart (if computed) |
| DELETE | `/synastry/:id` | Remove pair |

**`POST /synastry` Request:**
```json
{
  "chart_a_id": "uuid",
  "chart_b_id": "uuid",
  "relationship_type": "romantic",
  "compute_composite": true,
  "compute_davison": false
}
```

**`GET /synastry/:id` Response:**
```json
{
  "id": "uuid",
  "chart_a": { "id": "uuid", "user_id": "uuid", ... },
  "chart_b": { "id": "uuid", "user_id": "uuid", ... },
  "relationship_type": "romantic",
  "inter_aspects": [ ... ],
  "house_overlays": [
    { "body_key": "sun", "in_partner_house": 7, "partner_chart_id": "uuid" }
  ],
  "composite_chart": { ... },
  "score_summary": {
    "emotional": 72,
    "communication": 65,
    "passion": 80,
    "commitment": 58,
    "overall": 69
  }
}
```

#### Life Phases
| Method | Path | Description |
|--------|------|-------------|
| POST | `/me/life-phases/recalculate` | Recompute based on current birth profile |
| GET | `/me/life-phases` | Ordered phase timeline |
| GET | `/me/life-phases/current` | Active phase with dominant transits |

#### Conversations
| Method | Path | Description |
|--------|------|-------------|
| POST | `/conversations` | Start new conversation; optionally attach chart/synastry context |
| GET | `/conversations` | List for user |
| GET | `/conversations/:id` | Retrieve with recent messages |
| POST | `/conversations/:id/archive` | Archive |
| DELETE | `/conversations/:id` | Hard delete |

### 3.3 SSE Streaming Contract (`/v1/stream`)

The chat + chart delivery channel. Client opens an `EventSource` with `Authorization` header (polyfill if needed for header support).

**Connection Init:**
```
GET /v1/stream?conversation_id=<uuid>&accept=chart.data,chat.delta,component.render
```

**Event Types:**

#### `chat.delta`
LLM token streaming. Frontend appends to current assistant message bubble.
```json
{
  "conversation_id": "uuid",
  "message_id": "uuid",
  "delta": "The conjunction of your natal Sun...",
  "finish_reason": null
}
```

#### `chat.tool_call`
Agent requests a chart render. Stream pauses; frontend acknowledges via REST (not required, but used for logging).
```json
{
  "conversation_id": "uuid",
  "tool_call_id": "call_abc123",
  "tool_name": "render_transit_timeline",
  "arguments": {
    "chart_id": "uuid",
    "date_from": "2026-07-01",
    "date_to": "2026-09-30",
    "highlight_bodies": ["saturn", "jupiter"]
  }
}
```

#### `chart.data`
Full chart payload pushed by backend (either on user request or agent tool output). Instructs frontend to mount/replace a chart workspace.
```json
{
  "chart_id": "uuid",
  "chart_type": "natal",
  "payload": { /* same as GET /charts/:id */ },
  "render_mode": "replace | overlay | split"
}
```

#### `transit.data`
Transit payload for timeline / wheel overlay.
```json
{
  "chart_id": "uuid",
  "natal_chart_id": "uuid",
  "payload": { /* transit snapshot */ },
  "highlight_date": "2026-08-14"
}
```

#### `synastry.data`
Synastry payload for bi-wheel / comparison view.
```json
{
  "synastry_id": "uuid",
  "chart_a": { ... },
  "chart_b": { ... },
  "inter_aspects": [ ... ],
  "render_mode": "bi_wheel | composite | aspect_table"
}
```

#### `component.render`
Low-level directive to render a specific UI component with data. Used for life-phase timelines, aspect grids, or preset daily summaries.
```json
{
  "component": "LifePhaseTimeline",
  "props": {
    "phases": [ ... ],
    "current_phase_index": 2
  },
  "slot": "sidebar" // or "main", "overlay"
}
```

#### `session.status`
Heartbeat / session state.
```json
{
  "status": "connected",
  "user_id": "uuid",
  "active_chart_id": "uuid|null",
  "queue_depth": 0
}
```

---

## 4. Component Hierarchy

### 4.1 Top-Level Layout

```
AppShell
├── TopBar (user switcher, conversation list, settings)
├── Workspace (flex row, 60/40 split responsive)
│   ├── ChartWorkspace (left / main)
│   │   ├── ChartController (state machine: which chart view is active)
│   │   │   ├── NatalChartView
│   │   │   ├── TransitChartView
│   │   │   ├── SynastryChartView
│   │   │   ├── LifePhaseView
│   │   │   └── EventChartView
│   │   └── ChartDetailPanel (bottom sheet / drawer on mobile)
│   └── ChatPanel (right / sidebar)
│       ├── MessageList
│       ├── MessageBubble (text + inline component slots)
│       ├── PresetPromptChips
│       └── ChatInput
└── GlobalToast / ModalLayer
```

### 4.2 Chart Component Tree

#### `ZodiacWheel` (SVG, reusable primitive)
Renders the 360° zodiac ring. Consumes a `ChartData` context.

```
ZodiacWheel (width/height responsive)
├── BackgroundRing (12 sign segments)
│   └── SignSegment × 12 (gradient fill per element: fire/earth/air/water)
├── SignLabelRing (glyphs + degree ticks)
├── HouseRing (optional, drawn inside/outside based on view)
│   └── HouseCuspLine × 12
├── AspectLayer (SVG lines between body positions)
│   └── AspectLine (color-coded: blue=trine, red=square, etc.)
└── BodyLayer (planet glyphs at computed polar coordinates)
    └── PlanetMarker
        ├── Glyph
        ├── DegreeLabel
        └── RetrogradeBadge (if retrograde)
```

**Props:**
```ts
interface ZodiacWheelProps {
  chart: ChartPayload;
  size: number; // px, default 600
  innerPadding: number; // house ring inset
  showHouses: boolean;
  showAspects: boolean;
  aspectFilter?: AspectType[];
  highlightedBody?: BodyKey;
  onBodyClick?: (body: BodyKey) => void;
  onAspectClick?: (aspect: Aspect) => void;
}
```

#### `TransitOverlay` (composes ZodiacWheel)
Renders transiting bodies outside or on top of natal wheel.

```
TransitOverlay
├── OuterWheelRing (dashed, slightly larger radius)
├── TransitBodyLayer
│   └── TransitMarker (larger glyph, different palette)
├── TransitAspectLines (natal body → transiting body)
└── DateScrubber (radial or linear date selector)
```

#### `SynastryBiWheel` (composes two ZodiacWheels)

```
SynastryBiWheel
├── InnerWheel (Chart A — natal)
│   └── ZodiacWheel(chartA, showAspects=false)
├── OuterWheel (Chart B — partner)
│   └── ZodiacWheel(chartB, showAspects=false, isOuter=true)
├── InterAspectLayer (lines crossing the ring boundary)
└── HouseOverlayLegend (which inner houses contain outer planets)
```

#### `AspectTable` (HTML/CSS grid)
Dense matrix of bodies × bodies with aspect glyphs.

```
AspectTable
├── AspectMatrixHeader (body glyphs across top and down side)
└── AspectMatrixGrid
    └── AspectCell (colored orb badge; hover tooltip with exact degrees)
```

#### `TransitTimeline` (HTML/CSS + SVG)
Horizontal time-series view. Essential for year-ahead and multi-year trajectory.

```
TransitTimeline
├── TimelineAxis (months / years)
├── TransitBarRow × N (one per major transiting body)
│   └── TransitSegment (colored band: exact window ± orb)
│       └── ExactDateMarker (diamond at exact conjunction)
├── RetrogradeShading (translucent bands under timeline)
└── EventPopovers (click for detail)
```

#### `LifePhaseTimeline`

```
LifePhaseTimeline
├── PhaseTrack (horizontal segments)
│   └── PhaseSegment (width proportional to duration)
│       ├── PhaseLabel
│       ├── DominantTransitBadges
│       └── ClickTarget → opens phase detail
└── CurrentDateMarker (vertical line)
```

### 4.3 Chat Component Tree

```
ChatPanel
├── MessageList (virtualized if > 100 messages)
│   └── MessageBubble
│       ├── Avatar (user / assistant)
│       ├── TextBlock (markdown rendered)
│       ├── InlineChartSlot (if message has attached chart payload)
│       │   └── MiniZodiacWheel (small, 200px inline preview)
│       └── ToolCallCard (if message is a tool render directive)
│           └── RenderedComponent (mounts actual chart component)
├── PresetPromptChips
│   └── ChipButton × N ("Daily forecast", "This week", "Saturn return", "Compatibility")
└── ChatInput
    ├── TextArea (auto-grow)
    ├── SendButton
    └── BirthDataPrompt (if user has no birth_profile)
```

### 4.4 Data Flow Diagram

```
User Input → ChatInput
    → POST /conversations/:id/messages (or SSE send)
    → Backend orchestrates:
        a) LLM inference with chart context injected
        b) Ephemeris calculation (if tool_call triggered)
        c) SSE emit: chat.delta + chart.data / component.render
    → Frontend:
        → ChatPanel appends deltas to MessageBubble
        → ChartWorkspace receives chart.data → mounts ZodiacWheel/TransitOverlay/etc.
        → Component state updates via ChartContext provider
```

---

## 5. Chart Calculation Engine

### 5.1 Library Stack
- **`swisseph`** (C extension): Core ephemeris — positions, houses, nodes.
- **`flatlib`** or **`immanuel`** (Python): Higher-level chart objects, aspect detection, dignities.
- **Custom wrapper (`astro_engine`)**: Normalizes output to SPEC schema, handles timezone resolution (`zoneinfo` / `pytz`), caches computed charts.

### 5.2 Calculation Pipeline

```
Input: (datetime, lat, lon, tz, house_system, body_list)
    │
    ▼
[1] Time normalization → UTC Julian Day (JD)
    │
    ▼
[2] Ephemeris compute (swisseph)
    ├── Planetary longitudes, speeds, latitudes
    ├── House cusps (Placidus / Whole Sign / etc.)
    ├── Ascendant / MC / other angles
    └── Nodes, Lilith, Part of Fortune (optional)
    │
    ▼
[3] Aspect engine
    ├── Generate all body pairs
    ├── Test angular separation against aspect orbs
    ├── Determine applying vs separating (speed differential)
    └── Classify major / minor / Ptolemaic
    │
    ▼
[4] Dignity engine (immanuel rules or custom)
    ├── Domicile / exaltation / detriment / fall lookup tables
    └── Assign to each chart_body
    │
    ▼
[5] Serialization → chart_bodies[], chart_houses[], chart_aspects[]
    └── Persist to PostgreSQL + JSONB raw_ephemeris
```

### 5.3 Transit Pipeline

```
Input: (natal_chart_id, date_from, date_to, granularity)
    │
    ▼
[1] Retrieve natal chart bodies + houses
    │
    ▼
[2] Iterate date range (step size depends on granularity)
    ├── daily: 1 day
    ├── eventful_only: step 1 day, but filter to exact ± 2°
    └── weekly: 7 days
    │
    ▼
[3] For each step, compute transiting body positions
    ├── Compare to natal longitudes
    ├── Detect exact crossings, sign ingresses, house ingresses
    ├── Detect stations (speed crosses zero)
    └── Record events where orb < threshold
    │
    ▼
[4] Return as TransitSnapshot JSONB; cache with 24h TTL
```

### 5.4 Synastry Pipeline

```
Input: (chart_a_id, chart_b_id)
    │
    ▼
[1] Retrieve both charts
    │
    ▼
[2] Inter-chart aspects (same engine as intra-chart, cross-body sets)
    │
    ▼
[3] House overlays (Chart B bodies into Chart A houses, and reverse)
    │
    ▼
[4] Optional composite midpoint chart
    ├── Average lat/lon/date
    └── Compute new chart
    │
    ▼
[5] Optional Davison chart (average datetime + midpoint geo)
    │
    ▼
[6] Score heuristics (template-based, not ML)
    ├── Emotional: Moon-Moon, Venus-Moon aspects + overlays
    ├── Communication: Mercury-Merc, Mercury-Venus
    ├── Passion: Mars-Venus, Mars-Mars
    └── Commitment: Saturn-Sun, Saturn-Venus
```

---

## 6. LLM Integration & System Prompt Architecture

### 6.1 Context Injection Format

When a conversation has an `active_chart_id`, the backend serializes a compact astrological context block and prepends it to the system prompt:

```
You are an expert astrological interpreter. You have access to the user's natal chart and current transits. When you need to visualize data, emit a tool_call.

--- USER CHART CONTEXT ---
Name: {display_name}
Birth: {birth_date} {birth_time} {location_name}
Sun: {sign} {degree}° (House {house})
Moon: {sign} {degree}° (House {house})
Rising: {sign} {degree}°
Key Aspects: {list of major aspects}
Current Transits (as of {today}):
  - {transiting_body} {aspect} natal {natal_body} (orb {orb}°)
---
```

### 6.2 Tool Definitions (JSON Schema for LLM)

The LLM can invoke these tools; the backend maps them to SSE `chat.tool_call` events:

```json
{
  "name": "render_natal_chart",
  "description": "Display the user's natal chart wheel",
  "parameters": { "type": "object", "properties": { "chart_id": { "type": "string" } }, "required": ["chart_id"] }
}
{
  "name": "render_transit_timeline",
  "description": "Display a timeline of upcoming transits",
  "parameters": {
    "type": "object",
    "properties": {
      "chart_id": { "type": "string" },
      "date_from": { "type": "string", "format": "date" },
      "date_to": { "type": "string", "format": "date" },
      "highlight_bodies": { "type": "array", "items": { "type": "string" } }
    },
    "required": ["chart_id", "date_from", "date_to"]
  }
}
{
  "name": "render_synastry",
  "description": "Display a synastry comparison between two charts",
  "parameters": {
    "type": "object",
    "properties": {
      "synastry_id": { "type": "string" },
      "view_mode": { "type": "string", "enum": ["bi_wheel", "aspect_table", "composite"] }
    },
    "required": ["synastry_id"]
  }
}
{
  "name": "render_life_phases",
  "description": "Display the user's life phase map",
  "parameters": { "type": "object", "properties": { "user_id": { "type": "string" } } }
}
```

### 6.3 Streaming Protocol Flow

1. Client opens SSE to `/v1/stream?conversation_id=uuid`.
2. User sends message via `POST /conversations/:id/messages` or over SSE `client.message` event.
3. Backend:
   - Loads conversation + chart context.
   - Streams `chat.delta` tokens as LLM generates.
   - If LLM emits `<tool_call>`, backend pauses token stream, executes the tool (ephemeris calc or DB query), emits `chat.tool_call` + `chart.data` / `component.render`, then resumes or closes.
4. Client renders tokens into `MessageBubble`; mounts chart components into `ChartWorkspace` when chart events arrive.

---

## 7. Multi-User Context Model

Every request is scoped to a `user_id` derived from the JWT. Key isolation rules:

- **Birth profiles:** 1 per user. Update triggers natal chart recalculation.
- **Charts:** `user_id` ownership. A synastry chart_b may belong to another user if shared via link, but inter-aspects are computed server-side and only the synastry pair owner sees results.
- **Conversations:** `user_id` scoped. Messages never leak across users.
- **LLM context:** System prompt only injects the requesting user's chart data. No cross-user contamination.
- **Anonymous sessions:** JWT with `sub = anonymous:<uuid>`. Optionally upgraded to `users` row via magic link (`email` claim). Birth profile and charts migrate on upgrade.

---

## 8. Security & Privacy

| Concern | Mitigation |
|---------|------------|
| Birth data sensitivity (PII) | Store encrypted at rest (AES-256 via PostgreSQL pgcrypto, or application-level). Birth profiles excluded from casual logs. |
| LLM data leakage | System prompt context is ephemeral per request; no chart data sent to model training endpoints. |
| JWT/session | 24h expiry for anonymous; 7d for authenticated. Refresh rotation. |
| Rate limiting | 60 SSE connects / hour / IP; 20 chart calculations / hour / user. Redis sliding window. |
| Geo/location | `location_name` is user-provided string; lat/lon are calculation outputs. No reverse geocoding stored without consent. |

---

## 9. Implementation Phasing

### Phase 2a (MVP — Weeks 1–3)
- [ ] PostgreSQL schema migrations (`users`, `birth_profiles`, `charts`, `chart_bodies`, `chart_houses`, `chart_aspects`, `conversations`, `messages`)
- [ ] FastAPI skeleton + JWT anonymous auth
- [ ] Swiss Ephemeris Python wrapper (`astro_engine`) — natal chart compute only
- [ ] `ZodiacWheel` React component (SVG) with sign segments + body markers
- [ ] SSE `/stream` endpoint + `chat.delta` + `chart.data` events
- [ ] Birth profile collection UI + auto-natal chart render
- [ ] Basic chat UI with system prompt injection

### Phase 2b (Core Features — Weeks 4–6)
- [ ] `AspectTable` component
- [ ] Transit calculation engine + `TransitTimeline` component
- [ ] Daily / weekly / monthly preset prompts
- [ ] `TransitOverlay` on ZodiacWheel
- [ ] Life phase precomputation + `LifePhaseTimeline`

### Phase 2c (Synastry & Polish — Weeks 7–8)
- [ ] Synastry pair creation + `SynastryBiWheel`
- [ ] Composite / Davison chart compute
- [ ] Inter-chart aspect scoring heuristics
- [ ] Multi-user session switcher UI
- [ ] Chart export (SVG / PNG / PDF)
- [ ] Mobile responsive layout (stacked chat/chart)

---

## 10. Appendix

### A. Body Key Reference
```
sun, moon, mercury, venus, mars, jupiter, saturn, uranus, neptune, pluto,
north_node, south_node, chiron, asc, mc, dsc, ic, lilith, part_of_fortune
```

### B. House System Codes
```
P = Placidus (default)
W = Whole Sign
K = Koch
E = Equal
R = Regiomontanus
C = Campanus
V = Vehlow
```

### C. Aspect Orbs (Default)
| Aspect | Orb |
|--------|-----|
| Conjunction | 8° |
| Sextile | 6° |
| Square | 8° |
| Trine | 8° |
| Opposition | 8° |
| Quincunx | 3° |
| Semi-sextile | 2° |
| Semi-square | 2° |
| Sesquiquadrate | 2° |

### D. Sign Dignity Lookup (Simplified)
| Body | Domicile | Exaltation | Detriment | Fall |
|------|----------|------------|-----------|------|
| Sun | Leo | Aries | Aquarius | Libra |
| Moon | Cancer | Taurus | Capricorn | Scorpio |
| Mercury | Gemini/Virgo | Virgo | Sagittarius/Pisces | Pisces |
| Venus | Taurus/Libra | Pisces | Scorpio/Aries | Virgo |
| Mars | Aries/Scorpio | Capricorn | Libra/Taurus | Cancer |
| Jupiter | Sagittarius/Pisces | Cancer | Gemini/Virgo | Capricorn |
| Saturn | Capricorn/Aquarius | Libra | Cancer/Leo | Aries |
| Uranus | Aquarius | Scorpio | Leo | Taurus |
| Neptune | Pisces | Cancer/Leo? | Virgo | Capricorn/Aquarius? |
| Pluto | Scorpio | Leo? | Taurus | Aquarius? |

*(Standard classical rulerships used for dignity engine; modern rulerships optional toggle.)*
