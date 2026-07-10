# Agentic refactor plan — Astrology Agent

> Status: **Ready to execute**  
> Baseline: `.meta/AGENTIC_BASELINE.md`  
> Principles: `~/principles/agentic-coding.md`  
> Pattern reference: `~/principles/omnicanvas/agentic-refactor.md`

## Goal

Reduce agent tool-call cost and doc/code drift so future feature work (and multi-agent sessions) start from a single map, a single green gate, and deep modules at feature boundaries.

## Strategy (from principles)

1. **Measure** → 2. **Plan** → 3. **Merge co-read/co-change** → 4. **Deepen interfaces** → 5. **Document** → 6. **Verify**

- One phase per agent session when possible.
- **Never leave the gate red** across phase boundaries.
- Prefer merge over new abstraction layers.
- Update root `AGENTS.md` module map after every merge phase.

## Validation survival rule

Every phase ends with:

```bash
make validate
```

Defined in **R0** as:

```bash
# backend
cd backend && python -m pytest tests/ -q --ignore=tests/scenarios
# optional / documented: scenario runner when server up
# frontend
cd frontend && npx tsc --noEmit && npx vite build
```

If scenarios need a live server, document:

```bash
make validate          # unit + typecheck + build
make validate-scenarios  # requires uvicorn on BASE_URL
```

Do not block structural merges on live LLM scenarios; keep unit/API tests as the hard gate.

---

## Phase map

```text
R0  Context gate & root AGENTS     ──► agents can land without exploring
R1  Ops/docs truth (SQLite stack)  ──► Makefile/README match reality
R2  Chart SVG deep module          ──► wheel edits ≤2–3 files
R3  Chat/SSE frontend deep module  ──► stream path ≤3–4 FE files
R4  Backend domain collocation     ──► schema+router per domain
R5  Conversation/LLM deepen        ──► messages+llm clearer surface
R6  Astro engine interior merge    ──► fewer pipeline hops
R7  Dead code & barrel cleanup     ──► remove noise
R8  Re-measure + harness align     ──► metrics + scenario polish
```

Dependency DAG (execute left-to-right; R2∥R3 after R1; R4∥R5 after R1):

```text
R0 → R1 → R2 → R7 → R8
         ↘ R3 ↗
         ↘ R4 → R5 → R6 ↗
```

R2 and R3 are independent. R4 before R5 is preferred (messages schema moves with domain layout). R6 can follow R4 once import paths stabilize. R7 after major merges. R8 last.

---

## R0 — Context gate & root AGENTS

**Problem:** Product context lives under `.meta/`; agents re-explore. No single validate command.

**Do:**

1. Create **root** `AGENTS.md` (agent-facing, not a second PRD):
   - Stack truth (SQLite, ports 8001/5174, auth dev mode)
   - Module map (backend + frontend one-pagers)
   - Commands: install, run, `make validate`, scenarios
   - SSE event catalog (`chat.delta`, `chat.done`, `chart.data`, …)
   - Link to `.meta/SPEC.md` for deep product detail
2. Keep `.meta/AGENTS.md` as historical PRD **or** replace with a stub pointing at root (avoid two sources of truth — prefer root + “see .meta/SPEC”).
3. Add `make validate` (and fix `make test` to run **local** pytest without requiring docker postgres).
4. Point `.meta/workflow/handoffs.md` “Running” section at `AGENTS.md`.

**Gate:** `make validate` exists and passes on a clean checkout with deps installed.

**Out of scope:** Code merges.

**Est. agent session:** 1 small.

---

## R1 — Ops & docs truth

**Problem:** Makefile/README/conftest still describe Postgres + Redis; compose is backend+nginx+SQLite. Agents run wrong commands.

**Do:**

1. Rewrite Makefile targets for current stack:
   - `up`/`down` → docker compose (backend+nginx) **or** `dev` target for local uvicorn+vite
   - Remove or rename `psql` → `sqlite` shell helper
   - `migrate` / `seed` against local or container SQLite path
   - `test` → local pytest; drop hard docker dependency for unit tests
2. Restore or rewrite root `README.md` as short human entry (link SPEC, AGENTS).
3. Fix `conftest.py` comments / any remaining PG-only assumptions.
4. Align `.env.example` with `config.py` (SQLITE_PATH, AUTH_DEV_MODE, ports, OPENCODE_*).
5. Optionally add `scripts/dev-backend.sh` + `scripts/dev-frontend.sh` with `tee var/logs/*` (principles workflow).

**Gate:** `make validate` still green; `make help` documents real commands only.

**Est.:** 1 session.

---

## R2 — Chart SVG deep module

**Problem:** Wheel work requires 6–9 Chart files + 3 utils (classitis / co-read cluster C1).

**Do:**

1. Merge pure presentational wheel internals into **one deep module**, e.g.  
   `frontend/src/components/Chart/ZodiacWheel.tsx` (or `wheel.tsx`) containing:
   - SignSegment, PlanetMarker, AspectLine, ConstellationLines, GeometricCenter
   - Optionally inline or sibling-private helpers only used by the wheel
2. Keep **public** surface:
   - `ZodiacWheel` (export)
   - `ChartController` (modes / data wiring) — separate
   - `ChartDetailPanel` (side panel) — separate
3. Co-locate chart-only utils **or** import from a single `chartGeometry.ts` barrel used only by the wheel (prefer: put polar math next to wheel if nothing else needs it).
4. Delete or re-home orphaned `HouseCuspLine.tsx` (unused after redesign) — either drop or feature-flag inside the deep module if re-adding houses later.
5. Prefer **named exports**; update imports in Controller/Workspace.

**Target:** Wheel visual change = 1 file (+ types if schema changes).

**Gate:** `tsc --noEmit`, `vite build`, manual smoke: natal wheel renders.

**Non-goals:** Redesign aesthetics; mobile layout.

**Est.:** 1 session.

---

## R3 — Chat / SSE frontend deep module

**Problem:** Streaming chat spans api/sse, useSSE, SSEContext, useConversation, 5 Chat components (cluster C2).

**Do:**

1. Collapse transport + hooks into a **deep session module**, e.g.  
   `frontend/src/chat/session.ts` (or `hooks/chatSession.ts`):
   - EventSource/fetch stream client
   - subscribe / publish parsing of SSE event types
   - conversation send + message list state
2. Thin React bindings:
   - One `ChatProvider` **or** keep contexts but implement them with the deep module (no logic duplication).
3. Merge Chat UI that always co-changes:
   - `ChatPanel` + `MessageList` + `MessageBubble` → one file **or** Panel+List with Bubble kept if reused
   - Keep `ChatInput` and `PresetPromptChips` separate only if independently reused
4. Document event types once (mirror backend catalog in AGENTS).

**Target:** Change stream protocol handling in ≤2 FE files; change bubble styling in 1 file.

**Gate:** typecheck + build; manual: send message, see streaming tokens + thinking indicator.

**Est.:** 1 session.

---

## R4 — Backend domain collocation (schemas + routers)

**Problem:** Every API field change = router + schema in different trees (cluster C3).

**Do (preferred shape):**

```text
backend/app/domains/
  auth.py           # routes + pydantic models
  birth_profile.py
  charts.py
  conversations.py
  messages.py       # or leave for R5 with llm
  transits.py
  synastry.py
  life_phases.py
  me.py
```

Alternative (lower churn): co-locate as `routers/charts.py` importing from same-file schemas (models defined at top of router file). Same tool-call win; slightly messier FastAPI conventions.

**Rules:**

- Keep URL prefixes and OpenAPI tags stable (`/v1/...`).
- `main.py` imports domain routers only.
- Delete emptied `schemas/` modules after move.
- Do **not** invent a service layer per domain unless logic already duplicates.

**Order inside R4:** move smallest domains first (auth, me, birth_profile) → charts → transit/synastry/life_phases → conversations; leave `messages` for R5 if LLM tangle is large.

**Gate:** full pytest unit suite green; OpenAPI paths unchanged.

**Est.:** 1–2 sessions.

---

## R5 — Conversation / LLM deepen

**Problem:** Chat feature requires `messages` router + `llm/{client,prompts,tools}` (+ SSE). Tools file is 519 LOC mixing schema and execution.

**Do:**

1. Single package surface `app/llm/` with documented barrel:
   - `chat_completion`, `build_system_prompt`, `TOOL_DEFINITIONS`, `execute_tool`
2. Optionally collocate message routes into `domains/messages.py` that imports the llm barrel only.
3. Inside `tools.py`, use clear sectioning (or private `_exec_*.py` **only if** each is independently tested — prefer one deep tools module with TOC over many shallow files).
4. Ensure tool execution call chain is **≤2 hops**: router → `execute_tool` → engine.
5. Document tool names and SSE side-effects in AGENTS module map.

**Gate:** pytest including any message/LLM unit tests; smoke chat if key present (document skip without key).

**Est.:** 1 session.

---

## R6 — Astro engine interior merge

**Problem:** Natal pipeline is already a good deep façade (`compute_chart`), but dignity is a single-consumer shallow file; serializers always read with aspects/ephemeris.

**Do:**

1. **Keep** public API: `from app.astro_engine import compute_chart` (+ transit/synastry/life_phases entry points).
2. Merge `dignity.py` into `serializers.py` (or a private `_dignity` section) — update unit tests to import from new home **or** re-export for test stability.
3. Evaluate whether `aspects.py` + transit/synastry shared helpers should live in one `aspect_math` interior module (only if it reduces total files without creating a junk drawer).
4. Expand package docstring module map after merges.
5. Do **not** merge transit/synastry/life_phases into one file — they are separate features with separate routers.

**Gate:** `test_astro_engine.py` + transit/synastry/life_phases tests green.

**Est.:** 0.5–1 session.

---

## R7 — Dead code, barrels, export hygiene

**Problem:** Noise increases exploratory greps.

**Do:**

1. Remove empty `app/models/` **or** replace with one-line README in AGENTS (“no ORM; SQL in routers/database”).
2. Remove unused FE components after R2 (HouseCuspLine if still unused).
3. Prefer named exports on FE public components.
4. Ensure each package `__init__.py` is either a **documented barrel** or empty — no misleading re-exports.
5. Grep for stale Postgres/asyncpg references in comments and scripts.

**Gate:** `make validate`.

**Est.:** 0.5 session.

---

## R8 — Re-measure + harness alignment

**Problem:** Prove wins; align scenario harness with `~/principles/harness-*.md`.

**Do:**

1. Re-run baseline metrics table; write delta into `.meta/AGENTIC_BASELINE.md` (section “After R8”).
2. Files-per-feature targets:
   - Wheel visual: **≤2**
   - Domain API field: **≤1–2**
   - Chat stream protocol: **≤3** FE + **≤2** BE
3. Scenario harness (from ENHANCE_TESTING + principles):
   - Ensure JSONL fields useful for agent iteration
   - 3–5 turns per scenario; recovery case present
   - Document `make validate-scenarios` against BASE_URL
4. Append completion summary to `.meta/workflow/progress.md`.
5. Optional: `~/principles/astrology-agent/agentic-refactor.md` short pointer to this plan (project-specific application of universal principles).

**Gate:** validate green; baseline updated; open todos in workflow/todo.md refreshed.

**Est.:** 1 session.

---

## Priority if time-boxed

| Priority | Phase | Why |
|----------|-------|-----|
| P0 | R0 | Unblocks every future agent session |
| P0 | R1 | Stops wrong-stack thrash |
| P1 | R2 | Highest FE co-read cluster |
| P1 | R4 | Highest BE co-change tax |
| P2 | R3 | Chat path complexity |
| P2 | R5 | After domain layout stable |
| P3 | R6–R8 | Polish + proof |

---

## Per-phase checklist template

Copy into the session handoff when starting a phase:

```markdown
## Phase Rx — <title>
- [ ] Read .meta/AGENTIC_BASELINE.md + this phase section
- [ ] Read root AGENTS.md module map
- [ ] Implement merges only (no feature creep)
- [ ] Update AGENTS.md module map / paths
- [ ] make validate
- [ ] Append progress.md
- [ ] Note files-per-feature delta
```

---

## Risk register

| Risk | Mitigation |
|------|------------|
| Import churn breaks scenarios | Keep `/v1` paths; run pytest after each domain move |
| Giant ZodiacWheel.tsx hard to edit | One file is OK if **sectioned**; extract only if a second consumer appears |
| LLM tests need network/key | Mock client in unit tests; scenarios optional |
| Parallel agents on R2+R4 | Different trees (FE vs BE) — safe; avoid two agents on R4 domains |
| Scope creep into product features | Non-goals list; open product work stays in workflow/todo.md |

---

## Success criteria (program-level)

- [ ] Root `AGENTS.md` is the default landing doc for agents
- [ ] `make validate` is the only required green bar for refactors
- [ ] Chart wheel cluster ≤2 source files for pure visual work
- [ ] Domain API changes usually touch one backend module
- [ ] No Postgres/Redis instructions left for local unit development
- [ ] Baseline re-measured with improved files-per-feature numbers
- [ ] Product todos (E2E polish, PlanetMarker nit) still tracked separately — not lost inside refactor

---

## Suggested first execution step

Start **R0** immediately after this plan is accepted:

1. Write root `AGENTS.md` from baseline + handoff truth  
2. Add `make validate`  
3. Stub-point or retire duplicate vision in `.meta/AGENTS.md`  
4. Green bar → proceed to R1  

No application code merges until R0 gate is green.
