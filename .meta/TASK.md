# Phase 3 — Implementation Plan

Read SPEC.md first. Then:

## Build Order
1. Set up FastAPI project structure + PostgreSQL schema (the 12 tables)
2. Implement Swiss Ephemeris integration (chart calculation endpoints)
3. Build React frontend with SVG ZodiacWheel component
4. Wire SSE streaming for chat + chart renders
5. Integrate birth profile CRUD + guided onboarding
6. Wire transit calculation + rendering
7. Wire synastry calculation + rendering
8. Build life trajectory engine

## Implementation Rules
- Build one piece at a time, verify it works
- Write tests for each piece
- Keep the frontend chart components parametrizable (agent-driven via SSE)
- Use the Canvas/MCP pattern from Jarvis-personal (SSE events, not REST polling)
- Start with the data model and backend, then frontend

Output a IMPLEMENTATION_PLAN.md file breaking this into actionable chunks, then begin implementing chunk 1.

Start now.
