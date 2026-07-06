"""Pydantic schemas for the ``messages`` resource."""

from __future__ import annotations

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
