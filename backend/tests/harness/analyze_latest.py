#!/usr/bin/env python3
"""Print a compact analysis of the latest (or given) single-scenario run."""

from __future__ import annotations

import json
import sys
from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parents[2]  # backend/
    single = root / "harness_iterations" / "single"

    if len(sys.argv) > 1:
        path = Path(sys.argv[1])
    else:
        paths = single / "LATEST.paths"
        if not paths.exists():
            print("No LATEST.paths — pass a .jsonl or .summary.json path", file=sys.stderr)
            return 2
        meta = dict(
            line.split("=", 1) for line in paths.read_text().splitlines() if "=" in line
        )
        path = Path(meta.get("jsonl") or "")

    if path.suffix == ".jsonl":
        summary_path = path.with_suffix(".summary.json")
        if summary_path.exists():
            data = json.loads(summary_path.read_text())
        else:
            rows = [json.loads(l) for l in path.read_text().splitlines() if l.strip()]
            data = {
                "total_tokens": sum(r.get("total_tokens", 0) for r in rows),
                "total_latency_ms": sum(r.get("total_latency_ms", 0) for r in rows),
                "passed": sum(
                    1
                    for r in rows
                    if r.get("setup_ok")
                    and r.get("failed_turns") == 0
                    and r.get("passed_turns") == r.get("total_turns")
                ),
                "failed": 0,
                "scenarios": len(rows),
                "results": [
                    {
                        "name": r.get("name"),
                        "ok": r.get("failed_turns") == 0 and r.get("setup_ok"),
                        "tokens": r.get("total_tokens"),
                        "latency_ms": r.get("total_latency_ms"),
                        "turns": [
                            {
                                "id": t.get("turn_id"),
                                "passed": t.get("passed"),
                                "tools": t.get("tools_used"),
                                "rounds": t.get("llm_rounds"),
                                "prompt_tokens": t.get("prompt_tokens"),
                                "completion_tokens": t.get("completion_tokens"),
                                "total_tokens": t.get("total_tokens"),
                                "latency_ms": t.get("latency_ms"),
                                "reply_len": t.get("assistant_content_len"),
                                "error": t.get("error_message"),
                                "preview": (t.get("assistant_content") or "")[:200],
                            }
                            for t in r.get("turns") or []
                        ],
                    }
                    for r in rows
                ],
            }
            data["failed"] = data["scenarios"] - data["passed"]
    else:
        data = json.loads(path.read_text())

    print("=" * 60)
    print(
        f"pass {data.get('passed')}/{data.get('scenarios')}  "
        f"tok={data.get('total_tokens')}  "
        f"lat={data.get('total_latency_ms', 0):.0f}ms"
    )
    print("=" * 60)
    notes: list[str] = []
    for r in data.get("results") or []:
        flag = "✓" if r.get("ok") else "✗"
        print(f"{flag} {r.get('name')}  tok={r.get('tokens')}  lat={r.get('latency_ms', 0):.0f}ms")
        for t in r.get("turns") or []:
            tools = t.get("tools") or []
            print(
                f"  [{t.get('id')}] {'✓' if t.get('passed') else '✗'} "
                f"rounds={t.get('rounds')} tools={tools or '—'} "
                f"tok={t.get('total_tokens')} "
                f"(p={t.get('prompt_tokens')} c={t.get('completion_tokens')}) "
                f"len={t.get('reply_len')}"
            )
            if t.get("error"):
                print(f"      FAIL: {t['error']}")
                notes.append(f"{r.get('name')}/{t.get('id')}: {t['error']}")
            # soft signals for harness refinement
            if (t.get("total_tokens") or 0) > 20000:
                notes.append(
                    f"{r.get('name')}/{t.get('id')}: high tokens {t.get('total_tokens')}"
                )
            if (t.get("rounds") or 0) >= 3:
                notes.append(
                    f"{r.get('name')}/{t.get('id')}: hit {t.get('rounds')} LLM rounds"
                )
            if "render_natal_chart" in tools:
                notes.append(
                    f"{r.get('name')}/{t.get('id')}: still called render_natal_chart"
                )
            if t.get("preview"):
                print(f"      {t['preview'][:120].replace(chr(10), ' ')}…")

    if notes:
        print("\n-- soft signals --")
        for n in notes:
            print(f"  • {n}")
    else:
        print("\n-- soft signals: none --")
    return 0 if data.get("failed", 0) == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
