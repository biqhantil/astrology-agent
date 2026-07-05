#!/usr/bin/env python3
"""Scenario-based integration test runner for the Astrology Agent API.

Loads scenario definitions from ``tests/scenarios/scenario_*.py``,
sends prompts to a real backend API (or mock), collects per-turn metrics
(chart compute latency, aspect accuracy, validation errors), runs batches
in parallel, and outputs JSONL + aggregated report.

Usage::

    # Run all scenarios against local dev server
    python -m tests.scenario_runner

    # Run a specific scenario
    python -m tests.scenario_runner --scenario birth_chart_creation

    # Run against a different base URL
    python -m tests.scenario_runner --base-url http://localhost:8000

    # Dry run (validate scenarios without sending requests)
    python -m tests.scenario_runner --dry-run

    # Run with parallel batch execution
    python -m tests.scenario_runner --parallel 4
"""

from __future__ import annotations

import argparse
import asyncio
import copy
import importlib
import json
import logging
import os
import sys
import time
import traceback
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

import httpx

# Token estimation: 1 token ≈ 4 characters (rough heuristic)
TOKEN_ESTIMATE_RATIO = 4.0

# ── Logging ─────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("scenario_runner")


# ======================================================================
# Data classes
# ======================================================================


@dataclass
class TurnResult:
    """Result of executing a single scenario turn."""

    turn_id: str
    description: str
    status_code: int | None
    expected_status: int
    passed: bool
    latency_ms: float
    response_body: dict | list | None = None
    error_message: str | None = None
    extraction: dict[str, Any] = field(default_factory=dict)
    assertions_failed: list[str] = field(default_factory=list)
    metrics: dict[str, Any] = field(default_factory=dict)
    # ── Enhanced tracking fields ──
    request_bytes: int | None = None
    response_bytes: int | None = None
    response_preview: str | None = None
    estimated_prompt_tokens: int | None = None
    estimated_response_tokens: int | None = None
    exception_trace: str | None = None
    assertions_detail: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class ScenarioResult:
    """Result of executing an entire scenario."""

    name: str
    description: str
    turn_results: list[TurnResult]
    total_turns: int
    passed_turns: int
    failed_turns: int
    total_latency_ms: float
    max_turn_latency_ms: float
    avg_turn_latency_ms: float
    timestamp: str
    error: str | None = None


@dataclass
class ScenarioDefinition:
    """A loaded scenario definition with its module metadata."""

    name: str
    description: str
    turns: list[dict[str, Any]]
    module_name: str


# ======================================================================
# Metrics
# ======================================================================


@dataclass
class AggregateMetrics:
    """Aggregated metrics across all scenario runs."""

    total_scenarios: int = 0
    passed_scenarios: int = 0
    failed_scenarios: int = 0
    total_turns: int = 0
    passed_turns: int = 0
    failed_turns: int = 0
    total_latency_ms: float = 0.0
    avg_turn_latency_ms: float = 0.0
    max_turn_latency_ms: float = 0.0
    chart_compute_latencies: list[float] = field(default_factory=list)
    validation_errors: list[str] = field(default_factory=list)
    aspect_counts: list[int] = field(default_factory=list)
    # ── Enhanced aggregate metrics ──
    total_request_bytes: int = 0
    total_response_bytes: int = 0
    total_estimated_prompt_tokens: int = 0
    total_estimated_response_tokens: int = 0
    endpoint_error_counts: dict[str, int] = field(default_factory=dict)
    response_sizes: list[int] = field(default_factory=list)


# ======================================================================
# Scenario Loader
# ======================================================================


def discover_scenarios(scenarios_dir: str | None = None) -> list[ScenarioDefinition]:
    """Discover all scenario modules in the scenarios directory."""
    if scenarios_dir is None:
        scenarios_dir = os.path.join(os.path.dirname(__file__), "scenarios")

    scenarios_path = Path(scenarios_dir)
    if not scenarios_path.exists():
        logger.warning(f"Scenarios directory not found: {scenarios_dir}")
        return []

    scenarios: list[ScenarioDefinition] = []
    for filepath in sorted(scenarios_path.glob("scenario_*.py")):
        module_name = filepath.stem
        # Import the module
        spec = importlib.util.spec_from_file_location(module_name, filepath)
        if spec is None or spec.loader is None:
            logger.warning(f"Could not load scenario module: {filepath}")
            continue

        module = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(module)
        except Exception as exc:
            logger.warning(f"Error loading {filepath}: {exc}")
            continue

        if not hasattr(module, "SCENARIO"):
            logger.warning(f"No SCENARIO dict in {filepath}, skipping")
            continue

        scenario_data = module.SCENARIO
        scenarios.append(ScenarioDefinition(
            name=scenario_data.get("name", module_name),
            description=scenario_data.get("description", ""),
            turns=scenario_data.get("turns", []),
            module_name=module_name,
        ))

    return scenarios


# ======================================================================
# Assertion Engine
# ======================================================================


def _tokenize_json_path(path: str) -> list[str]:
    """Tokenize a JSON path into parts, splitting on dots while preserving bracket groups.

    Examples::
        "phases[0].phase_key"  -> ["phases[0]", "phase_key"]
        "[0].transit_events"   -> ["[0]", "transit_events"]
        "score_summary.overall" -> ["score_summary", "overall"]
        "phases[-1].end_year"  -> ["phases[-1]", "end_year"]
    """
    parts: list[str] = []
    current: list[str] = []
    in_bracket = False
    for ch in path:
        if ch == "[":
            in_bracket = True
            current.append(ch)
        elif ch == "]":
            in_bracket = False
            current.append(ch)
        elif ch == "." and not in_bracket:
            if current:
                parts.append("".join(current).strip())
                current = []
        else:
            current.append(ch)
    if current:
        parts.append("".join(current).strip())
    return [p for p in parts if p]


def _navigate_path(obj: Any, path: str) -> Any:
    """Navigate a dot/bracket path and return the resolved value.

    Used by ``_simple_json_query`` for complex pipe segments.
    """
    import re

    parts = _tokenize_json_path(path)
    current = obj
    for part in parts:
        # key[index] or [index]
        m = re.match(r"^(\w+)?\[(-?\d+)\]$", part)
        if m:
            key = m.group(1)
            idx = int(m.group(2))
            if key:
                if isinstance(current, dict):
                    current = current.get(key)
                else:
                    return None
            if isinstance(current, list):
                try:
                    current = current[idx]
                    continue
                except IndexError:
                    return None
            else:
                return None

        # Plain numeric = list index
        try:
            idx = int(part)
            if isinstance(current, list):
                try:
                    current = current[idx]
                    continue
                except IndexError:
                    return None
            else:
                return None
        except ValueError:
            pass

        # Plain string key
        if isinstance(current, dict):
            current = current.get(part)
        else:
            return None

    return current


class AssertionEngine:
    """Evaluates assertions against response bodies."""

    @staticmethod
    def evaluate(
        assertion: dict[str, Any],
        response_body: Any,
        context: dict[str, str],
    ) -> str | None:
        """Evaluate a single assertion. Returns None on pass, error string on fail."""
        try:
            # Resolve template variables in the assertion values (e.g., ``{chart_id}``),
            # not in the response body — the response is real data from the server.
            resolved_assertion = AssertionEngine._resolve_template(assertion, context)
            return AssertionEngine._evaluate_single(resolved_assertion, response_body)
        except Exception as exc:
            return f"Assertion evaluation error: {exc}"

    @staticmethod
    def _resolve_template(obj: Any, context: dict[str, str]) -> Any:
        """Resolve template variables like ``{chart_id}`` in assertion values."""
        if isinstance(obj, str):
            for key, value in context.items():
                obj = obj.replace("{" + key + "}", value)
            return obj
        elif isinstance(obj, dict):
            return {k: AssertionEngine._resolve_template(v, context) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [AssertionEngine._resolve_template(v, context) for v in obj]
        return obj

    @staticmethod
    def _evaluate_single(assertion: dict[str, Any], body: Any) -> str | None:
        """Evaluate a single assertion against the response body."""
        method = AssertionEngine._get_method(assertion)
        if method is None:
            return f"Unknown assertion type: {list(assertion.keys())}"

        return method(assertion, body)

    @staticmethod
    def _get_method(assertion: dict[str, Any]) -> Any:
        """Dispatch to the correct assertion evaluator based on keys present."""
        if "json_path" in assertion and "equals" in assertion:
            return AssertionEngine._assert_json_path_equals
        elif "json_path" in assertion and "is_none" in assertion:
            return AssertionEngine._assert_json_path_is_none
        elif "json_path" in assertion and "not_none" in assertion:
            return AssertionEngine._assert_json_path_not_none
        elif "json_path" in assertion and "is_list" in assertion:
            return AssertionEngine._assert_json_path_is_list
        elif "json_path" in assertion and "min_length" in assertion and "equals" not in assertion:
            return AssertionEngine._assert_json_path_min_length
        elif "json_path" in assertion and "gte" in assertion:
            return AssertionEngine._assert_json_path_gte
        elif "json_path" in assertion and "gt" in assertion:
            return AssertionEngine._assert_json_path_gt
        elif "json_path" in assertion and "contains" in assertion:
            return AssertionEngine._assert_json_path_contains
        elif "json_query" in assertion and "equals" in assertion:
            return AssertionEngine._assert_json_query_equals
        elif "json_query" in assertion and "gt" in assertion:
            return AssertionEngine._assert_json_query_gt
        elif "json_query" in assertion and "keys_present" in assertion:
            return AssertionEngine._assert_json_query_keys_present
        return None

    @staticmethod
    def _get_json_path(obj: Any, path: str) -> Any:
        """Traverse a dot-delimited JSON path supporting bracket notation.

        Supports:
        - ``score_summary.overall``
        - ``phases[0].phase_key``
        - ``phases[-1].end_year``
        - ``[0].transit_events``
        """
        import re

        parts = _tokenize_json_path(path)
        current = obj
        for part in parts:
            # key[index] or [index]
            m = re.match(r'^(\w+)?\[(-?\d+)\]$', part)
            if m:
                key = m.group(1)
                idx = int(m.group(2))
                if key:
                    if isinstance(current, dict):
                        current = current.get(key)
                    else:
                        return None
                if isinstance(current, list):
                    try:
                        current = current[idx]
                        continue
                    except IndexError:
                        return None
                else:
                    return None

            # Plain numeric = list index
            try:
                idx = int(part)
                if isinstance(current, list):
                    try:
                        current = current[idx]
                        continue
                    except IndexError:
                        return None
                else:
                    return None
            except ValueError:
                pass

            # Plain string key = dict key
            if isinstance(current, dict):
                current = current.get(part)
            else:
                return None

        return current

    @staticmethod
    def _assert_json_path_equals(assertion: dict[str, Any], body: Any) -> str | None:
        path = assertion["json_path"]
        expected = assertion["equals"]
        actual = AssertionEngine._get_json_path(body, path)
        if actual != expected:
            return f"`{path}` expected {expected!r}, got {actual!r}"
        return None

    @staticmethod
    def _assert_json_path_is_none(assertion: dict[str, Any], body: Any) -> str | None:
        path = assertion["json_path"]
        actual = AssertionEngine._get_json_path(body, path)
        if actual is not None:
            return f"`{path}` expected None, got {actual!r}"
        return None

    @staticmethod
    def _assert_json_path_not_none(assertion: dict[str, Any], body: Any) -> str | None:
        path = assertion["json_path"]
        actual = AssertionEngine._get_json_path(body, path)
        if actual is None:
            return f"`{path}` expected non-None, got None"
        return None

    @staticmethod
    def _assert_json_path_is_list(assertion: dict[str, Any], body: Any) -> str | None:
        path = assertion["json_path"]
        actual = AssertionEngine._get_json_path(body, path)
        if not isinstance(actual, list):
            return f"`{path}` expected a list, got {type(actual).__name__}"
        return None

    @staticmethod
    def _assert_json_path_min_length(assertion: dict[str, Any], body: Any) -> str | None:
        path = assertion["json_path"]
        min_len = assertion["min_length"]
        actual = AssertionEngine._get_json_path(body, path)
        if not isinstance(actual, (list, str)):
            return f"`{path}` expected list/string, got {type(actual).__name__}"
        if len(actual) < min_len:
            return f"`{path}` length {len(actual)} < min {min_len}"
        return None

    @staticmethod
    def _assert_json_path_gte(assertion: dict[str, Any], body: Any) -> str | None:
        path = assertion["json_path"]
        threshold = assertion["gte"]
        actual = AssertionEngine._get_json_path(body, path)
        if actual is None or (isinstance(actual, (int, float)) and actual < threshold):
            return f"`{path}` expected >= {threshold}, got {actual!r}"
        return None

    @staticmethod
    def _assert_json_path_gt(assertion: dict[str, Any], body: Any) -> str | None:
        path = assertion["json_path"]
        threshold = assertion["gt"]
        actual = AssertionEngine._get_json_path(body, path)
        if actual is None or (isinstance(actual, (int, float)) and actual <= threshold):
            return f"`{path}` expected > {threshold}, got {actual!r}"
        return None

    @staticmethod
    def _assert_json_path_contains(assertion: dict[str, Any], body: Any) -> str | None:
        path = assertion["json_path"]
        expected = assertion["contains"]
        actual = AssertionEngine._get_json_path(body, path)
        if actual is None or expected not in str(actual):
            return f"`{path}` expected to contain {expected!r}, got {actual!r}"
        return None

    @staticmethod
    def _assert_json_query_equals(assertion: dict[str, Any], body: Any) -> str | None:
        """Simple JSONPath-like query using regex for list filtering.

        Supports queries like ``bodies[?body_key=='sun'].sign | [0]``
        """
        query = assertion["json_query"]
        expected = assertion["equals"]
        actual = AssertionEngine._simple_json_query(query, body)
        if actual != expected:
            return f"query `{query}` expected {expected!r}, got {actual!r}"
        return None

    @staticmethod
    def _assert_json_query_gt(assertion: dict[str, Any], body: Any) -> str | None:
        query = assertion["json_query"]
        threshold = assertion["gt"]
        actual = AssertionEngine._simple_json_query(query, body)
        if actual is None or (isinstance(actual, (int, float)) and actual <= threshold):
            return f"query `{query}` expected > {threshold}, got {actual!r}"
        return None

    @staticmethod
    def _assert_json_query_keys_present(assertion: dict[str, Any], body: Any) -> str | None:
        query = assertion["json_query"]
        keys = assertion["keys_present"]
        actual = AssertionEngine._simple_json_query(query, body)
        if not isinstance(actual, dict):
            return f"query `{query}` expected dict, got {type(actual).__name__}"
        missing = [k for k in keys if k not in actual]
        if missing:
            return f"query `{query}` missing keys: {missing}"
        return None

    @staticmethod
    def _simple_json_query(query: str, body: Any) -> Any:
        """Very basic query parser for common scenario patterns.

        Supports:
        - ``bodies[?body_key=='sun'].sign | [0]``
        - ``aspects[0]``
        - ``transit_events[0].date``
        - ``[0].transit_events[0]``
        """
        # Split on pipe for chaining
        parts = [p.strip() for p in query.split("|")]

        current = body
        for part in parts:
            part = part.strip()

            # Handle list index: aspects[0] or [0]
            if "[" in part and "?" not in part:
                import re

                # key[index] or [index]
                m = re.match(r"^(\w+)?\[(-?\d+)\]$", part)
                if m:
                    key = m.group(1)
                    idx = int(m.group(2))
                    if key:
                        if isinstance(current, dict) and key in current:
                            lst = current[key]
                        else:
                            return None
                    else:
                        # bare [index] — current should already be a list
                        lst = current if isinstance(current, list) else None

                    if isinstance(lst, list):
                        try:
                            current = lst[idx]
                            continue
                        except IndexError:
                            return None
                    # If current is not a list (e.g. a scalar), pass through
                    continue

            # Handle filter query: bodies[?body_key=='sun'].sign
            if "[?" in part:
                import re

                m = re.match(r"^([^\[]+)\[\?([^\]]+)\]\.(.+)$", part)
                if m:
                    list_key = m.group(1)
                    condition = m.group(2)
                    field_key = m.group(3)

                    # Parse condition: body_key=='sun'
                    cond_match = re.match(r"(\w+)\s*==\s*'([^']+)'", condition)
                    if cond_match:
                        cond_field = cond_match.group(1)
                        cond_value = cond_match.group(2)

                        lst = current.get(list_key, []) if isinstance(current, dict) else []
                        for item in lst:
                            if isinstance(item, dict) and item.get(cond_field) == cond_value:
                                current = item.get(field_key)
                                break
                        else:
                            return None
                        continue

            # Handle complex path (e.g., "[0].transit_events[0]")
            # Use _get_json_path-style tokenization for paths without filter queries
            if "." in part or part.startswith("["):
                current = _navigate_path(current, part)
                if current is None:
                    return None
                continue

            # Handle simple field access
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return None

        return current


# ======================================================================
# Scenario Executor
# ======================================================================


class ScenarioExecutor:
    """Executes a single scenario against a target API."""

    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        dry_run: bool = False,
        timeout: float = 30.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.dry_run = dry_run
        self.timeout = timeout
        self.context: dict[str, str] = {}  # extracted values, shared across turns
        self.current_token: str | None = None

    async def execute_scenario(
        self,
        scenario: ScenarioDefinition,
    ) -> ScenarioResult:
        """Execute all turns in a scenario and return results."""
        logger.info(f"▶ Executing scenario: {scenario.name} ({scenario.description})")
        turn_results: list[TurnResult] = []
        total_latency = 0.0
        max_latency = 0.0
        passed = 0
        failed = 0

        async with httpx.AsyncClient(
            base_url=self.base_url,
            timeout=httpx.Timeout(self.timeout),
        ) as client:
            for i, turn in enumerate(scenario.turns):
                result = await self._execute_turn(client, turn, i + 1)
                turn_results.append(result)
                total_latency += result.latency_ms
                max_latency = max(max_latency, result.latency_ms)

                if result.passed:
                    passed += 1
                else:
                    failed += 1

                # Update context with extractions from this turn
                self.context.update(result.extraction)

        avg_latency = total_latency / len(turn_results) if turn_results else 0.0

        scenario_result = ScenarioResult(
            name=scenario.name,
            description=scenario.description,
            turn_results=turn_results,
            total_turns=len(turn_results),
            passed_turns=passed,
            failed_turns=failed,
            total_latency_ms=total_latency,
            max_turn_latency_ms=max_latency,
            avg_turn_latency_ms=avg_latency,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

        status = "✓ PASS" if failed == 0 else f"✗ FAIL ({failed}/{len(turn_results)})"
        logger.info(
            f"  {status} — {passed}/{len(turn_results)} turns passed, "
            f"avg {avg_latency:.0f}ms, max {max_latency:.0f}ms"
        )

        return scenario_result

    async def _execute_turn(
        self,
        client: httpx.AsyncClient,
        turn: dict[str, Any],
        turn_num: int,
    ) -> TurnResult:
        """Execute a single turn/step within a scenario."""
        turn_id = turn.get("id", f"turn_{turn_num}")
        description = turn.get("description", "")
        req_spec = turn.get("request", {})
        expected_status = turn.get("expected_status", 200)
        assertions = turn.get("assertions", [])
        metrics_spec = turn.get("metrics", {})

        logger.info(f"  [{turn_num}] {turn_id}: {description}")

        if self.dry_run:
            return TurnResult(
                turn_id=turn_id,
                description=description,
                status_code=None,
                expected_status=expected_status,
                passed=True,
                latency_ms=0.0,
                error_message=None,
            )

        # Resolve request template variables
        method = req_spec.get("method", "GET").upper()
        path = self._resolve_template(req_spec.get("path", ""), self.context)
        body = req_spec.get("body")
        # Also resolve body template vars
        if body:
            body = self._resolve_template_deep(body, self.context)

        # Calculate request payload size (before sending)
        request_bytes: int | None = None
        if body is not None:
            try:
                request_bytes = len(json.dumps(body, default=str).encode("utf-8"))
            except Exception:
                pass

        # Build headers
        headers: dict[str, str] = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        # Check for custom headers (e.g., for invalid token tests)
        custom_headers = turn.get("custom_headers", {})
        headers.update(custom_headers)

        # Use the current access token if available and no custom auth header set
        auth_check = any("Authorization" in k for k in custom_headers)
        if not auth_check:
            # Check if a specific api_key_ref is specified (for multi-user scenarios)
            api_key_ref = turn.get("api_key_ref")
            if api_key_ref and api_key_ref in self.context:
                headers["Authorization"] = f"Bearer {self.context[api_key_ref]}"
            elif self.context.get("access_token"):
                headers["Authorization"] = f"Bearer {self.context['access_token']}"

        # Track latency
        start_time = time.monotonic()
        error_message: str | None = None
        exception_trace: str | None = None
        response_body: Any = None
        status_code: int | None = None
        assertions_failed: list[str] = []
        assertions_detail: list[dict[str, Any]] = []

        response_text: str | None = None

        try:
            # Send request
            response = await client.request(
                method=method,
                url=path,
                json=body,
                headers=headers,
            )
            latency_ms = (time.monotonic() - start_time) * 1000
            status_code = response.status_code
            response_text = response.text

            # Parse response body
            content_type = response.headers.get("content-type", "")
            if "application/json" in content_type:
                try:
                    response_body = response.json()
                except json.JSONDecodeError:
                    response_body = {"_raw_text": response_text}
            else:
                response_body = {"_raw_text": response_text}

            # Check expected status code
            if status_code != expected_status:
                error_message = (
                    f"Expected status {expected_status}, got {status_code}. "
                    f"Body: {json.dumps(response_body, default=str)[:200]}"
                )
                logger.warning(f"    ✗ {error_message}")

        except httpx.TimeoutException as exc:
            latency_ms = (time.monotonic() - start_time) * 1000
            error_message = f"Request timed out after {self.timeout}s: {exc}"
            exception_trace = traceback.format_exc()
            logger.warning(f"    ✗ {error_message}")
        except Exception as exc:
            latency_ms = (time.monotonic() - start_time) * 1000
            error_message = f"Request error: {exc}"
            exception_trace = traceback.format_exc()
            logger.warning(f"    ✗ {error_message}")

        # ── Calculate response size & preview ──
        response_bytes: int | None = None
        response_preview: str | None = None
        if response_text is not None:
            response_bytes = len(response_text.encode("utf-8"))
            response_preview = response_text[:500]
        elif response_body is not None:
            try:
                raw = json.dumps(response_body, default=str)
                response_bytes = len(raw.encode("utf-8"))
                response_preview = raw[:500]
            except Exception:
                pass

        # ── Token estimates ──
        estimated_prompt_tokens: int | None = None
        if request_bytes is not None:
            estimated_prompt_tokens = max(1, int(request_bytes / TOKEN_ESTIMATE_RATIO))
        estimated_response_tokens: int | None = None
        if response_bytes is not None:
            estimated_response_tokens = max(1, int(response_bytes / TOKEN_ESTIMATE_RATIO))

        # Evaluate assertions (only if request succeeded and we have a body)
        if error_message is None and response_body is not None:
            for assertion in assertions:
                assertion_result = {
                    "assertion": assertion,
                    "passed": False,
                    "error": None,
                }
                err = AssertionEngine.evaluate(assertion, response_body, self.context)
                if err is not None:
                    assertions_failed.append(err)
                    assertion_result["error"] = err
                    logger.warning(f"    ✗ assertion failed: {err}")
                else:
                    assertion_result["passed"] = True
                assertions_detail.append(assertion_result)

        # Collect metrics
        metrics: dict[str, Any] = {}
        if metrics_spec.get("track_latency"):
            metrics["latency_ms"] = latency_ms
        if metrics_spec.get("expected_min_aspects") and isinstance(response_body, dict):
            aspects = response_body.get("aspects", [])
            if isinstance(aspects, list):
                metrics["aspect_count"] = len(aspects)
        if metrics_spec.get("expected_min_aspects") and isinstance(response_body, dict):
            aspects = response_body.get("aspects", [])
            metrics["aspect_count"] = len(aspects) if isinstance(aspects, list) else 0
        if metrics_spec.get("expected_event_count_range") and isinstance(response_body, dict):
            events = response_body.get("transit_events", [])
            metrics["event_count"] = len(events) if isinstance(events, list) else 0
        if metrics_spec.get("expected_phase_count") and isinstance(response_body, dict):
            phases = response_body.get("phases", [])
            metrics["phase_count"] = len(phases) if isinstance(phases, list) else 0

        # Extract values for context
        extraction: dict[str, Any] = {}
        if isinstance(response_body, dict):
            extract_spec = turn.get("extract", {})
            for key, json_path in extract_spec.items():
                value = AssertionEngine._get_json_path(response_body, json_path)
                if value is not None:
                    extraction[key] = str(value)

        passed = (
            error_message is None
            and len(assertions_failed) == 0
            and status_code == expected_status
        )

        if passed:
            logger.info(f"    ✓ passed ({latency_ms:.0f}ms)")

        return TurnResult(
            turn_id=turn_id,
            description=description,
            status_code=status_code,
            expected_status=expected_status,
            passed=passed,
            latency_ms=latency_ms,
            response_body=response_body,
            error_message=error_message,
            extraction=extraction,
            assertions_failed=assertions_failed,
            metrics=metrics,
            request_bytes=request_bytes,
            response_bytes=response_bytes,
            response_preview=response_preview,
            estimated_prompt_tokens=estimated_prompt_tokens,
            estimated_response_tokens=estimated_response_tokens,
            exception_trace=exception_trace,
            assertions_detail=assertions_detail,
        )

    @staticmethod
    def _resolve_template(text: str, context: dict[str, str]) -> str:
        """Replace ``{var}`` placeholders with context values."""
        for key, value in context.items():
            text = text.replace("{" + key + "}", value)
        return text

    @staticmethod
    def _resolve_template_deep(obj: Any, context: dict[str, str]) -> Any:
        """Recursively resolve template variables in dicts/lists/strings."""
        if isinstance(obj, str):
            return ScenarioExecutor._resolve_template(obj, context)
        elif isinstance(obj, dict):
            return {k: ScenarioExecutor._resolve_template_deep(v, context) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [ScenarioExecutor._resolve_template_deep(v, context) for v in obj]
        return obj


# ======================================================================
# Batch Runner
# ======================================================================


class BatchRunner:
    """Runs multiple scenarios, optionally in parallel, and aggregates results."""

    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        dry_run: bool = False,
        parallel: int = 1,
        timeout: float = 30.0,
    ) -> None:
        self.base_url = base_url
        self.dry_run = dry_run
        self.parallel = parallel
        self.timeout = timeout

    async def run_all(
        self,
        scenarios: list[ScenarioDefinition],
    ) -> tuple[list[ScenarioResult], AggregateMetrics]:
        """Run all scenarios and aggregate results."""
        logger.info(
            f"\n{'='*60}\n"
            f"🚀 Running {len(scenarios)} scenarios "
            f"(parallel={self.parallel}, dry_run={self.dry_run})\n"
            f"{'='*60}\n"
        )

        if self.parallel > 1:
            # Run in parallel batches
            results = await self._run_parallel(scenarios)
        else:
            results = await self._run_sequential(scenarios)

        metrics = self._aggregate_metrics(results)
        self._print_summary(results, metrics)

        return results, metrics

    async def _run_sequential(
        self,
        scenarios: list[ScenarioDefinition],
    ) -> list[ScenarioResult]:
        results: list[ScenarioResult] = []
        for scenario in scenarios:
            executor = ScenarioExecutor(
                base_url=self.base_url,
                dry_run=self.dry_run,
                timeout=self.timeout,
            )
            result = await executor.execute_scenario(scenario)
            results.append(result)
        return results

    async def _run_parallel(
        self,
        scenarios: list[ScenarioDefinition],
    ) -> list[ScenarioResult]:
        semaphore = asyncio.Semaphore(self.parallel)

        async def _run_one(scenario: ScenarioDefinition) -> ScenarioResult:
            async with semaphore:
                executor = ScenarioExecutor(
                    base_url=self.base_url,
                    dry_run=self.dry_run,
                    timeout=self.timeout,
                )
                # Each parallel executor needs its own context, so create fresh
                return await executor.execute_scenario(scenario)

        tasks = [_run_one(s) for s in scenarios]
        return await asyncio.gather(*tasks)

    @staticmethod
    def _aggregate_metrics(results: list[ScenarioResult]) -> AggregateMetrics:
        """Compute aggregate metrics across all scenario results."""
        metrics = AggregateMetrics()
        metrics.total_scenarios = len(results)

        chart_latencies: list[float] = []
        aspect_counts: list[int] = []
        validation_errors: list[str] = []

        for scenario_result in results:
            if scenario_result.failed_turns == 0:
                metrics.passed_scenarios += 1
            else:
                metrics.failed_scenarios += 1

            metrics.total_turns += scenario_result.total_turns
            metrics.passed_turns += scenario_result.passed_turns
            metrics.failed_turns += scenario_result.failed_turns
            metrics.total_latency_ms += scenario_result.total_latency_ms
            metrics.max_turn_latency_ms = max(
                metrics.max_turn_latency_ms,
                scenario_result.max_turn_latency_ms,
            )

            for turn in scenario_result.turn_results:
                # ── Enhanced tracking ──
                if turn.request_bytes is not None:
                    metrics.total_request_bytes += turn.request_bytes
                if turn.response_bytes is not None:
                    metrics.total_response_bytes += turn.response_bytes
                if turn.estimated_prompt_tokens is not None:
                    metrics.total_estimated_prompt_tokens += turn.estimated_prompt_tokens
                if turn.estimated_response_tokens is not None:
                    metrics.total_estimated_response_tokens += turn.estimated_response_tokens
                if turn.response_bytes is not None:
                    metrics.response_sizes.append(turn.response_bytes)

                if turn.error_message:
                    validation_errors.append(
                        f"[{scenario_result.name}/{turn.turn_id}] {turn.error_message}"
                    )
                    # Track endpoint error counts
                    metrics.endpoint_error_counts[turn.turn_id] = metrics.endpoint_error_counts.get(turn.turn_id, 0) + 1

                # Collect chart compute latencies
                if "chart" in turn.turn_id and turn.latency_ms > 0:
                    chart_latencies.append(turn.latency_ms)
                # Collect aspect counts
                if "aspect_count" in turn.metrics:
                    aspect_counts.append(turn.metrics["aspect_count"])

        metrics.chart_compute_latencies = chart_latencies
        metrics.validation_errors = validation_errors
        metrics.aspect_counts = aspect_counts

        if metrics.total_turns > 0:
            metrics.avg_turn_latency_ms = metrics.total_latency_ms / metrics.total_turns

        return metrics

    @staticmethod
    def _print_summary(
        results: list[ScenarioResult],
        metrics: AggregateMetrics,
    ) -> None:
        """Print a human-readable summary report."""
        print(f"\n{'='*60}")
        print(f"📊 SCENARIO TEST REPORT")
        print(f"{'='*60}")
        print(f"  Scenarios: {metrics.total_scenarios} total")
        print(f"  Passed:    {metrics.passed_scenarios}")
        print(f"  Failed:    {metrics.failed_scenarios}")
        print(f"  Turns:     {metrics.total_turns} total, "
              f"{metrics.passed_turns} passed, "
              f"{metrics.failed_turns} failed")
        print(f"  Latency:   avg {metrics.avg_turn_latency_ms:.0f}ms, "
              f"max {metrics.max_turn_latency_ms:.0f}ms")

        if metrics.chart_compute_latencies:
            avg_chart = sum(metrics.chart_compute_latencies) / len(metrics.chart_compute_latencies)
            max_chart = max(metrics.chart_compute_latencies)
            print(f"  Chart compute: {len(metrics.chart_compute_latencies)} calls, "
                  f"avg {avg_chart:.0f}ms, max {max_chart:.0f}ms")

        if metrics.aspect_counts:
            avg_aspects = sum(metrics.aspect_counts) / len(metrics.aspect_counts)
            print(f"  Avg aspects per chart: {avg_aspects:.1f}")

        # ── Enhanced reporting ──
        if metrics.total_request_bytes > 0 or metrics.total_response_bytes > 0:
            print(f"  --- Data Transfer ---")
            print(f"  Total request bytes:  {metrics.total_request_bytes:,}")
            print(f"  Total response bytes: {metrics.total_response_bytes:,}")
            if metrics.total_turns > 0:
                avg_req = metrics.total_request_bytes / metrics.total_turns
                avg_res = metrics.total_response_bytes / metrics.total_turns
                print(f"  Avg request/turn:  {avg_req:.0f} bytes")
                print(f"  Avg response/turn: {avg_res:.0f} bytes")

        if metrics.total_estimated_prompt_tokens > 0 or metrics.total_estimated_response_tokens > 0:
            print(f"  --- Token Estimates ---")
            print(f"  Total prompt tokens:   {metrics.total_estimated_prompt_tokens:,}")
            print(f"  Total response tokens: {metrics.total_estimated_response_tokens:,}")
            total_all = metrics.total_estimated_prompt_tokens + metrics.total_estimated_response_tokens
            print(f"  Total tokens (all):    {total_all:,}")

        if metrics.response_sizes:
            sizes = metrics.response_sizes
            max_resp = max(sizes)
            min_resp = min(sizes)
            avg_resp = sum(sizes) / len(sizes)
            print(f"  --- Response Size Analysis ---")
            print(f"  Avg: {avg_resp:.0f} bytes | Min: {min_resp} | Max: {max_resp}")
            # Anomaly detection: responses > 3 standard deviations from mean
            if len(sizes) > 2:
                variance = sum((s - avg_resp) ** 2 for s in sizes) / len(sizes)
                std_dev = variance ** 0.5
                anomalies = [s for s in sizes if abs(s - avg_resp) > 3 * std_dev]
                if anomalies:
                    print(f"  ⚠ Response size anomalies (>3σ): {len(anomalies)} responses")
                    for s in anomalies[:5]:
                        print(f"      {s:,} bytes")

        if metrics.endpoint_error_counts:
            print(f"  --- Error Distribution ---")
            for endpoint, count in sorted(metrics.endpoint_error_counts.items(), key=lambda x: -x[1]):
                print(f"    {endpoint}: {count} error(s)")

        print()

        for idx, sr in enumerate(results):
            status = "✓" if sr.failed_turns == 0 else "✗"
            # Compute per-scenario data transfer
            scenario_req_bytes = sum(t.request_bytes or 0 for t in sr.turn_results)
            scenario_resp_bytes = sum(t.response_bytes or 0 for t in sr.turn_results)
            print(f"  {status} {idx + 1}. {sr.name}: {sr.passed_turns}/{sr.total_turns} turns passed "
                  f"(avg {sr.avg_turn_latency_ms:.0f}ms, {scenario_req_bytes:,}B req/{scenario_resp_bytes:,}B resp)")

        if metrics.validation_errors:
            print(f"\n  ⚠ Validation Errors ({len(metrics.validation_errors)}):")
            for err in metrics.validation_errors[:10]:  # Show first 10
                print(f"    • {err[:150]}")

        print(f"{'='*60}\n")


# ======================================================================
# JSONL Output
# ======================================================================


def write_jsonl(
    results: list[ScenarioResult],
    metrics: AggregateMetrics,
    filepath: str = "scenario_results.jsonl",
) -> str:
    """Write scenario results and metrics to a JSONL file.

    Each line is a JSON object representing either a scenario result or
    the aggregate metrics summary.

    Returns the filepath written to.
    """
    with open(filepath, "w") as f:
        # Write scenario results first
        for sr in results:
            record = {
                "type": "scenario_result",
                "timestamp": sr.timestamp,
                "scenario": sr.name,
                "description": sr.description,
                "total_turns": sr.total_turns,
                "passed_turns": sr.passed_turns,
                "failed_turns": sr.failed_turns,
                "total_latency_ms": round(sr.total_latency_ms, 2),
                "avg_turn_latency_ms": round(sr.avg_turn_latency_ms, 2),
                "max_turn_latency_ms": round(sr.max_turn_latency_ms, 2),
                "turns": [
                    {
                        "id": t.turn_id,
                        "description": t.description,
                        "passed": t.passed,
                        "status_code": t.status_code,
                        "expected_status": t.expected_status,
                        "latency_ms": round(t.latency_ms, 2),
                        "error": t.error_message,
                        "assertions_failed": t.assertions_failed,
                        "metrics": t.metrics,
                        # Enhanced fields
                        "request_bytes": t.request_bytes,
                        "response_bytes": t.response_bytes,
                        "response_preview": t.response_preview[:200] if t.response_preview else None,
                        "estimated_prompt_tokens": t.estimated_prompt_tokens,
                        "estimated_response_tokens": t.estimated_response_tokens,
                        "exception_trace": t.exception_trace,
                        "assertions_detail": [
                            {k: v for k, v in ad.items() if k != "assertion"}
                            for ad in t.assertions_detail
                        ],
                    }
                    for t in sr.turn_results
                ],
            }
            f.write(json.dumps(record, default=str) + "\n")

        # Write aggregate metrics as the last line
        agg_line = {
            "type": "aggregate_metrics",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "total_scenarios": metrics.total_scenarios,
            "passed_scenarios": metrics.passed_scenarios,
            "failed_scenarios": metrics.failed_scenarios,
            "total_turns": metrics.total_turns,
            "passed_turns": metrics.passed_turns,
            "failed_turns": metrics.failed_turns,
            "total_latency_ms": round(metrics.total_latency_ms, 2),
            "avg_turn_latency_ms": round(metrics.avg_turn_latency_ms, 2),
            "max_turn_latency_ms": round(metrics.max_turn_latency_ms, 2),
            "chart_compute_latencies": [round(l, 2) for l in metrics.chart_compute_latencies],
            "avg_chart_latency_ms": round(
                sum(metrics.chart_compute_latencies) / len(metrics.chart_compute_latencies), 2
            ) if metrics.chart_compute_latencies else None,
            "aspect_counts": metrics.aspect_counts,
            "avg_aspect_count": round(
                sum(metrics.aspect_counts) / len(metrics.aspect_counts), 1
            ) if metrics.aspect_counts else None,
            "validation_errors": metrics.validation_errors[:20],  # cap at 20
            # Enhanced aggregate fields
            "total_request_bytes": metrics.total_request_bytes,
            "total_response_bytes": metrics.total_response_bytes,
            "total_estimated_prompt_tokens": metrics.total_estimated_prompt_tokens,
            "total_estimated_response_tokens": metrics.total_estimated_response_tokens,
            "avg_response_size_bytes": round(
                sum(metrics.response_sizes) / len(metrics.response_sizes), 1
            ) if metrics.response_sizes else None,
            "max_response_size_bytes": max(metrics.response_sizes) if metrics.response_sizes else None,
            "min_response_size_bytes": min(metrics.response_sizes) if metrics.response_sizes else None,
            "endpoint_error_counts": metrics.endpoint_error_counts,
        }
        f.write(json.dumps(agg_line, default=str) + "\n")

    logger.info(f"📄 Results written to {filepath}")
    return filepath


# ======================================================================
# CLI entry point
# ======================================================================


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Scenario-based integration test runner for Astrology Agent API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--base-url",
        default="http://localhost:8000",
        help="Base URL of the target API (default: http://localhost:8000)",
    )
    parser.add_argument(
        "--scenario",
        default=None,
        help="Run only a specific scenario by name",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate scenario definitions without sending requests",
    )
    parser.add_argument(
        "--parallel",
        type=int,
        default=1,
        help="Number of scenarios to run in parallel (default: 1)",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=30.0,
        help="Request timeout in seconds (default: 30)",
    )
    parser.add_argument(
        "--output",
        default="scenario_results.jsonl",
        help="Output JSONL file path (default: scenario_results.jsonl)",
    )
    parser.add_argument(
        "--scenarios-dir",
        default=None,
        help="Directory containing scenario files (default: tests/scenarios)",
    )
    return parser.parse_args(argv)


async def main(argv: list[str] | None = None) -> int:
    """Main entry point. Returns 0 on success, 1 on failure."""
    args = parse_args(argv)

    # Discover scenarios
    all_scenarios = discover_scenarios(args.scenarios_dir)

    if not all_scenarios:
        logger.error("No scenarios found. Check --scenarios-dir or working directory.")
        return 1

    # Filter by name if specified
    if args.scenario:
        filtered = [s for s in all_scenarios if s.name == args.scenario]
        if not filtered:
            logger.error(f"Scenario '{args.scenario}' not found. Available: {[s.name for s in all_scenarios]}")
            return 1
        scenarios = filtered
    else:
        scenarios = all_scenarios

    logger.info(f"Loaded {len(scenarios)} scenario(s):")
    for s in scenarios:
        logger.info(f"  • {s.name}: {s.description} ({len(s.turns)} turns)")

    # Run
    runner = BatchRunner(
        base_url=args.base_url,
        dry_run=args.dry_run,
        parallel=args.parallel,
        timeout=args.timeout,
    )
    results, metrics = await runner.run_all(scenarios)

    # Write JSONL
    write_jsonl(results, metrics, args.output)

    # Return exit code
    if metrics.failed_scenarios > 0 or metrics.failed_turns > 0:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
