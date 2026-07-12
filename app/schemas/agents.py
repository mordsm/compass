from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


AgentId = Literal[
    "rules_engine",
    "self_manage",
    "assessment",
    "mail_manager",
    "economic_spending",
    "task_commander",
    "administrative",
]


class InvokeAgentRequest(BaseModel):
    agent_id: AgentId
    task: str
    user_id: str = "moshe"
    context: dict[str, Any] = Field(default_factory=dict)
    expected_output: str | None = None
    require_approval: bool = False
    risk_level: str = "medium"
