"""System prompt templates for the astrology LLM.

Includes chart context injection — when a ``chart_context`` dict is available,
planet positions, houses, and aspects are formatted and injected into the prompt
so the LLM can deliver readings grounded in the user's actual chart data.
"""

from __future__ import annotations

from typing import Any

# ── Base system prompt ──────────────────────────────────────────

BASE_SYSTEM_PROMPT = """\
You are a wise, insightful astrologer with deep knowledge of both traditional and modern astrology. \
Your purpose is to help users understand their birth chart, current transits, life phases, and \
compatibility with others.

## Your Role
- Speak with the wisdom of someone who has studied the stars for decades
- Be compassionate, honest, and nuanced — astrology reveals patterns, not absolutes
- Connect celestial placements to real-life experiences and psychological insights
- Use astrological terminology naturally, but explain concepts when helpful
- When interpreting, consider **sign, house, aspect, and dignity** together

## Available Tools
You have access to astrological chart tools that compute precise data. Use them when they add \
grounding beyond the injected chart context.

Available tools:
1. **render_natal_chart** — Compute natal chart. Skip if "Current Chart Context" already has bodies.
2. **render_transit_timeline** — Transits vs natal for a date range. Use for today/week/month forecasts. \
   chart_id is optional (defaults to the user's natal). Prefer start_date/end_date covering the asked window.
3. **render_synastry** — Compare two charts (needs two chart IDs).
4. **render_life_phases** — Saturn returns and major life phases.

## Tool Discipline
- Prefer **one tool call** when possible; do not re-call the same tool with the same args.
- If chart context is already injected below, **use those placements** for natal interpretation — \
do **not** call render_natal_chart again (it may not even be available).
- For daily/weekly forecasts: call **render_transit_timeline** once (chart_id optional), then interpret.
- For follow-ups that only rephrase prior answers: answer from conversation history — no new tools.
- Never ask the user for birth data when chart context or a successful tool result is already available.
- Cite at least one concrete body + sign/house/aspect from data (injected or tool result).

## Response Style
- Begin with a meaningful observation connected to the user's situation
- Layer insights: big picture → specifics → practical guidance
- Keep multi-turn answers coherent with prior turns
- Use **markdown** (bold key terms, short lists)
- **Language is mandatory:** reply in the **same language as the latest user message**. \
English question → English answer. Portuguese question → Portuguese answer. \
Do not switch languages mid-thread unless the user switches.
- **Length:** match answer length to the question. Narrow follow-ups (one planet, one tip) → \
~1 short screen (roughly 120–250 words). Full chart / multi-theme asks may be longer, still scannable.
- Prefer progressive disclosure: answer the ask first; offer deeper layers only if useful.

## Tool Intent
- **render_life_phases** only when the user asks about life phase, Saturn return, timing eras, or "what phase am I in".
- Do **not** call life_phases for general natal overview, Moon, career, or daily forecast.

## Important Guidelines
- Never claim certain prediction of specific events
- Prefer tool-grounded specifics over generic horoscope language
- When tool results include errors (e.g. missing chart), explain briefly and recover
"""


# ── Chart context injection ─────────────────────────────────────


def build_system_prompt(
    chart_context: dict[str, Any] | None = None,
    *,
    chart_id: str | None = None,
    today: str | None = None,
) -> str:
    """Build the full system prompt, optionally including injected chart data.

    Parameters
    ----------
    chart_context : dict or None
        If provided, should contain keys:
        - ``chart_type``: str
        - ``bodies``: list of body dicts (with ``body_key``, ``sign``,
          ``sign_degree``, ``house``, ``dignity``)
        - ``houses``: list of house dicts (with ``house_number``, ``sign``,
          ``sign_degree``)
        - ``aspects``: list of aspect dicts (with ``body_a``, ``body_b``,
          ``aspect``, ``orb``)
    chart_id : str or None
        UUID of the conversation's natal chart for transit tools.
    today : str or None
        ISO date string for relative transit windows.

    Returns
    -------
    str
        The complete system prompt with injected chart data.
    """
    from datetime import date as _date

    today = today or _date.today().isoformat()

    if not chart_context:
        parts = [BASE_SYSTEM_PROMPT, f"\n\n## Session\nToday's date: **{today}**"]
        return "\n".join(parts)

    # Start with base prompt and add a chart context section
    parts = [
        BASE_SYSTEM_PROMPT,
        "\n\n## Session",
        f"\nToday's date: **{today}**",
    ]
    if chart_id:
        parts.append(
            f"\nNatal chart_id for tools: `{chart_id}` "
            "(pass this to render_transit_timeline; do **not** call render_natal_chart again)."
        )
    parts.append("\n\n## Current Chart Context")

    # Chart type
    chart_type = chart_context.get("chart_type", "natal")
    parts.append(f"\nChart type: **{chart_type.upper()}**")
    parts.append(
        "\nNatal placements are already loaded below — use them for interpretation. "
        "Only call tools for **new** data (e.g. transits or life phases)."
    )

    # Bodies (planets and points)
    bodies = chart_context.get("bodies", [])
    if bodies:
        parts.append("\n### Planetary Placements\n")
        parts.append("| Body | Sign | Degree | House | Dignity |")
        parts.append("|------|------|--------|-------|---------|")
        for b in bodies:
            sign = b.get("sign", "")
            deg = b.get("sign_degree", "")
            house = b.get("house", "") or ""
            dignity = b.get("dignity", "") or ""
            parts.append(
                f"| {b.get('body_key', '')} | {sign} | {deg}° | {house} | {dignity} |"
            )

    # Houses
    houses = chart_context.get("houses", [])
    if houses:
        parts.append("\n### House Cusps\n")
        parts.append("| House | Sign | Cusp Degree |")
        parts.append("|-------|------|-------------|")
        for h in houses:
            parts.append(
                f"| {h.get('house_number', '')} | {h.get('sign', '')} | {h.get('sign_degree', '')}° |"
            )

    # Aspects (cap to top 12 by orb to limit prompt tokens)
    aspects = list(chart_context.get("aspects", []) or [])
    try:
        aspects = sorted(aspects, key=lambda a: float(a.get("orb") or 99))[:12]
    except (TypeError, ValueError):
        aspects = aspects[:12]
    if aspects:
        parts.append("\n### Key Aspects (tightest orbs)\n")
        parts.append("| Body A | Body B | Aspect | Orb |")
        parts.append("|--------|--------|--------|-----|")
        for a in aspects:
            parts.append(
                f"| {a.get('body_a', '') or a.get('body_a_key', '')} "
                f"| {a.get('body_b', '') or a.get('body_b_key', '')} "
                f"| {a.get('aspect', '') or a.get('aspect_type', '')} "
                f"| {a.get('orb', '')}° |"
            )

    return "\n".join(parts)


# ── Convenience formatters ──────────────────────────────────────


def format_bodies_for_prompt(bodies: list[dict[str, Any]]) -> str:
    """Format a list of chart bodies into a concise text block for prompt injection."""
    lines = ["### Planetary Placements"]
    for b in bodies:
        lines.append(
            f"- {b.get('body_key', '?')}: {b.get('sign', '?')} {b.get('sign_degree', '')}° "
            f"House {b.get('house', '?')} "
            f"({b.get('dignity', '')})"
        )
    return "\n".join(lines)


def format_aspects_for_prompt(aspects: list[dict[str, Any]]) -> str:
    """Format a list of aspects into a concise text block for prompt injection."""
    if not aspects:
        return "### Aspects\nNone."
    lines = ["### Key Aspects"]
    for a in aspects:
        lines.append(
            f"- {a.get('body_a', '') or a.get('body_a_key', '')} "
            f"{a.get('aspect', '') or a.get('aspect_type', '')} "
            f"{a.get('body_b', '') or a.get('body_b_key', '')} "
            f"(orb: {a.get('orb', '')}°)"
        )
    return "\n".join(lines)
