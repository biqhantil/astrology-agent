"""Deterministic mock LLM for harness runs and offline development.

Keyword-driven scripted turns that can emit tool calls, so multi-turn
conversation scenarios exercise the full messages → tools → SSE path
without OpenCode credits.
"""

from __future__ import annotations

import re
import uuid
from typing import Any

from app.llm.client import LLMResponse


def _tc(name: str, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "id": f"call_{uuid.uuid4().hex[:12]}",
        "type": "function",
        "function": {
            "name": name,
            "arguments": arguments or {},
        },
    }


def _last_user_text(messages: list[dict[str, Any]]) -> str:
    for msg in reversed(messages):
        if msg.get("role") == "user" and msg.get("content"):
            return str(msg["content"]).lower()
    return ""


def _has_tool_results(messages: list[dict[str, Any]]) -> bool:
    return any(m.get("role") == "tool" for m in messages)


def _last_tool_names(messages: list[dict[str, Any]]) -> list[str]:
    names: list[str] = []
    for msg in messages:
        if msg.get("role") == "assistant" and msg.get("tool_calls"):
            for tc in msg["tool_calls"]:
                fn = tc.get("function") or {}
                n = fn.get("name")
                if n:
                    names.append(n)
    return names


async def mock_chat_completion(
    messages: list[dict[str, Any]],
    system_prompt: str | None = None,
    tools: list[dict[str, Any]] | None = None,
    **_kwargs: Any,
) -> LLMResponse:
    """Scripted OpenAI-compatible completion used when ``LLM_MODE=mock``."""
    user = _last_user_text(messages)
    tools_present = bool(tools)
    after_tools = _has_tool_results(messages)
    used = _last_tool_names(messages)

    # After tools ran, always synthesize a text answer
    if after_tools:
        if "render_transit_timeline" in used:
            return LLMResponse(
                content=(
                    "I've reviewed the current sky against your natal chart. "
                    "Key transit themes: tension around work/structure (Saturn tones) "
                    "and opportunity for connection (Venus/Jupiter aspects). "
                    "Stay grounded this week and note emotional peaks mid-week."
                )
            )
        if "render_natal_chart" in used:
            return LLMResponse(
                content=(
                    "Your natal chart highlights a strong identity signature through the Sun "
                    "and emotional patterning via the Moon. The Ascendant frames how you meet "
                    "the world. Focus on integrating house themes rather than any single planet."
                )
            )
        if "render_life_phases" in used:
            return LLMResponse(
                content=(
                    "You appear between major life milestones. The current phase emphasizes "
                    "consolidation and intentional growth before the next outer-planet trigger."
                )
            )
        if "render_synastry" in used:
            return LLMResponse(
                content=(
                    "The synastry comparison shows complementary dynamics in emotional and "
                    "communication areas, with some friction in autonomy/control themes. "
                    "Conscious dialogue turns the hard aspects into growth."
                )
            )
        return LLMResponse(
            content=(
                "I've consulted the chart tools and synthesized the main patterns. "
                "Ask a follow-up if you want a deeper house-by-house or transit window."
            )
        )

    # First-pass: decide tools vs pure text
    wants_natal = bool(
        re.search(r"\b(natal|birth chart|meu mapa|mapa natal|placements|my chart)\b", user)
    )
    wants_transit = bool(
        re.search(
            r"\b(today|daily|di[aá]rio|tr[aâ]nsit|forecast|hoje|semanal|weekly|current sky)\b",
            user,
        )
    )
    wants_phases = bool(
        re.search(r"\b(life phase|saturn return|retorno de saturno|fase da vida)\b", user)
    )
    wants_synastry = bool(
        re.search(r"\b(synastry|compatib|relacionamento|partner|compar)\b", user)
    )

    if tools_present and wants_transit and not after_tools:
        # chart_id left empty → execute_tool should resolve from user's natal
        return LLMResponse(
            content=None,
            tool_calls=[
                _tc(
                    "render_transit_timeline",
                    {
                        "start_date": "2026-07-01",
                        "end_date": "2026-07-31",
                    },
                )
            ],
        )

    if tools_present and wants_natal and not after_tools:
        return LLMResponse(
            content=None,
            tool_calls=[_tc("render_natal_chart", {})],
        )

    if tools_present and wants_phases and not after_tools:
        return LLMResponse(
            content=None,
            tool_calls=[_tc("render_life_phases", {})],
        )

    if tools_present and wants_synastry and not after_tools:
        return LLMResponse(
            content=(
                "To compare charts I need two chart IDs. "
                "Create a partner chart first, then ask again with both IDs."
            )
        )

    # Generic multi-turn friendly text
    if re.search(r"\b(follow.?up|more detail|deeper|mais detalhe|continue)\b", user):
        return LLMResponse(
            content=(
                "Going deeper: the previous themes intensify when personal planets "
                "activate angular houses. Practical step: journal one concrete action "
                "aligned with your Sun-sign element this week."
            )
        )

    if re.search(r"\b(hello|hi|ola|olá|hey)\b", user):
        return LLMResponse(
            content=(
                "Welcome. I can read your natal chart, current transits, life phases, "
                "or relationship synastry. What would you like to explore?"
            )
        )

    return LLMResponse(
        content=(
            "I've considered your question through an astrological lens. "
            "Share a birth profile if you haven't, then ask about your natal chart, "
            "today's transits, or a life-phase window for a more precise reading."
        )
    )
