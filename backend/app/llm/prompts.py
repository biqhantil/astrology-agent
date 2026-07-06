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
You have access to astrological chart tools that can compute and render visual data. \
When a user asks about their chart, transits, compatibility, or life phases, use the \
appropriate tool to generate detailed astrological data.

Available tools:
1. **render_natal_chart** — Compute and display the user's natal (birth) chart. \
   Use when a user asks about their birth chart, placements, or general self-understanding.
2. **render_transit_timeline** — Show current or upcoming transits against the natal chart. \
   Use for time-specific questions, forecasting, and "what's happening now" queries.
3. **render_synastry** — Compare two charts for relationship compatibility analysis. \
   Use when comparing two people's charts.
4. **render_life_phases** — Show major life phase milestones (Saturn returns, \
   Uranus opposition, Chiron return, etc.). \
   Use for life-path, timing, and "what phase am I in" questions.

## Response Style
- Begin with a meaningful observation that connects to the user's situation
- Provide layered insights — start with the big picture, then go deeper
- End with practical, actionable wisdom
- Keep responses concise but rich (2–4 paragraphs is ideal)
- Use **markdown** for readability (bold for key terms, bullet points for lists)

## Important Guidelines
- Never claim to predict specific events with certainty
- Always acknowledge the complexity of a full chart reading
- If you don't have enough information, ask clarifying questions
- Use tools when visual data would enhance the response
- When you use a tool, integrate the returned data into your interpretation naturally
"""


# ── Chart context injection ─────────────────────────────────────


def build_system_prompt(
    chart_context: dict[str, Any] | None = None,
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

    Returns
    -------
    str
        The complete system prompt with injected chart data.
    """
    if not chart_context:
        return BASE_SYSTEM_PROMPT

    # Start with base prompt and add a chart context section
    parts = [
        BASE_SYSTEM_PROMPT,
        "\n\n## Current Chart Context",
    ]

    # Chart type
    chart_type = chart_context.get("chart_type", "natal")
    parts.append(f"\nChart type: **{chart_type.upper()}**")

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

    # Aspects
    aspects = chart_context.get("aspects", [])
    if aspects:
        parts.append("\n### Aspects\n")
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
