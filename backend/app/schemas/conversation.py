"""Pydantic schemas for the ``conversations`` resource."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


# ── Request ─────────────────────────────────────────────────────

class ConversationCreate(BaseModel):
    """Create a new conversation for the current user.

    All fields are optional — the API will auto-generate defaults.
    A ``title`` may be provided by the client for display purposes,
    otherwise the LLM will generate one from the first user message.
    """

    chart_context_id: UUID | None = None
    synastry_context_id: UUID | None = None
    title: str | None = None
    model_version: str | None = None


class ConversationUpdate(BaseModel):
    """Partial update of a conversation.

    Supports renaming the conversation and changing its status.
    """

    title: str | None = None
    status: str | None = Field(None, pattern="^(active|archived)$")


# ── Response ────────────────────────────────────────────────────

class ConversationResponse(BaseModel):
    """Full conversation returned to the client."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    chart_context_id: UUID | None = None
    synastry_context_id: UUID | None = None
    title: str | None = None
    status: str = "active"
    model_version: str | None = None
    created_at: datetime
    updated_at: datetime
