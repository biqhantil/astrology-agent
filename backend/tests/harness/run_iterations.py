#!/usr/bin/env python3
"""Run multi-turn harness iterations and write a summary report.

Usage::

    python -m tests.harness.run_iterations --base-url http://127.0.0.1:8012 --iterations 5
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

from tests.harness.multi_turn_runner import run_all

logger = logging.getLogger("harness_iterations")


async def main_async(args: argparse.Namespace) -> int:
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    summary_path = out_dir / "iterations_summary.jsonl"
    codes: list[int] = []

    for i in range(1, args.iterations + 1):
        results_path = out_dir / f"iter_{i}.jsonl"
        # wipe this iter file
        if results_path.exists():
            results_path.unlink()
        logger.info("=" * 20 + f" ITERATION {i}/{args.iterations} " + "=" * 20)
        code = await run_all(
            base_url=args.base_url,
            scenario=args.scenario,
            timeout=args.timeout,
            results_path=results_path,
            skip_preflight=args.skip_preflight and i > 1,
            pause=args.pause,
            iteration=i,
        )
        codes.append(code)

        # Aggregate this iteration
        rows = []
        if results_path.exists():
            for line in results_path.read_text().splitlines():
                if line.strip():
                    rows.append(json.loads(line))
        fail_turns = []
        for r in rows:
            for t in r.get("turns") or []:
                if not t.get("passed"):
                    fail_turns.append(
                        {
                            "scenario": r.get("name"),
                            "turn": t.get("turn_id"),
                            "error": t.get("error_message"),
                            "status": t.get("status_code"),
                            "tools": t.get("tools_used"),
                        }
                    )
        agg = {
            "iteration": i,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "exit_code": code,
            "scenarios": len(rows),
            "scenario_pass": sum(
                1
                for r in rows
                if r.get("setup_ok")
                and r.get("failed_turns") == 0
                and r.get("passed_turns") == r.get("total_turns")
            ),
            "turns_passed": sum(r.get("passed_turns", 0) for r in rows),
            "turns_total": sum(r.get("total_turns", 0) for r in rows),
            "total_tokens": sum(r.get("total_tokens", 0) for r in rows),
            "total_latency_ms": sum(r.get("total_latency_ms", 0) for r in rows),
            "failures": fail_turns,
        }
        with summary_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(agg) + "\n")
        logger.info(
            "ITER %d summary: scenarios %d/%d  turns %d/%d  tokens=%d  fails=%d",
            i,
            agg["scenario_pass"],
            agg["scenarios"],
            agg["turns_passed"],
            agg["turns_total"],
            agg["total_tokens"],
            len(fail_turns),
        )
        # Stop early if perfect? User asked for 5 iterations always.
        # Continue even on success to measure variance.

    print("\n" + "#" * 64)
    print("ITERATION SERIES COMPLETE")
    print("#" * 64)
    if summary_path.exists():
        for line in summary_path.read_text().splitlines():
            a = json.loads(line)
            print(
                f"  iter {a['iteration']}: "
                f"scen {a['scenario_pass']}/{a['scenarios']}  "
                f"turns {a['turns_passed']}/{a['turns_total']}  "
                f"tok={a['total_tokens']}  "
                f"fails={len(a.get('failures') or [])}"
            )
    print(f"  Summary JSONL: {summary_path}")
    return 0 if all(c == 0 for c in codes) else 1


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--base-url", default="http://127.0.0.1:8012")
    p.add_argument("--iterations", type=int, default=5)
    p.add_argument("--timeout", type=float, default=180.0)
    p.add_argument("--pause", type=float, default=0.5)
    p.add_argument("--scenario", default=None)
    p.add_argument("--out-dir", default="harness_iterations")
    p.add_argument("--skip-preflight", action="store_true")
    p.add_argument("-v", action="store_true")
    args = p.parse_args()
    logging.basicConfig(
        level=logging.DEBUG if args.v else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )
    return asyncio.run(main_async(args))


if __name__ == "__main__":
    sys.exit(main())
