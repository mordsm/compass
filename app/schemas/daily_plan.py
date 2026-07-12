from __future__ import annotations

from datetime import date
from typing import Any

from pydantic import BaseModel, Field

from app.schemas.common import IdempotentRequest


class SaveDailyPlanRequest(IdempotentRequest):
    user_id: str
    date: date
    plan_id: str | None = None
    status: str = "approved"
    energy_level: int | None = Field(default=None, ge=1, le=5)
    available_minutes: int | None = Field(default=None, ge=0)
    outcomes: list[dict[str, Any]] = Field(default_factory=list)
    scheduled_tasks: list[dict[str, Any]] = Field(default_factory=list)
    deferred_items: list[dict[str, Any]] = Field(default_factory=list)
    risks: list[dict[str, Any]] = Field(default_factory=list)
    notes: str | None = None
