"""Conversation CRUD — nested under /v1/conversations.

Follows the same pattern as birth_profiles.py and me.py:
  - ``require_user`` dependency for auth
  - ``get_conn`` dependency for DB access
  - ``auth["sub"]`` → UUID for the current user
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.auth import AuthPayload, require_user
from app.core.deps import get_conn
from app.schemas.conversation import (
    ConversationCreate,
    ConversationResponse,
    ConversationUpdate,
)

router = APIRouter()


# ── Helpers ─────────────────────────────────────────────────────

_CONVERSATION_COLUMNS = """\
    id, user_id, chart_context_id, synastry_context_id,
    title, status, model_version, created_at, updated_at\
"""


async def _fetch_conversation(
    conn, conversation_id: UUID, user_id: UUID,
) -> dict | None:
    """Return a single conversation row, or ``None`` if not found/not owned."""
    row = await conn.fetchrow(
        f"""
        SELECT {_CONVERSATION_COLUMNS}
        FROM conversations
        WHERE id = $1 AND user_id = $2
        """,
        conversation_id,
        user_id,
    )
    return dict(row) if row else None


async def _fetch_messages(
    conn, conversation_id: UUID, *, limit: int = 50, offset: int = 0,
) -> list[dict]:
    """Return messages for a conversation, newest first."""
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
    return [dict(r) for r in rows]


async def _count_messages(conn, conversation_id: UUID) -> int:
    """Return total message count for a conversation."""
    return await conn.fetchval(
        "SELECT COUNT(*) FROM messages WHERE conversation_id = $1",
        conversation_id,
    )


# ── POST /v1/conversations ──────────────────────────────────────

@router.post("", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED)
async def create_conversation(
    body: ConversationCreate,
    auth: AuthPayload = Depends(require_user),
    conn=Depends(get_conn),
) -> ConversationResponse:
    """Create a new conversation for the authenticated user."""
    user_id = UUID(auth["sub"])

    row = await conn.fetchrow(
        """
        INSERT INTO conversations
            (user_id, chart_context_id, synastry_context_id, title, model_version)
        VALUES ($1, $2, $3, $4, $5)
        RETURNING id, user_id, chart_context_id, synastry_context_id,
                  title, status, model_version, created_at, updated_at
        """,
        user_id,
        body.chart_context_id,
        body.synastry_context_id,
        body.title,
        body.model_version,
    )

    return ConversationResponse(**dict(row))


# ── GET /v1/conversations ───────────────────────────────────────

@router.get("", response_model=list[ConversationResponse])
async def list_conversations(
    status_filter: str | None = Query(
        None, alias="status", pattern="^(active|archived)$",
    ),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    auth: AuthPayload = Depends(require_user),
    conn=Depends(get_conn),
) -> list[ConversationResponse]:
    """List the authenticated user's conversations.

    By default returns active conversations only. Pass ``?status=archived``
    to see archived, or ``?status=all`` (or omit) for both.
    """
    user_id = UUID(auth["sub"])

    if status_filter:
        rows = await conn.fetch(
            f"""
            SELECT {_CONVERSATION_COLUMNS}
            FROM conversations
            WHERE user_id = $1 AND status = $2
            ORDER BY updated_at DESC
            LIMIT $3 OFFSET $4
            """,
            user_id,
            status_filter,
            limit,
            offset,
        )
    else:
        rows = await conn.fetch(
            f"""
            SELECT {_CONVERSATION_COLUMNS}
            FROM conversations
            WHERE user_id = $1
            ORDER BY updated_at DESC
            LIMIT $2 OFFSET $3
            """,
            user_id,
            limit,
            offset,
        )

    return [ConversationResponse(**dict(r)) for r in rows]


# ── GET /v1/conversations/{id} ──────────────────────────────────

@router.get("/{conversation_id}")
async def get_conversation(
    conversation_id: UUID,
    auth: AuthPayload = Depends(require_user),
    conn=Depends(get_conn),
) -> dict:
    """Return a conversation with its messages (paginated).

    The response includes the conversation metadata and a paginated
    list of messages ordered oldest-first.
    """
    user_id = UUID(auth["sub"])

    conversation = await _fetch_conversation(conn, conversation_id, user_id)
    if conversation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found",
        )

    messages = await _fetch_messages(conn, conversation_id)
    total = await _count_messages(conn, conversation_id)

    return {
        "conversation": conversation,
        "messages": {
            "items": messages,
            "total": total,
            "offset": 0,
            "limit": 50,
        },
    }


# ── PATCH /v1/conversations/{id} ────────────────────────────────

@router.patch("/{conversation_id}", response_model=ConversationResponse)
async def update_conversation(
    conversation_id: UUID,
    body: ConversationUpdate,
    auth: AuthPayload = Depends(require_user),
    conn=Depends(get_conn),
) -> ConversationResponse:
    """Update a conversation's title and/or status.

    Only the owner can update a conversation.
    """
    user_id = UUID(auth["sub"])

    # Build dynamic SET clause
    sets: list[str] = []
    params: list[object] = []
    idx = 1

    if body.title is not None:
        sets.append(f"title = ${idx}")
        params.append(body.title)
        idx += 1

    if body.status is not None:
        sets.append(f"status = ${idx}")
        params.append(body.status)
        idx += 1

    if not sets:
        # Nothing to update — return current
        conversation = await _fetch_conversation(conn, conversation_id, user_id)
        if conversation is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found",
            )
        return ConversationResponse(**conversation)

    # Always bump updated_at
    sets.append(f"updated_at = now()")

    params.append(conversation_id)
    params.append(user_id)

    row = await conn.fetchrow(
        f"""
        UPDATE conversations
        SET {', '.join(sets)}
        WHERE id = ${idx} AND user_id = ${idx + 1}
        RETURNING {_CONVERSATION_COLUMNS}
        """,
        *params,
    )

    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found",
        )

    return ConversationResponse(**dict(row))


# ── DELETE /v1/conversations/{id} ───────────────────────────────

@router.delete("/{conversation_id}", status_code=status.HTTP_200_OK)
async def archive_conversation(
    conversation_id: UUID,
    auth: AuthPayload = Depends(require_user),
    conn=Depends(get_conn),
) -> dict:
    """Archive (soft-delete) a conversation by setting status to ``archived``.

    Returns the updated conversation.
    """
    user_id = UUID(auth["sub"])

    row = await conn.fetchrow(
        f"""
        UPDATE conversations
        SET status = 'archived', updated_at = now()
        WHERE id = $1 AND user_id = $2
        RETURNING {_CONVERSATION_COLUMNS}
        """,
        conversation_id,
        user_id,
    )

    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found",
        )

    return dict(row)
