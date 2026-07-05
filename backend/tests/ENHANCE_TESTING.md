# Testing Framework Enhancement — Scope of Work

## Current State

The scenario runner at `tests/scenario_runner.py` captures basic metrics:
- Per-turn: pass/fail, status code, latency, error message
- Per-scenario: aggregate pass/fail, avg/max latency
- Output: JSONL with these fields

**Missing:** No token tracking, no response body logging, no request/response size tracking, no exception stack traces, no prompt logging. The `metrics` field per turn is always empty `{}`.

## What's Needed

### Enhanced Per-Turn Metrics
Each turn should capture:

| Metric | How | Why |
|--------|-----|-----|
| Request payload size (bytes) | `len(json.dumps(body))` | Track prompt growth |
| Response body size (bytes) | `len(response.text)` | Track output size |
| Response body preview (first 500 chars) | `response.text[:500]` | Debug unexpected responses |
| Token estimation | `len(text) / 4` heuristic | Rough cost tracking |
| Exception stack traces | `traceback.format_exc()` | Full error visibility |
| Assertion detail | What value vs expected | Debug assertion failures |

### Results JSONL Schema Enhancement
Current fields → add: request_bytes, response_bytes, response_preview, estimated_tokens, exception_trace, assertions_detail

### Enhanced Reporting
The summary report should include:
- Average request/response sizes per scenario
- Token estimate totals
- Error distribution (which endpoints fail most)
- Response size anomaly detection

### Test Expansion
Create a stress test suite in `tests/scenarios/scenario_stress.py`:
- 20+ rapid-fire chart creations (verify no connection leaks)
- Concurrent same-user requests (auth token handling)
- Large date range transits (1+ year)
- Synastry with identical charts (edge case)
- Malformed birth data (invalid lat/lng, future dates, etc.)

## Additional Test Scenarios

1. **Concurrent user isolation** — two users, verify they can't access each other's data
2. **Chart recalculation** — update birth profile, recalculate chart, verify changes
3. **Transit date boundaries** — compute transits on exact birth date
4. **Large synastry** — create 5+ charts, compute all pairwise synastries
5. **Data persistence** — restart server, verify data accessible

## Build Order
1. Update ScenarioTurnResult dataclass with new fields
2. Update _execute_turn() to capture request/response sizes, token estimates, stack traces
3. Update _run_scenario() to collect and aggregate metrics
4. Update summary to display new metrics
5. Create scenario_stress.py with 5+ stress/edge scenarios
6. Add 5 new scenario files
7. Run full suite: python3 -m tests.scenario_runner --base-url http://localhost:8002 --parallel 3
8. Analyze results — find 3-5 actionable improvements or bugs

## Files to Modify
- tests/scenario_runner.py
- tests/scenarios/scenario_stress.py (new)
- tests/scenarios/ (additional scenarios)

## Completion Criteria
- All 10+ scenarios pass
- JSONL output includes request_bytes, response_bytes, estimated_tokens, exception_trace, assertions_detail
- Summary shows token estimates, response size distribution, error frequency
- At least 1 bug or context gap found from enhanced logging
