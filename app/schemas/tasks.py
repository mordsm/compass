from __future__ import annotations

from datetime import date
from typing import Any

from pydantic import BaseModel, Field

from app.schemas.common import IdempotentRequest, TaskStatus


class UpsertTaskRequest(IdempotentRequest):
    user_id: str
    title: str
    task_id: str | None = None
    description: str | None = None
    status: TaskStatus = "proposed"
    due_date: date | None = None
    priority: str | None = None
    source: str = "gpt"
    metadata: dict[str, Any] = Field(default_factory=dict)
