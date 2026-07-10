#!/usr/bin/env python3
"""Live multi-turn conversation harness — real LLM, API only.

Runs scenarios **one at a time**, logs tokens / tools / exceptions, writes JSONL.

Usage::

    python -m tests.harness.multi_turn_runner --base-url http://localhost:8012
    python -m tests.harness.multi_turn_runner --scenario u1_daily --iteration 1
"""

from __future__ import annotations

import argparse
import asyncio
import importlib
import json
import logging
import pkgutil
import sys
import time
import traceback
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

logger = logging.getLogger("multi_turn_harness")


@dataclass
class ChatTurnResult:
    turn_id: str
    description: str
    user_message: str
    passed: bool
    status_code: int | None
    latency_ms: float
    assistant_content: str | None = None
    assistant_content_len: int = 0
    error_message: str | None = None
    assertions_failed: list[str] = field(default_factory=list)
    exception_trace: str | None = None
    tools_used: list[str] = field(default_factory=list)
    tool_messages: list[dict[str, Any]] = field(default_factory=list)
    # Provider token usage (aggregated over LLM rounds in this HTTP call)
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    reasoning_tokens: int = 0
    llm_rounds: int = 0
    request_bytes: int = 0
    response_bytes: int = 0
    message_count_after: int = 0


@dataclass
class MultiTurnScenarioResult:
    name: str
    description: str
    setup_ok: bool
    turns: list[ChatTurnResult]
    total_turns: int
    passed_turns: int
    failed_turns: int
    total_latency_ms: float
    total_prompt_tokens: int = 0
    total_completion_tokens: int = 0
    total_tokens: int = 0
    conversation_id: str | None = None
    user_id: str | None = None
    chart_id: str | None = None
    error: str | None = None
    iteration: int | None = None


def load_scenarios(only: str | None = None) -> list[dict[str, Any]]:
    """Load scenario modules. ``only`` matches exact id, or prefix/substring.

    Examples: ``u1``, ``u1_quick_daily``, ``quick_daily`` all select u1_quick_daily.
    """
    import tests.harness.scenarios as pkg

    found: list[dict[str, Any]] = []
    for modinfo in pkgutil.iter_modules(pkg.__path__, pkg.__name__ + "."):
        leaf = modinfo.name.rsplit(".", 1)[-1]
        if not leaf.startswith("scenario_"):
            continue
        mod = importlib.import_module(modinfo.name)
        sc = getattr(mod, "SCENARIO", None)
        if not isinstance(sc, dict):
            continue
        sid = str(sc.get("id") or sc.get("name") or "")
        if only:
            key = only.strip().lower()
            sid_l = sid.lower()
            if not (
                sid_l == key
                or sid_l.startswith(key)
                or key in sid_l
                or leaf.lower().replace("scenario_", "").startswith(key)
            ):
                continue
        found.append(sc)
    found.sort(key=lambda s: s.get("id", ""))
    return found


def _check_expect(
    expect: dict[str, Any],
    status: int,
    body: dict | None,
    tools_used: list[str],
) -> list[str]:
    fails: list[str] = []
    body = body or {}

    exp_status = expect.get("status", 201)
    if status != exp_status:
        fails.append(f"status expected {exp_status}, got {status}")
        if status in (502, 503) and body.get("detail"):
            fails.append(f"provider: {body['detail']}")
        return fails

    asst = body.get("assistant_message") or {}
    content = (asst.get("content") or "") if isinstance(asst, dict) else ""
    content_l = content.lower()

    if expect.get("require_nonempty_assistant", True) and not content.strip():
        fails.append("assistant content empty")

    min_len = expect.get("min_content_len")
    if min_len is not None and len(content) < int(min_len):
        fails.append(f"content length {len(content)} < min {min_len}")

    for frag in expect.get("assistant_contains", []) or []:
        if str(frag).lower() not in content_l:
            fails.append(f"missing fragment: {frag!r}")

    for frag in expect.get("assistant_not_contains", []) or []:
        if str(frag).lower() in content_l:
            fails.append(f"forbidden fragment: {frag!r}")

    any_of = expect.get("assistant_contains_any") or []
    if any_of and not any(str(f).lower() in content_l for f in any_of):
        fails.append(f"missing all of: {any_of!r}")

    # Astro grounding: at least one planet/sign-ish token when required
    if expect.get("require_astro_grounding"):
        planets = [
            "sun", "moon", "mercury", "venus", "mars", "jupiter", "saturn",
            "uranus", "neptune", "pluto", "ascendant", "rising", "house",
            "aries", "taurus", "gemini", "cancer", "leo", "virgo", "libra",
            "scorpio", "sagittarius", "capricorn", "aquarius", "pisces",
            "sol", "lua", "marte", "vênus", "venus", "júpiter", "saturno",
            "trânsito", "transit", "aspect", "aspecto", "nodo",
        ]
        if not any(p in content_l for p in planets):
            fails.append("missing astro grounding (no planet/sign/house/aspect terms)")

    tools_any = expect.get("tools_any_of") or []
    if tools_any and not any(t in tools_used for t in tools_any):
        fails.append(f"expected tools any of {tools_any}, saw {tools_used or 'none'}")

    tools_all = expect.get("tools_all_of") or []
    missing = [t for t in tools_all if t not in tools_used]
    if missing:
        fails.append(f"missing tools: {missing}")

    tools_none = expect.get("tools_none_of") or []
    bad = [t for t in tools_none if t in tools_used]
    if bad:
        fails.append(f"unexpected tools: {bad}")

    if expect.get("tools_empty"):
        if tools_used:
            fails.append(f"expected no tools, saw {tools_used}")

    return fails


class MultiTurnRunner:
    def __init__(
        self,
        base_url: str,
        timeout: float = 180.0,
        results_path: Path | None = None,
        pause_between_turns: float = 0.5,
        iteration: int | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.results_path = results_path or Path("harness_multi_turn_results.jsonl")
        self.pause_between_turns = pause_between_turns
        self.iteration = iteration
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> MultiTurnRunner:
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=httpx.Timeout(self.timeout, connect=30.0),
        )
        return self

    async def __aexit__(self, *args: object) -> None:
        if self._client:
            await self._client.aclose()

    @property
    def client(self) -> httpx.AsyncClient:
        assert self._client is not None
        return self._client

    async def _json(
        self,
        method: str,
        path: str,
        *,
        token: str | None = None,
        json_body: dict | None = None,
    ) -> tuple[int, dict | list | None, float, int, int, str | None]:
        headers: dict[str, str] = {}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        req_bytes = len(json.dumps(json_body).encode()) if json_body is not None else 0
        t0 = time.perf_counter()
        exc_trace = None
        try:
            r = await self.client.request(method, path, headers=headers, json=json_body)
        except Exception:
            latency = (time.perf_counter() - t0) * 1000
            return 0, None, latency, req_bytes, 0, traceback.format_exc()
        latency = (time.perf_counter() - t0) * 1000
        try:
            data = r.json() if r.content else None
        except Exception:
            data = {"raw": r.text[:800]}
        return r.status_code, data, latency, req_bytes, len(r.content or b""), exc_trace

    async def preflight(self) -> str | None:
        try:
            status, body, _, _, _, exc = await self._json("GET", "/v1/health")
        except Exception as e:
            return f"Cannot reach {self.base_url}: {e}"
        if exc:
            return exc
        if status != 200:
            return f"Health failed: {status} {body}"

        status, body, _, _, _, _ = await self._json("POST", "/v1/auth/anonymous", json_body={})
        if status != 200 or not isinstance(body, dict):
            return f"Auth failed: {status}"
        token = body["access_token"]
        status, body, _, _, _, _ = await self._json(
            "POST", "/v1/conversations", token=token, json_body={}
        )
        if status not in (200, 201) or not isinstance(body, dict):
            return f"Conversation create failed: {status}"
        cid = body["id"]
        status, body, lat, _, _, _ = await self._json(
            "POST",
            f"/v1/conversations/{cid}/messages",
            token=token,
            json_body={"content": "Reply with exactly: harness-ok"},
        )
        if status in (502, 503):
            detail = body.get("detail") if isinstance(body, dict) else body
            return f"Live LLM unavailable ({status}): {detail}"
        if status != 201:
            return f"LLM probe unexpected status {status}: {body}"
        logger.info("Preflight LLM OK (%.0fms)", lat)
        return None

    async def _setup(self, scenario: dict[str, Any]) -> dict[str, Any]:
        ctx: dict[str, Any] = {}
        status, body, _, _, _, _ = await self._json("POST", "/v1/auth/anonymous", json_body={})
        if status != 200 or not isinstance(body, dict):
            raise RuntimeError(f"auth failed: {status} {body}")
        ctx["token"] = body["access_token"]
        ctx["user_id"] = body.get("user_id")
        token = ctx["token"]

        setup = scenario.get("setup") or {}
        if setup.get("birth_profile"):
            status, body, _, _, _, _ = await self._json(
                "PUT", "/v1/me/profile", token=token, json_body=setup["birth_profile"]
            )
            if status not in (200, 201):
                raise RuntimeError(f"birth profile failed: {status} {body}")

        if setup.get("natal_chart"):
            status, body, _, _, _, _ = await self._json(
                "POST", "/v1/charts", token=token, json_body=setup["natal_chart"]
            )
            if status not in (200, 201) or not isinstance(body, dict):
                raise RuntimeError(f"natal chart failed: {status} {body}")
            ctx["chart_id"] = body.get("id")

        status, body, _, _, _, _ = await self._json(
            "POST", "/v1/conversations", token=token, json_body={}
        )
        if status not in (200, 201) or not isinstance(body, dict):
            raise RuntimeError(f"conversation failed: {status} {body}")
        ctx["conversation_id"] = body["id"]

        if ctx.get("chart_id"):
            await self._json(
                "PATCH",
                f"/v1/conversations/{ctx['conversation_id']}",
                token=token,
                json_body={"chart_context_id": ctx["chart_id"]},
            )
        return ctx

    async def _history(
        self, token: str, conversation_id: str
    ) -> tuple[list[str], list[dict], int]:
        status, body, _, _, _, _ = await self._json(
            "GET",
            f"/v1/conversations/{conversation_id}/messages?limit=200",
            token=token,
        )
        if status != 200 or not isinstance(body, dict):
            return [], [], 0
        items = body.get("items") or []
        names: list[str] = []
        tool_msgs: list[dict] = []
        for m in items:
            if m.get("role") == "tool" and m.get("tool_name"):
                names.append(m["tool_name"])
                tool_msgs.append(
                    {
                        "tool_name": m.get("tool_name"),
                        "preview": (m.get("content") or "")[:240],
                    }
                )
            if m.get("role") == "assistant" and isinstance(m.get("payload"), dict):
                for tc in m["payload"].get("tool_calls") or []:
                    n = (tc.get("function") or {}).get("name")
                    if n:
                        names.append(n)
                for n in m["payload"].get("tools_used") or []:
                    names.append(n)
        # unique preserve order
        uniq = list(dict.fromkeys(names))
        return uniq, tool_msgs, len(items)

    async def run_scenario(self, scenario: dict[str, Any]) -> MultiTurnScenarioResult:
        name = scenario.get("id") or "unnamed"
        desc = scenario.get("description") or ""
        turns_def: list[dict[str, Any]] = scenario.get("turns") or []
        results: list[ChatTurnResult] = []

        try:
            ctx = await self._setup(scenario)
        except Exception as exc:
            logger.error("[%s] setup failed: %s", name, exc)
            return MultiTurnScenarioResult(
                name=name,
                description=desc,
                setup_ok=False,
                turns=[],
                total_turns=len(turns_def),
                passed_turns=0,
                failed_turns=len(turns_def),
                total_latency_ms=0,
                error=str(exc),
                iteration=self.iteration,
            )

        token = ctx["token"]
        conversation_id = ctx["conversation_id"]
        user_id = ctx.get("user_id")
        chart_id = ctx.get("chart_id")

        for i, turn in enumerate(turns_def):
            turn_id = turn.get("id") or f"t{i + 1}"
            description = turn.get("description") or turn_id
            user_msg = turn["user"].replace("{chart_id}", str(chart_id or ""))
            user_msg = user_msg.replace("{user_id}", str(user_id or ""))
            expect = turn.get("expect") or {}

            logger.info("  → [%s] %s", turn_id, user_msg[:120].replace("\n", " "))

            status, body, latency, req_b, resp_b, exc_trace = await self._json(
                "POST",
                f"/v1/conversations/{conversation_id}/messages",
                token=token,
                json_body={"content": user_msg},
            )

            content = None
            tools_from_resp: list[str] = []
            usage: dict[str, Any] = {}
            if isinstance(body, dict):
                asst = body.get("assistant_message") or {}
                if isinstance(asst, dict):
                    content = asst.get("content")
                # Per-turn tools only — do not merge conversation-wide history
                # (that inflated follow-up turns with earlier tool names).
                tools_from_resp = list(body.get("tools_used") or [])
                usage = body.get("usage") or {}

            _hist_tools, tool_msgs, msg_count = await self._history(token, conversation_id)
            tools_used = list(dict.fromkeys(tools_from_resp))

            fails = _check_expect(
                expect,
                status,
                body if isinstance(body, dict) else None,
                tools_used,
            )
            if exc_trace:
                fails.append("transport exception")

            passed = not fails
            tr = ChatTurnResult(
                turn_id=turn_id,
                description=description,
                user_message=user_msg[:1000],
                passed=passed,
                status_code=status,
                latency_ms=latency,
                assistant_content=(content or "")[:5000] if content else None,
                assistant_content_len=len(content or ""),
                error_message=None if passed else "; ".join(fails),
                assertions_failed=fails,
                exception_trace=exc_trace,
                tools_used=tools_used,
                tool_messages=tool_msgs[-6:],
                prompt_tokens=int(usage.get("prompt_tokens") or 0),
                completion_tokens=int(usage.get("completion_tokens") or 0),
                total_tokens=int(usage.get("total_tokens") or 0),
                reasoning_tokens=int(usage.get("reasoning_tokens") or 0),
                llm_rounds=int(usage.get("llm_rounds") or 0),
                request_bytes=req_b,
                response_bytes=resp_b,
                message_count_after=msg_count,
            )
            results.append(tr)

            mark = "✓" if passed else "✗"
            preview = (
                (content or "")[:90].replace("\n", " ")
                if content
                else (fails[0] if fails else "")
            )
            logger.info(
                "  ← [%s] %s %s %.0fms tokens=%s tools=%s | %s",
                turn_id,
                mark,
                status,
                latency,
                usage.get("total_tokens") or "?",
                tools_used or "—",
                preview,
            )

            if not passed and turn.get("stop_on_fail", True):
                logger.warning("  stop_on_fail — ending scenario")
                break
            if self.pause_between_turns and i < len(turns_def) - 1:
                await asyncio.sleep(self.pause_between_turns)

        passed_n = sum(1 for t in results if t.passed)
        return MultiTurnScenarioResult(
            name=name,
            description=desc,
            setup_ok=True,
            turns=results,
            total_turns=len(turns_def),
            passed_turns=passed_n,
            failed_turns=len(results) - passed_n,
            total_latency_ms=sum(t.latency_ms for t in results),
            total_prompt_tokens=sum(t.prompt_tokens for t in results),
            total_completion_tokens=sum(t.completion_tokens for t in results),
            total_tokens=sum(t.total_tokens for t in results),
            conversation_id=conversation_id,
            user_id=str(user_id) if user_id else None,
            chart_id=str(chart_id) if chart_id else None,
            iteration=self.iteration,
        )

    def append_jsonl(self, result: MultiTurnScenarioResult) -> None:
        row = {
            "type": "multi_turn_scenario",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **asdict(result),
        }
        self.results_path.parent.mkdir(parents=True, exist_ok=True)
        with self.results_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(row, default=str) + "\n")


async def run_all(
    base_url: str,
    scenario: str | None,
    timeout: float,
    results_path: Path,
    skip_preflight: bool,
    pause: float,
    iteration: int | None,
    sequential: bool = True,
) -> int:
    scenarios = load_scenarios(scenario)
    if not scenarios:
        logger.error("No scenarios found")
        return 2

    logger.info("Loaded %d scenario(s) — live LLM, one-at-a-time", len(scenarios))
    for sc in scenarios:
        logger.info(
            "  • %s (%d turns): %s",
            sc.get("id"),
            len(sc.get("turns") or []),
            sc.get("description", ""),
        )

    all_results: list[MultiTurnScenarioResult] = []
    async with MultiTurnRunner(
        base_url,
        timeout=timeout,
        results_path=results_path,
        pause_between_turns=pause,
        iteration=iteration,
    ) as runner:
        if not skip_preflight:
            err = await runner.preflight()
            if err:
                logger.error("PREFLIGHT FAILED:\n%s", err)
                print(err, file=sys.stderr)
                return 2

        for sc in scenarios:
            logger.info("▶ START %s", sc.get("id"))
            res = await runner.run_scenario(sc)
            runner.append_jsonl(res)
            all_results.append(res)
            ok = res.setup_ok and res.failed_turns == 0 and res.passed_turns == res.total_turns
            logger.info(
                "▶ END %s — %s %d/%d  %.0fms  tokens=%d",
                sc.get("id"),
                "PASS" if ok else "FAIL",
                res.passed_turns,
                res.total_turns,
                res.total_latency_ms,
                res.total_tokens,
            )

    # Report
    print("\n" + "=" * 64)
    print(f"LIVE MULTI-TURN REPORT  iteration={iteration or '-'}")
    print("=" * 64)
    n_ok = sum(
        1
        for r in all_results
        if r.setup_ok and r.failed_turns == 0 and r.passed_turns == r.total_turns
    )
    print(f"  Scenarios: {len(all_results)}  passed: {n_ok}  failed: {len(all_results) - n_ok}")
    print(f"  Tokens:    {sum(r.total_tokens for r in all_results)}")
    print(f"  Latency:   {sum(r.total_latency_ms for r in all_results):.0f}ms")
    for r in all_results:
        flag = "✓" if r.setup_ok and r.failed_turns == 0 and r.passed_turns == r.total_turns else "✗"
        print(
            f"  {flag} {r.name}: {r.passed_turns}/{r.total_turns}  "
            f"{r.total_latency_ms:.0f}ms  tok={r.total_tokens}"
        )
        for t in r.turns:
            tools = ",".join(t.tools_used) if t.tools_used else "—"
            print(
                f"      [{t.turn_id}] {'✓' if t.passed else '✗'} "
                f"{t.status_code} {t.latency_ms:.0f}ms "
                f"tok={t.total_tokens} rounds={t.llm_rounds} tools=[{tools}] "
                f"len={t.assistant_content_len}"
            )
            if not t.passed:
                print(f"          FAIL: {t.error_message}")
            if t.exception_trace:
                print(f"          EXC: {t.exception_trace.splitlines()[-1]}")
    print(f"  JSONL → {results_path.resolve()}")
    print("=" * 64)

    # Compact sibling summary for quick post-run analysis (no DEBUG noise)
    summary_path = results_path.with_suffix(".summary.json")
    summary = {
        "iteration": iteration,
        "scenarios": len(all_results),
        "passed": n_ok,
        "failed": len(all_results) - n_ok,
        "total_tokens": sum(r.total_tokens for r in all_results),
        "total_latency_ms": sum(r.total_latency_ms for r in all_results),
        "results": [
            {
                "name": r.name,
                "ok": r.setup_ok and r.failed_turns == 0 and r.passed_turns == r.total_turns,
                "passed_turns": r.passed_turns,
                "total_turns": r.total_turns,
                "tokens": r.total_tokens,
                "latency_ms": r.total_latency_ms,
                "error": r.error,
                "turns": [
                    {
                        "id": t.turn_id,
                        "passed": t.passed,
                        "status": t.status_code,
                        "tools": t.tools_used,
                        "rounds": t.llm_rounds,
                        "prompt_tokens": t.prompt_tokens,
                        "completion_tokens": t.completion_tokens,
                        "total_tokens": t.total_tokens,
                        "reasoning_tokens": t.reasoning_tokens,
                        "latency_ms": t.latency_ms,
                        "reply_len": t.assistant_content_len,
                        "error": t.error_message,
                        "exception": (t.exception_trace or "")[:400] or None,
                        "preview": (t.assistant_content or "")[:240],
                    }
                    for t in r.turns
                ],
            }
            for r in all_results
        ],
    }
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n")
    print(f"  SUMMARY → {summary_path.resolve()}")
    return 0 if n_ok == len(all_results) and all_results else 1


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Live multi-turn harness (real LLM)")
    p.add_argument("--base-url", default="http://127.0.0.1:8012")
    p.add_argument("--scenario", default=None, help="Exact id, prefix, or substring (e.g. u1)")
    p.add_argument("--timeout", type=float, default=180.0)
    p.add_argument("--results", default="harness_multi_turn_results.jsonl")
    p.add_argument("--skip-preflight", action="store_true")
    p.add_argument("--pause", type=float, default=0.5)
    p.add_argument("--iteration", type=int, default=None)
    p.add_argument("-v", "--verbose", action="store_true")
    args = p.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )
    # Keep HTTP client noise out of harness logs unless -v
    if not args.verbose:
        for name in ("httpx", "httpcore", "openai", "urllib3"):
            logging.getLogger(name).setLevel(logging.WARNING)

    return asyncio.run(
        run_all(
            base_url=args.base_url,
            scenario=args.scenario,
            timeout=args.timeout,
            results_path=Path(args.results),
            skip_preflight=args.skip_preflight,
            pause=args.pause,
            iteration=args.iteration,
        )
    )


if __name__ == "__main__":
    sys.exit(main())
