"""Message router — send messages and list conversation history.

POST /v1/conversations/{conversation_id}/messages
  - Creates a user message in DB
  - Calls the real LLM via ``app.llm.client``
  - Handles tool calls via ``app.llm.tools``
  - Stores assistant message(s) in DB
  - Publishes to SSE streams
  - Returns both messages

GET /v1/conversations/{conversation_id}/messages
  - Paginated list of all messages in a conversation
"""

from __future__ import annotations

import json
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.auth import AuthPayload, require_user
from app.core.deps import get_conn
from app.core.sse_manager import publish
from app.llm import (
    LLMProviderError,
    LLMResponse,
    chat_completion,
    build_system_prompt,
    TOOL_DEFINITIONS,
    execute_tool,
)

# ── Domain schemas (colocated) ────────────────────────────────────
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


# ── Request ─────────────────────────────────────────────────────

class MessageCreate(BaseModel):
    """Send a new user message in a conversation.

    The ``role`` is always ``"user"`` for client submissions.
    ``content`` is the visible markdown text of the message.
    """

    role: str = Field(default="user", pattern="^(system|user|assistant|tool)$")
    content: str


# ── Response ────────────────────────────────────────────────────

class MessageResponse(BaseModel):
    """A single message returned to the client."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    conversation_id: UUID
    role: str
    content: str
    tool_call_id: str | None = None
    tool_name: str | None = None
    payload: dict | None = None
    created_at: datetime


class MessageListResponse(BaseModel):
    """Paginated list of messages."""

    items: list[MessageResponse]
    total: int
    offset: int = 0
    limit: int = 50

# ── Routes ──────────────────────────────────────────────────────────

router = APIRouter()

# How many previous messages to include as context (to keep prompt within budget)
_HISTORY_LIMIT = 50
# Maximum rounds of tool calling before we force a text response
_MAX_TOOL_ROUNDS = 3


# ── Helpers ─────────────────────────────────────────────────────


def _tool_to_chart_event(tool_name: str) -> str:
    """Map an LLM tool name to a ``chart.*`` SSE event type."""
    mapping = {
        "render_natal_chart": "chart.natal",
        "render_transit_timeline": "chart.transit",
        "render_synastry": "chart.synastry",
        "render_life_phases": "chart.life_phases",
    }
    return mapping.get(tool_name, "chart.render")


def _detect_reply_language(text: str) -> str | None:
    """Heuristic language of a user message: ``en``, ``pt``, or None if unclear."""
    t = (text or "").lower()
    if not t.strip():
        return None
    pt_markers = (
        "você", "voce", "olá", "ola", "obrigad", "por favor", "meu mapa",
        "hoje", "lua", "sol ", "carta", "trânsito", "transito", "me diga",
        "como está", "como esta", "preciso", "quero", "não", "nao ",
        "bom dia", "boa tarde", "ajuda",
    )
    en_markers = (
        " what ", "what's", "whats", "how ", "my ", "the ", "please",
        "today", "moon", "sun ", "chart", "transit", "should ", "would ",
        "tell me", "i want", "i need", "hello", "hi ", "career", "love",
    )
    # pad for boundary matches on short strings
    padded = f" {t} "
    pt = sum(1 for m in pt_markers if m in padded or m in t)
    en = sum(1 for m in en_markers if m in padded)
    # accented Portuguese characters are a strong signal
    if any(ch in t for ch in "áàâãéêíóôõúç"):
        pt += 2
    if pt == 0 and en == 0:
        return None
    if pt > en:
        return "pt"
    if en > pt:
        return "en"
    return None


async def _conversation_belongs_to_user(
    conn, conversation_id: UUID, user_id: UUID,
) -> dict | None:
    """Return the conversation row if it exists and belongs to user, else None."""
    row = await conn.fetchrow(
        """
        SELECT id, user_id, status, chart_context_id, synastry_context_id, model_version
        FROM conversations
        WHERE id = $1 AND user_id = $2
        """,
        conversation_id,
        user_id,
    )
    return dict(row) if row else None


async def _insert_message(
    conn,
    conversation_id: UUID,
    role: str,
    content: str | None,
    *,
    tool_call_id: str | None = None,
    tool_name: str | None = None,
    payload: dict | None = None,
) -> dict:
    """Insert a single message row and return it as a dict."""
    row = await conn.fetchrow(
        """
        INSERT INTO messages
            (conversation_id, role, content, tool_call_id, tool_name, payload)
        VALUES ($1, $2, $3, $4, $5, $6)
        RETURNING id, conversation_id, role, content,
                  tool_call_id, tool_name, payload, created_at
        """,
        conversation_id,
        role,
        content,
        tool_call_id,
        tool_name,
        payload,
    )
    return dict(row)


async def _load_conversation_history(
    conn, conversation_id: UUID, limit: int = _HISTORY_LIMIT,
) -> list[dict]:
    """Load recent messages from a conversation in OpenAI-compatible format.

    Returns a list of message dicts with keys ``role``, ``content``,
    ``tool_calls``, ``tool_call_id``.
    """
    rows = await conn.fetch(
        """
        SELECT role, content, tool_call_id, tool_name, payload
        FROM messages
        WHERE conversation_id = $1
        ORDER BY created_at ASC
        LIMIT $2
        """,
        conversation_id,
        limit,
    )

    messages: list[dict] = []
    for row in rows:
        role = row["role"]
        content = row["content"]
        tool_call_id = row.get("tool_call_id")

        if role == "tool":
            # Tool result message
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call_id,
                "content": content or "",
            })
        elif role == "assistant" and row.get("payload") and "tool_calls" in row["payload"]:
            # Assistant message with tool_calls — ensure args are JSON strings for the API
            tcs = []
            for tc in row["payload"]["tool_calls"]:
                tc = dict(tc)
                fn = dict(tc.get("function") or {})
                args = fn.get("arguments")
                if isinstance(args, dict):
                    fn["arguments"] = json.dumps(args)
                elif not isinstance(args, str):
                    fn["arguments"] = "{}"
                tc["function"] = fn
                tcs.append(tc)
            messages.append({
                "role": "assistant",
                "content": content,
                "tool_calls": tcs,
            })
        else:
            messages.append({
                "role": role,
                "content": content or "",
            })

    return messages


async def _load_chart_context(
    conn, chart_context_id: UUID | None,
) -> dict | None:
    """Fetch chart data for context injection into the system prompt.

    Returns a dict with ``bodies``, ``houses``, ``aspects``, ``chart_type``,
    or ``None`` if no chart context is set or the chart doesn't exist.
    """
    if chart_context_id is None:
        return None

    # Fetch the chart row
    chart_row = await conn.fetchrow(
        "SELECT id, chart_type FROM charts WHERE id = $1",
        chart_context_id,
    )
    if chart_row is None:
        return None

    # Fetch bodies
    bodies = await conn.fetch(
        """
        SELECT body_key, longitude, sign, sign_degree, house, dignity
        FROM chart_bodies WHERE chart_id = $1
        """,
        chart_context_id,
    )

    # Fetch houses
    houses = await conn.fetch(
        """
        SELECT house_number, sign, sign_degree
        FROM chart_houses WHERE chart_id = $1
        ORDER BY house_number
        """,
        chart_context_id,
    )

    # Fetch aspects
    aspects = await conn.fetch(
        """
        SELECT body_a_key, body_b_key, aspect_type, orb
        FROM chart_aspects WHERE chart_id = $1
        ORDER BY orb ASC
        """,
        chart_context_id,
    )

    return {
        "chart_type": chart_row["chart_type"],
        "bodies": [dict(r) for r in bodies],
        "houses": [dict(r) for r in houses],
        "aspects": [dict(r) for r in aspects],
    }


async def _call_llm_with_tools(
    messages: list[dict],
    system_prompt: str,
    conn,
    user_id: UUID,
    conversation_id: UUID,
    tools: list | None = None,
) -> tuple[str | None, list[dict], dict]:
    """Run the LLM loop: text → tool_calls → text.

    Parameters
    ----------
    messages : list[dict]
        The conversation history in OpenAI format. This list is mutated
        in-place as tool calls and results are appended.
    system_prompt : str
        The full system prompt (with chart context injected).
    conn
        Database connection for tool execution.
    user_id : UUID
        The authenticated user's ID.
    conversation_id : UUID
        The conversation UUID (for SSE publishing).
    tools : list or None
        Tool definitions to expose (defaults to full TOOL_DEFINITIONS).

    Returns
    -------
    (final_content, all_messages, usage_totals)
    """
    final_content: str | None = None
    all_created: list[dict] = []
    tool_round = 0
    active_tools = tools if tools is not None else TOOL_DEFINITIONS
    usage_totals: dict[str, int] = {
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "total_tokens": 0,
        "reasoning_tokens": 0,
        "llm_rounds": 0,
    }

    while tool_round < _MAX_TOOL_ROUNDS:
        response: LLMResponse = await chat_completion(
            messages=messages,
            system_prompt=system_prompt,
            tools=active_tools,
        )
        usage_totals["llm_rounds"] += 1
        u = response.usage or {}
        usage_totals["prompt_tokens"] += int(u.get("prompt_tokens") or 0)
        usage_totals["completion_tokens"] += int(u.get("completion_tokens") or 0)
        usage_totals["total_tokens"] += int(u.get("total_tokens") or 0)
        ctd = u.get("completion_tokens_details") or {}
        usage_totals["reasoning_tokens"] += int(
            ctd.get("reasoning_tokens") or u.get("reasoning_tokens") or 0
        )

        # Append assistant message
        assistant_msg: dict = {
            "role": "assistant",
            "content": response.content,
        }
        assistant_msg_db: dict = {
            "role": "assistant",
            "content": response.content,
        }

        if response.tool_calls:
            assistant_msg["tool_calls"] = response.tool_calls
            assistant_msg_db["payload"] = {"tool_calls": response.tool_calls}

        messages.append(assistant_msg)

        if not response.tool_calls:
            # Pure text response — we're done
            final_content = response.content
            break

        # Execute each tool call
        for tc in response.tool_calls:
            tool_name = tc["function"]["name"]
            raw_args = tc["function"].get("arguments")
            # API requires string args in history; parse a copy for execution
            if isinstance(raw_args, str):
                try:
                    tool_args = json.loads(raw_args) if raw_args.strip() else {}
                except (json.JSONDecodeError, TypeError):
                    tool_args = {}
            elif isinstance(raw_args, dict):
                tool_args = raw_args
                # Normalize for next LLM round (provider rejects dict args)
                tc["function"]["arguments"] = json.dumps(raw_args)
            else:
                tool_args = {}
                tc["function"]["arguments"] = "{}"

            try:
                result = await execute_tool(tool_name, tool_args, conn, user_id)
            except ValueError as exc:
                result = {"result": str(exc), "error": "unknown_tool"}
            except Exception as exc:
                result = {"result": f"Tool execution error: {exc}", "error": "execution_error"}

            # Append tool result message
            tool_result_content = json.dumps(result, default=str)
            tool_msg = {
                "role": "tool",
                "tool_call_id": tc["id"],
                "content": tool_result_content,
            }
            messages.append(tool_msg)

            # Ensure assistant tool_calls entry keeps string arguments
            if isinstance(tc.get("function", {}).get("arguments"), dict):
                tc["function"]["arguments"] = json.dumps(tc["function"]["arguments"])

            # Publish tool result to SSE as a chart.* event
            chart_event = _tool_to_chart_event(tool_name)
            await publish(
                str(conversation_id),
                chart_event,
                {
                    "tool": tool_name,
                    "result": result,
                    "conversation_id": str(conversation_id),
                },
            )

        tool_round += 1

    if final_content is None and messages:
        # Safety net: if we exhausted tool rounds without a text response,
        # use the last assistant content or a fallback
        for msg in reversed(messages):
            if msg["role"] == "assistant" and msg.get("content"):
                final_content = msg["content"]
                break
        if final_content is None:
            final_content = (
                "I've consulted the stars on your question. "
                "The patterns are complex — let me offer the key insight: "
                "trust the process and observe what unfolds in the coming days."
            )

    return final_content, messages, usage_totals


# ── POST /v1/conversations/{conversation_id}/messages ───────────


@router.post(
    "/{conversation_id}/messages",
    response_model=dict,
    status_code=status.HTTP_201_CREATED,
)
async def send_message(
    conversation_id: UUID,
    body: MessageCreate,
    auth: AuthPayload = Depends(require_user),
    conn=Depends(get_conn),
) -> dict:
    """Send a new message in a conversation and get an AI response.

    1. Verifies the conversation exists and is owned by the current user.
    2. Saves the user message to the database.
    3. Loads conversation history and chart context.
    4. Calls the LLM client with tools for function calling.
    5. Handles tool calls -> tool results -> final response loop.
    6. Saves the assistant response(s) to the database.
    7. Publishes all messages to SSE streams.
    8. Returns the user and assistant messages.
    """
    user_id = UUID(auth["sub"])

    # ── Verify ownership and active status ────────────────────────
    conv = await _conversation_belongs_to_user(conn, conversation_id, user_id)
    if conv is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found",
        )
    if conv["status"] == "archived":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot send messages to an archived conversation",
        )

    # ── Insert the user message ───────────────────────────────────
    user_message = await _insert_message(
        conn,
        conversation_id,
        role=body.role or "user",
        content=body.content,
    )

    # ── Build context for the LLM ─────────────────────────────────

    # 1. Load chart context from the conversation (if any)
    chart_context = await _load_chart_context(conn, conv.get("chart_context_id"))

    # 2. Build the system prompt (include chart_id so transit tools don't need re-natal)
    chart_id_str = str(conv["chart_context_id"]) if conv.get("chart_context_id") else None
    system_prompt = build_system_prompt(chart_context, chart_id=chart_id_str)

    # 2b. Language lock from the latest user text (product: never surprise-switch locale)
    lang = _detect_reply_language(body.content or "")
    if lang == "pt":
        system_prompt += (
            "\n\n## Language lock\n"
            "The user's latest message is in **Portuguese**. "
            "You MUST answer entirely in Portuguese (pt-BR)."
        )
    elif lang == "en":
        system_prompt += (
            "\n\n## Language lock\n"
            "The user's latest message is in **English**. "
            "You MUST answer entirely in English."
        )

    # 3. Tool surface: when natal placements are already injected, hide
    # render_natal_chart so the model cannot waste a round recomputing them.
    active_tools = TOOL_DEFINITIONS
    if chart_context and chart_context.get("bodies"):
        active_tools = [
            t
            for t in TOOL_DEFINITIONS
            if (t.get("function") or {}).get("name") != "render_natal_chart"
        ]

    # 4. Load recent conversation history (includes the user message just inserted)
    history = await _load_conversation_history(conn, conversation_id)

    # ── Call LLM with tool support ────────────────────────────────
    # New LLM-only rows are appended after this length
    history_len_before_llm = len(history)
    usage_totals: dict = {}
    try:
        assistant_content, all_messages, usage_totals = await _call_llm_with_tools(
            messages=history,
            system_prompt=system_prompt,
            conn=conn,
            user_id=user_id,
            conversation_id=conversation_id,
            tools=active_tools,
        )
    except LLMProviderError as exc:
        # Surface provider/auth/credit failures as clean API errors (not raw 500)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE
            if exc.status_code in (401, 402, 403, 429)
            else status.HTTP_502_BAD_GATEWAY,
            detail=exc.detail,
        ) from exc
    except RuntimeError as exc:
        # Missing API key, etc.
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc

    if assistant_content is None:
        assistant_content = "I have processed your request through the celestial lens."

    # ── Persist intermediate tool trail (for multi-turn harness inspection) ──
    # all_messages is the mutated history list; new rows are after history_len_before_llm
    tools_used: list[str] = []
    for msg in all_messages[history_len_before_llm:]:
        role = msg.get("role")
        if role == "assistant" and msg.get("tool_calls"):
            await _insert_message(
                conn,
                conversation_id,
                role="assistant",
                content=msg.get("content"),
                payload={"tool_calls": msg["tool_calls"]},
            )
            for tc in msg["tool_calls"]:
                name = (tc.get("function") or {}).get("name")
                if name:
                    tools_used.append(name)
        elif role == "tool":
            # Map tool_call_id → name when possible
            tname = None
            for prev in reversed(all_messages[: all_messages.index(msg)]):
                if prev.get("role") == "assistant" and prev.get("tool_calls"):
                    for tc in prev["tool_calls"]:
                        if tc.get("id") == msg.get("tool_call_id"):
                            tname = (tc.get("function") or {}).get("name")
                            break
                if tname:
                    break
            if tname:
                tools_used.append(tname)
            await _insert_message(
                conn,
                conversation_id,
                role="tool",
                content=msg.get("content"),
                tool_call_id=msg.get("tool_call_id"),
                tool_name=tname,
            )

    # ── Insert the final assistant text message ───────────────────
    assistant_message = await _insert_message(
        conn,
        conversation_id,
        role="assistant",
        content=assistant_content,
        payload={"tools_used": tools_used} if tools_used else None,
    )

    # ── Bump conversation updated_at ──────────────────────────────
    await conn.execute(
        "UPDATE conversations SET updated_at = now() WHERE id = $1",
        conversation_id,
    )

    # ── Publish to SSE streams ────────────────────────────────────
    conv_id_str = str(conversation_id)

    await publish(
        conv_id_str,
        "chat.delta",
        {
            "message_id": user_message["id"],
            "role": "user",
            "content": user_message["content"],
            "conversation_id": conv_id_str,
        },
    )

    await publish(
        conv_id_str,
        "chat.delta",
        {
            "message_id": assistant_message["id"],
            "role": "assistant",
            "content": assistant_message["content"],
            "conversation_id": conv_id_str,
        },
    )

    return {
        "user_message": MessageResponse(**user_message),
        "assistant_message": MessageResponse(**assistant_message),
        "tools_used": list(dict.fromkeys(tools_used)),  # preserve order, unique
        "usage": usage_totals,
    }


# ── GET /v1/conversations/{conversation_id}/messages ────────────


@router.get(
    "/{conversation_id}/messages",
    response_model=MessageListResponse,
)
async def list_messages(
    conversation_id: UUID,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    auth: AuthPayload = Depends(require_user),
    conn=Depends(get_conn),
) -> MessageListResponse:
    """List messages in a conversation (oldest first, paginated).

    Only the conversation owner may view messages.
    """
    user_id = UUID(auth["sub"])

    conv = await _conversation_belongs_to_user(conn, conversation_id, user_id)
    if conv is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found",
        )

    rows = await conn.fetch(
        """
        SELECT id, conversation_id, role, content,
               tool_call_id, tool_name, payload, created_at
        FROM messages
        WHERE conversation_id = $1
        ORDER BY created_at ASC
        LIMIT $2 OFFSET $3
        """,
        conversation_id,
        limit,
        offset,
    )

    total = await conn.fetchval(
        "SELECT COUNT(*) FROM messages WHERE conversation_id = $1",
        conversation_id,
    )

    return MessageListResponse(
        items=[MessageResponse(**dict(r)) for r in rows],
        total=total or 0,
        offset=offset,
        limit=limit,
    )
