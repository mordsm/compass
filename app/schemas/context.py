from __future__ import annotations

from datetime import date
from typing import Any

from pydantic import BaseModel, Field


class MorningContextRequest(BaseModel):
    user_id: str
    date: date
    timezone: str = "Asia/Jerusalem"
    include: list[str] = Field(default_factory=list)


class MorningContextResponse(BaseModel):
    success: bool = True
    user_id: str
    date: date
    timezone: str
    calendar: list[dict[str, Any]] = Field(default_factory=list)
    open_tasks: list[dict[str, Any]] = Field(default_factory=list)
    overdue_tasks: list[dict[str, Any]] = Field(default_factory=list)
    recent_events: list[dict[str, Any]] = Field(default_factory=list)
    recent_daily_plans: list[dict[str, Any]] = Field(default_factory=list)
    self_management: dict[str, Any] = Field(default_factory=dict)
    assessment: dict[str, Any] = Field(default_factory=dict)
    mail: dict[str, Any] = Field(default_factory=dict)
    economic_spending: dict[str, Any] = Field(default_factory=dict)
    task_commander: dict[str, Any] = Field(default_factory=dict)
    administrative: dict[str, Any] = Field(default_factory=dict)
    rules_backbone: dict[str, Any] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
    suggested_focus: list[str] = Field(default_factory=list)
