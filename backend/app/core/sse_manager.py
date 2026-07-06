"""SSE connection manager — tracks active streaming connections per conversation.

Each connection gets an ``asyncio.Queue``. When a new message is published
for a conversation, it's pushed to all active queues for that conversation,
which then write it to the SSE wire.
"""

from __future__ import annotations

import asyncio
import json
from collections import defaultdict
from typing import Any

# ── Global registry ─────────────────────────────────────────────
# conversation_id (str) → list[asyncio.Queue]
_connections: dict[str, list[asyncio.Queue]] = defaultdict(list)
_lock = asyncio.Lock()


# ── Public API ──────────────────────────────────────────────────


async def register(conversation_id: str) -> asyncio.Queue:
    """Create a new queue for a conversation and register it.

    Returns the queue that the SSE handler should read from.
    """
    queue: asyncio.Queue = asyncio.Queue()
    async with _lock:
        _connections[conversation_id].append(queue)
    return queue


async def unregister(conversation_id: str, queue: asyncio.Queue) -> None:
    """Remove a queue from the conversation's active connections."""
    async with _lock:
        queues = _connections.get(conversation_id, [])
        if queue in queues:
            queues.remove(queue)
        if not queues:
            _connections.pop(conversation_id, None)


def _format_sse(event: str, data: dict[str, Any]) -> str:
    """Format a dict as an SSE message string."""
    return f"event: {event}\ndata: {json.dumps(data, default=str)}\n\n"


async def publish(
    conversation_id: str,
    event: str,
    data: dict[str, Any],
) -> int:
    """Push an event to all active connections for a conversation.

    Returns the number of connections that received the event.
    """
    payload = _format_sse(event, data)
    sent = 0
    async with _lock:
        queues = list(_connections.get(conversation_id, []))
        for queue in queues:
            await queue.put(payload)
            sent += 1
    return sent
