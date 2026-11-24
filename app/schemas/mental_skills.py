from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


MspMode = Literal["TRAINING_MODE", "FIELD_MODE"]
MspEventType = Literal[
    "baseline_response",
    "reflection",
    "micro_skill",
    "retest_response",
    "debrief",
    "user_stop",
    "cooldown",
]


class UserQuery(BaseModel):
    user_id: str = "moshe"


class SkillHistoryQuery(UserQuery):
    limit: int = Field(default=10, ge=1, le=50)


class StartSessionRequest(BaseModel):
    idempotency_key: str
    user_id: str = "moshe"
    skill_id: str
    exercise_id: str | None = None
    mode: MspMode = "TRAINING_MODE"
    difficulty: int = Field(default=1, ge=1, le=2)


class RecordSessionEventRequest(BaseModel):
    idempotency_key: str
    event_type: MspEventType
    occurred_at: datetime
    payload: dict[str, Any] = Field(default_factory=dict)


class CompleteSessionRequest(BaseModel):
    idempotency_key: str
    summary: str
    user_noticed_change: bool = False
    safety_state: str = "ok"


class SaveObservationRequest(BaseModel):
    idempotency_key: str
    user_id: str = "moshe"
    content: str
    skill_id: str | None = None
    occurred_at: datetime | None = None
    source: str = "gpt"
    tags: list[str] = Field(default_factory=list)


class SaveReflectionRequest(BaseModel):
    idempotency_key: str
    user_id: str = "moshe"
    content: str
    session_id: str | None = None
    skill_id: str | None = None
    insight_tags: list[str] = Field(default_factory=list)
