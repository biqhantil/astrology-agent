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
from app.llm.client import LLMResponse, chat_completion
from app.llm.prompts import build_system_prompt
from app.llm.tools import TOOL_DEFINITIONS, execute_tool
from app.schemas.message import MessageCreate, MessageListResponse, MessageResponse

router = APIRouter()

# How many previous messages to include as context (to keep prompt within budget)
_HISTORY_LIMIT = 50
# Maximum rounds of tool calling before we force a text response
_MAX_TOOL_ROUNDS = 5


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
            # Assistant message with tool_calls
            messages.append({
                "role": "assistant",
                "content": content,
                "tool_calls": row["payload"]["tool_calls"],
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
) -> tuple[str | None, list[dict]]:
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

    Returns
    -------
    (final_content, all_messages)
        ``final_content`` is the last assistant text response, or ``None`` if
        all rounds resulted in tool calls only.
        ``all_messages`` is the list of all message dicts that were created
        during the call (for DB storage and SSE publishing).
    """
    final_content: str | None = None
    all_created: list[dict] = []
    tool_round = 0

    while tool_round < _MAX_TOOL_ROUNDS:
        response: LLMResponse = await chat_completion(
            messages=messages,
            system_prompt=system_prompt,
            tools=TOOL_DEFINITIONS,
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
            tool_args = tc["function"]["arguments"]

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

    return final_content, messages


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

    # 2. Build the system prompt
    system_prompt = build_system_prompt(chart_context)

    # 3. Load recent conversation history
    history = await _load_conversation_history(conn, conversation_id)

    # 4. Append the new user message
    history.append({
        "role": "user",
        "content": body.content,
    })

    # ── Call LLM with tool support ────────────────────────────────
    assistant_content, _all_messages = await _call_llm_with_tools(
        messages=history,
        system_prompt=system_prompt,
        conn=conn,
        user_id=user_id,
        conversation_id=conversation_id,
    )

    if assistant_content is None:
        assistant_content = "I have processed your request through the celestial lens."

    # ── Insert the assistant message ──────────────────────────────
    assistant_message = await _insert_message(
        conn,
        conversation_id,
        role="assistant",
        content=assistant_content,
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
