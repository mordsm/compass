from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from app.schemas.common import IdempotentRequest, Importance


class ConversationEventRequest(IdempotentRequest):
    user_id: str
    event_type: str
    content: str
    conversation_id: str | None = None
    importance: Importance = "medium"
    structured_payload: dict[str, Any] = Field(default_factory=dict)


class FinalizeConversationRequest(IdempotentRequest):
    user_id: str
    summary: str
    conversation_id: str | None = None
    decisions: list[dict[str, Any]] = Field(default_factory=list)
    tasks: list[dict[str, Any]] = Field(default_factory=list)
    open_questions: list[str] = Field(default_factory=list)
