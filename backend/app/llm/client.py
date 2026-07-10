"""Async HTTP client for the OpenCode Go API (OpenAI-compatible chat completions).

Uses ``httpx.AsyncClient`` for streaming HTTP requests.
Config from pydantic settings: OPENCODE_API_KEY, OPENCODE_API_BASE, OPENCODE_MODEL.
"""

from __future__ import annotations

import json
from typing import Any

import httpx

from app.config import settings

# ── Defaults (overridable via env) ──────────────────────────────

DEFAULT_MAX_TOKENS = 4096
DEFAULT_TIMEOUT = 120.0


class LLMProviderError(RuntimeError):
    """Raised when the upstream LLM API fails (auth, credits, network)."""

    def __init__(self, status_code: int, detail: str) -> None:
        self.status_code = status_code
        self.detail = detail
        super().__init__(detail)


def _friendly_provider_error(status_code: int, body: str) -> str:
    lower = body.lower()
    if "insufficient balance" in lower or "credits" in lower or "billing" in lower:
        return (
            "LLM provider rejected the request: insufficient credits/balance. "
            "Top up OpenCode billing at the workspace billing URL, then retry. "
            "Multi-turn harness requires a live funded key."
        )
    if status_code in (401, 403):
        return (
            "LLM provider authentication failed. Check OPENCODE_API_KEY in backend/.env "
            "and ensure LLM_MODE=live."
        )
    return f"LLM provider error ({status_code}): {body[:400]}"


def _api_key() -> str:
    return settings.OPENCODE_API_KEY or ""


def _api_base() -> str:
    base = (settings.OPENCODE_API_BASE or "https://opencode.ai/zen/go/v1").rstrip("/")
    # Allow full chat/completions URL in env — strip to base
    if base.endswith("/chat/completions"):
        base = base[: -len("/chat/completions")].rstrip("/")
    return base


def _model() -> str:
    return settings.OPENCODE_MODEL or "deepseek-v4-flash"


# ── Response model ──────────────────────────────────────────────


class LLMResponse:
    """Parsed response from an LLM call."""

    def __init__(
        self,
        content: str | None = None,
        tool_calls: list[dict] | None = None,
        usage: dict[str, Any] | None = None,
    ) -> None:
        self.content = content
        self.tool_calls = tool_calls
        # OpenAI-style usage when the provider sends it (stream final chunk)
        self.usage = usage or {}

    def __repr__(self) -> str:
        return (
            f"LLMResponse(content={self.content!r}, "
            f"tool_calls={self.tool_calls!r}, usage={self.usage!r})"
        )


# ── Public API ──────────────────────────────────────────────────


async def chat_completion(
    messages: list[dict[str, Any]],
    system_prompt: str | None = None,
    tools: list[dict[str, Any]] | None = None,
    *,
    model: str | None = None,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    timeout: float = DEFAULT_TIMEOUT,
    on_token: Any | None = None,
) -> LLMResponse:
    """Send a chat completion request (streaming) and return the assembled response."""
    mode = (settings.LLM_MODE or "live").strip().lower()
    if mode == "mock":
        from app.llm.mock_client import mock_chat_completion

        return await mock_chat_completion(
            messages=messages,
            system_prompt=system_prompt,
            tools=tools,
            model=model or _model(),
            max_tokens=max_tokens,
            on_token=on_token,
        )

    api_key = _api_key()
    if not api_key:
        raise RuntimeError(
            "OPENCODE_API_KEY is not set. "
            "Add it to backend/.env and use LLM_MODE=live."
        )

    full_messages: list[dict[str, Any]] = list(messages)
    if system_prompt:
        full_messages.insert(0, {"role": "system", "content": system_prompt})

    body: dict[str, Any] = {
        "model": model or _model(),
        "messages": full_messages,
        "stream": True,
        "max_tokens": max_tokens,
    }
    if tools:
        body["tools"] = tools

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Accept": "text/event-stream",
    }

    url = f"{_api_base()}/chat/completions"

    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(timeout)) as client:
            async with client.stream(
                "POST",
                url,
                json=body,
                headers=headers,
            ) as response:
                if response.status_code >= 400:
                    err_text = ""
                    try:
                        err_text = (await response.aread()).decode("utf-8", errors="replace")
                    except Exception:
                        err_text = response.reason_phrase
                    raise LLMProviderError(
                        status_code=response.status_code,
                        detail=_friendly_provider_error(response.status_code, err_text),
                    )
                return await _parse_stream(response, on_token=on_token)
    except LLMProviderError:
        raise
    except httpx.TimeoutException as exc:
        raise LLMProviderError(
            status_code=504,
            detail="LLM provider timed out. Try again.",
        ) from exc
    except httpx.HTTPError as exc:
        raise LLMProviderError(
            status_code=502,
            detail=f"LLM provider network error: {exc}",
        ) from exc


# ── Internal helpers ────────────────────────────────────────────


async def _parse_stream(
    response: httpx.Response,
    *,
    on_token: Any | None = None,
) -> LLMResponse:
    """Parse an SSE stream; accumulate content (and reasoning as fallback).

    deepseek-v4-flash may stream ``reasoning_content`` first, then ``content``.
    User-facing text uses ``content`` only; if content stays empty, fall back
    to reasoning so we never return a blank assistant message.
    """
    content_parts: list[str] = []
    reasoning_parts: list[str] = []
    tool_calls: dict[int, dict[str, Any]] = {}
    usage: dict[str, Any] = {}

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

        # Usage often arrives on a late chunk (sometimes with empty choices)
        chunk_usage = chunk.get("usage")
        if isinstance(chunk_usage, dict) and chunk_usage:
            usage = chunk_usage

        choices = chunk.get("choices", [])
        if not choices:
            continue

        delta = choices[0].get("delta", {})
        finish_reason = choices[0].get("finish_reason")

        content = delta.get("content")
        if content is not None:
            content_parts.append(content)
            if on_token is not None:
                await on_token(content)

        reasoning = delta.get("reasoning_content")
        if reasoning:
            reasoning_parts.append(reasoning)

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

        if finish_reason in ("stop", "tool_calls", "end_turn"):
            # Don't break early on null finish — some providers send more chunks
            if finish_reason == "stop" and content_parts:
                break
            if finish_reason in ("tool_calls", "end_turn"):
                break

    content = "".join(content_parts).strip() if content_parts else None
    if not content and reasoning_parts:
        # Fallback only if the model produced no public content
        content = "".join(reasoning_parts).strip() or None

    tc_list = list(tool_calls.values()) if tool_calls else None

    # Keep ``arguments`` as a JSON *string* in tool_calls so multi-turn
    # history can be re-sent to OpenAI-compatible APIs. Callers that need a
    # dict should parse a copy (see messages.execute_tool path).
    if tc_list:
        for tc in tc_list:
            args_str = tc["function"].get("arguments") or ""
            if not isinstance(args_str, str):
                tc["function"]["arguments"] = json.dumps(args_str)
            # Ensure empty args are valid JSON object string
            elif args_str.strip() == "":
                tc["function"]["arguments"] = "{}"

    return LLMResponse(content=content, tool_calls=tc_list, usage=usage)
