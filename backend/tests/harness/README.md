# Live multi-turn conversation harness

Programmatic **real-user multi-turn chats** against the API. No frontend.
Uses the **live LLM** (`LLM_MODE=live` + funded `OPENCODE_API_KEY`).

## Goal

Observe and refine harness/agent behavior under realistic conditions:

- Tool use across turns (natal, transits, life phases)
- Follow-ups and context carry-over
- Vague → specific recovery
- Latency, empty/incomplete answers, provider errors

## Run

```bash
# 1. Backend with live LLM (credits required)
cd backend
# .env: OPENCODE_API_KEY=sk-...   LLM_MODE=live
uvicorn app.main:app --reload --port 8001

# 2. Harness
python -m tests.harness.multi_turn_runner --base-url http://localhost:8001 --timeout 180

# One scenario
python -m tests.harness.multi_turn_runner --scenario mt_daily_forecast

# Or
make validate-harness BASE_URL=http://localhost:8001
```

Preflight sends one real chat turn and **aborts** if the provider returns 401/503 (e.g. insufficient credits).

## Scenarios

| ID | Real-user story |
|----|-----------------|
| `mt_daily_forecast` | Diário → work/love follow-up → timing |
| `mt_natal_then_phases` | Natal explain → Moon deep-dive → Saturn return |
| `mt_error_recovery` | pt-BR vague → daily transit → “be less generic” |
| `mt_tool_chain` | Load chart → 2-week transits → synthesize → memory check |

## Output

JSONL (`harness_multi_turn_results.jsonl` by default) per scenario:

- per-turn latency, status, content length
- tool names observed from conversation history
- assertion failures
- conversation_id for manual inspection

## Note on `LLM_MODE=mock`

Mock mode exists only for offline unit-style smoke tests. **This harness is for live LLM.** Do not set `LLM_MODE=mock` when refining real user behavior.
