"""SSE stream endpoint — ``GET /v1/stream``.

Keeps a persistent connection open per user/conversation and pushes
real-time events (chat tokens, chart data, status updates, etc.) as
they occur.
"""

from __future__ import annotations

import asyncio
import json
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from starlette.responses import StreamingResponse

from app.core.auth import AuthPayload, require_user
from app.core.deps import get_conn
from app.core.sse_manager import register, unregister

router = APIRouter()

# ── Heartbeat interval ──────────────────────────────────────────

_PING_INTERVAL = 30  # seconds between keep-alive pings


# ── SSE endpoint ────────────────────────────────────────────────


@router.get("/stream")
async def stream_events(
    conversation_id: str = Query(
        ...,
        description="UUID of the conversation to subscribe to",
    ),
    auth: AuthPayload = Depends(require_user),
    conn=Depends(get_conn),
):
    """SSE stream that pushes real-time events for a conversation.

    Required query parameter ``conversation_id`` — a valid UUID of an
    existing conversation owned by the current user.

    Event types
    -----------
    - ``session.status`` — initial connection confirmation
    - ``chat.delta`` — partial / full message content
    - ``chart.natal`` — natal chart data payload (from render_natal_chart tool)
    - ``chart.transit`` — transit timeline data payload (from render_transit_timeline tool)
    - ``chart.synastry`` — synastry overlay data payload (from render_synastry tool)
    - ``chart.life_phases`` — life phase data payload (from render_life_phases tool)
    - ``chart.render`` — fallback chart render event for unknown tools
    - ``error`` — server-side error information
    - ``ping`` (comment) — keep-alive signal (no ``event`` field)
    """
    # ── Validate conversation_id format ──────────────────────────
    try:
        conv_uuid = UUID(conversation_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid conversation_id — must be a valid UUID",
        )

    user_id = UUID(auth["sub"])

    # ── Verify conversation exists and is owned by the user ──────
    conv = await conn.fetchrow(
        """
        SELECT id, user_id, status
        FROM conversations
        WHERE id = $1 AND user_id = $2
        """,
        conv_uuid,
        user_id,
    )
    if conv is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found or not owned by you",
        )

    # ── Async generator → SSE streaming response ─────────────────

    async def event_generator():
        queue = await register(conversation_id)
        try:
            # Send initial session.status event
            yield (
                f"event: session.status\n"
                f"data: {json.dumps({'status': 'connected', 'conversation_id': conversation_id})}\n\n"
            )

            while True:
                try:
                    # Wait for either a queued event or the ping timeout
                    event = await asyncio.wait_for(
                        queue.get(),
                        timeout=_PING_INTERVAL,
                    )
                    yield event
                except asyncio.TimeoutError:
                    # Keep-alive ping (SSE comment — no event type)
                    yield ": ping\n\n"
        except asyncio.CancelledError:
            # Client disconnected — clean up
            pass
        finally:
            await unregister(conversation_id, queue)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
