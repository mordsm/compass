from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from app.schemas.common import IdempotentRequest


ApprovalStatus = Literal["pending", "approved", "rejected", "executed", "cancelled"]
RiskLevel = Literal["low", "medium", "high", "critical"]


class CreateApprovalRequest(IdempotentRequest):
    user_id: str
    title: str
    action_type: str
    description: str | None = None
    requested_by: str = "gpt"
    risk_level: RiskLevel = "medium"
    proposed_action: dict[str, Any] = Field(default_factory=dict)
    rule_result: dict[str, Any] = Field(default_factory=dict)


class DecideApprovalRequest(BaseModel):
    user_id: str
    decision_by: str = "user"
    decision_notes: str | None = None


class ApprovalRequest(BaseModel):
    id: str
    user_id: str
    title: str
    description: str | None = None
    requested_by: str
    action_type: str
    status: ApprovalStatus
    risk_level: RiskLevel
    proposed_action: dict[str, Any] = Field(default_factory=dict)
    rule_result: dict[str, Any] = Field(default_factory=dict)
    created_at: str
    updated_at: str
    decided_at: str | None = None
    decision_by: str | None = None
    decision_notes: str | None = None
