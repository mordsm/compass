from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class RulesEventRequest(BaseModel):
    user_id: str
    event_type: str
    actor: str | None = None
    context: dict[str, Any] = Field(default_factory=dict)
    signals: list[str] = Field(default_factory=list)
    dry_run: bool = True
