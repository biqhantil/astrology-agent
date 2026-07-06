"""Async HTTP client for the OpenCode Go API (OpenAI-compatible chat completions).

Uses ``httpx.AsyncClient`` for streaming HTTP requests.
API key is read from the ``OPENCODE_API_KEY`` environment variable.
"""

from __future__ import annotations

import json
import os
from typing import Any

import httpx

# ── Constants ───────────────────────────────────────────────────

OPENCODE_API_BASE = "https://api.opencode.go/v1"
OPENCODE_MODEL = "deepseek-v4-flash"
DEFAULT_MAX_TOKENS = 4096
DEFAULT_TIMEOUT = 120.0

# API key from environment
API_KEY: str = os.environ.get("OPENCODE_API_KEY", "")


# ── Response model ──────────────────────────────────────────────


class LLMResponse:
    """Parsed response from an LLM call.

    Attributes
    ----------
    content : str | None
        The text content of the assistant's reply, or ``None`` if
        the response contains only tool calls.
    tool_calls : list[dict] | None
        A list of tool call dicts following OpenAI format:
        ``[{"id": "...", "type": "function", "function": {"name": "...", "arguments": {...}}}, ...]``
        ``None`` if no tool calls were made.
    """

    def __init__(
        self,
        content: str | None = None,
        tool_calls: list[dict] | None = None,
    ) -> None:
        self.content = content
        self.tool_calls = tool_calls

    def __repr__(self) -> str:
        return (
            f"LLMResponse(content={self.content!r}, "
            f"tool_calls={self.tool_calls!r})"
        )


# ── Public API ──────────────────────────────────────────────────


async def chat_completion(
    messages: list[dict[str, Any]],
    system_prompt: str | None = None,
    tools: list[dict[str, Any]] | None = None,
    *,
    model: str = OPENCODE_MODEL,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    timeout: float = DEFAULT_TIMEOUT,
) -> LLMResponse:
    """Send a chat completion request (streaming) and return the assembled response.

    Parameters
    ----------
    messages : list[dict]
        The conversation messages so far in OpenAI format::

            {"role": "user" | "assistant" | "tool",
             "content": str | None,
             "tool_calls": [...] | None,
             "tool_call_id": str | None}

    system_prompt : str or None
        If provided, inserted as a ``system`` message at the start.
    tools : list[dict] or None
        JSON Schema tool definitions in OpenAI format.
    model : str
        Model identifier (default ``deepseek-v4-flash``).
    max_tokens : int
        Maximum tokens in the response.
    timeout : float
        HTTP request timeout in seconds.

    Returns
    -------
    LLMResponse
        Parsed content and/or tool_calls from the assistant.

    Raises
    ------
    RuntimeError
        If ``OPENCODE_API_KEY`` is not set.
    httpx.HTTPStatusError
        If the API returns a non-2xx status.
    """
    if not API_KEY:
        raise RuntimeError(
            "OPENCODE_API_KEY environment variable is not set. "
            "Set it to your OpenCode Go API key before starting the server."
        )

    # Build the full message list
    full_messages: list[dict[str, Any]] = list(messages)
    if system_prompt:
        full_messages.insert(0, {"role": "system", "content": system_prompt})

    # Build the request body
    body: dict[str, Any] = {
        "model": model,
        "messages": full_messages,
        "stream": True,
        "max_tokens": max_tokens,
    }
    if tools:
        body["tools"] = tools

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
        "Accept": "text/event-stream",
    }

    async with httpx.AsyncClient(timeout=httpx.Timeout(timeout)) as client:
        async with client.stream(
            "POST",
            f"{OPENCODE_API_BASE}/chat/completions",
            json=body,
            headers=headers,
        ) as response:
            response.raise_for_status()
            return await _parse_stream(response)


# ── Internal helpers ────────────────────────────────────────────


async def _parse_stream(response: httpx.Response) -> LLMResponse:
    """Parse an SSE stream from the API and accumulate the full response."""
    content_parts: list[str] = []
    tool_calls: dict[int, dict[str, Any]] = {}

    async for line in response.aiter_lines():
        if not line.startswith("data: "):
            continue

        data_str = line[len("data: "):].strip()
        if data_str == "[DONE]":
            break

        try:
            chunk = json.loads(data_str)
        except json.JSONDecodeError:
            continue

        choices = chunk.get("choices", [])
        if not choices:
            continue

        delta = choices[0].get("delta", {})
        finish_reason = choices[0].get("finish_reason")

        # Accumulate text content
        content = delta.get("content")
        if content is not None:
            content_parts.append(content)

        # Accumulate tool calls (streaming chunks)
        raw_tool_calls = delta.get("tool_calls")
        if raw_tool_calls:
            for tc in raw_tool_calls:
                idx = tc.get("index", 0)
                if idx not in tool_calls:
                    tool_calls[idx] = {
                        "id": tc.get("id", ""),
                        "type": "function",
                        "function": {"name": "", "arguments": ""},
                    }
                existing = tool_calls[idx]

                if "id" in tc and tc["id"]:
                    existing["id"] = tc["id"]

                fn = tc.get("function")
                if fn:
                    if "name" in fn and fn["name"]:
                        existing["function"]["name"] += fn["name"]
                    if "arguments" in fn and fn["arguments"]:
                        existing["function"]["arguments"] += fn["arguments"]

        if finish_reason == "stop":
            break

    content = "".join(content_parts) if content_parts else None
    tc_list = list(tool_calls.values()) if tool_calls else None

    # Parse ``arguments`` JSON string for each tool call
    if tc_list:
        for tc in tc_list:
            args_str = tc["function"]["arguments"]
            if isinstance(args_str, str):
                try:
                    tc["function"]["arguments"] = json.loads(args_str)
                except (json.JSONDecodeError, TypeError):
                    pass

    return LLMResponse(content=content, tool_calls=tc_list)
