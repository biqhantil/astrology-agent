# Astrology Agent — Product Context

## Vision
A multi-user conversational astrology platform where users submit birth data (DOB, TOB, location) and receive personalized astrological analysis through a chat interface with rich visual chart components.

## Architecture Pattern
Use the established pattern from Jarvis-personal web UI:
- SSE streaming for real-time agent responses
- Canvas/MCP pattern — agent pushes structured data via event stream
- Frontend renders chart components (SVG zodiac wheel, aspect tables, transit timelines)
- Parametrized components fed by backend events, not REST polling

## Core Features (Phase 1)
1. Birth chart calculation — given DOB/TOB/location → signs, houses, aspects, degrees
2. Chart interpretation — natural language reading of placements and themes
3. Multi-year trajectory analysis — year-by-year across life dimensions
4. Transit analysis — current sky vs natal chart
5. Synastry / compatibility — two-chart overlay
6. Life phase mapping — Foundation → Saturn Return → Expansion → Legacy

## User Experience
- First interaction: guided collection of birth data
- Subsequent: full chart context loaded into system prompt
- Preset prompts for common queries (daily/weekly/monthly/yearly)
- Chat + visual chart side-by-side

## Key Decisions
- Conversational interface (not dashboard-first)
- Compartmentalized user contexts (multi-user from day one)
- Persistent astrological profile per user
- Chart-injected system prompt
- Rich visual charts using SVG/HTML rendered client-side from structured data

## Tech Stack
- Backend: Python/Node (determine during spec)
- Frontend: React with chart visualization library
- Chart calculation: Swiss Ephemeris
- LLM: OpenCode Go (via pi.dev)
- Hosting: CX23 VPS in fsn1 (this server)

## Reference
Full PRD is in the project directory.
