from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


class RulesEventRequest(BaseModel):
    user_id: str
    event_type: str
    actor: str | None = None
    context: dict[str, Any] = Field(default_factory=dict)
    signals: list[str] = Field(default_factory=list)
    dry_run: bool = True


class EventMetadata(BaseModel):
    trace_id: str | None = None
    dry_run: bool = False
    requested_actions: list[dict[str, Any]] = Field(default_factory=list)


class StructuredRulesEventRequest(BaseModel):
    event_id: str
    event_type: str
    source: str
    user_id: str
    occurred_at: datetime
    payload: dict[str, Any]
    idempotency_key: str
    event_version: str = "1.0"
    actor: str | None = None
    subject_type: str | None = None
    subject_id: str | None = None
    metadata: EventMetadata = Field(default_factory=EventMetadata)
    dry_run: bool = False

    @field_validator("occurred_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value

    def to_structured_event(self) -> dict[str, Any]:
        data = self.model_dump(mode="json", exclude={"actor", "dry_run"})
        data["metadata"]["dry_run"] = self.dry_run
        return data


class MatchedRule(BaseModel):
    rule_id: str
    name: str
    category: str
    priority: int
    version: int
    effects: list[str] = Field(default_factory=list)


class PlannedAction(BaseModel):
    action_type: str
    title: str | None = None
    component: str | None = None
    purpose: str | None = None
    due_date: str | None = None
    parameters: dict[str, Any] = Field(default_factory=dict)


class BlockedAction(BaseModel):
    action_type: str
    reason_code: str
    title: str | None = None
    parameters: dict[str, Any] = Field(default_factory=dict)


class RouteDecision(BaseModel):
    component: str
    capability: str | None = None
    purpose: str | None = None


class Redaction(BaseModel):
    field: str
    reason_code: str


class RuleEvaluationResponse(BaseModel):
    evaluation_id: str
    event_id: str
    final_decision: Literal[
        "block",
        "require_approval",
        "allow_with_redaction",
        "allow_read_only",
        "allow",
        "recommendation_only",
    ]
    risk_level: Literal["low", "medium", "high", "critical"]
    matched_rules: list[MatchedRule] = Field(default_factory=list)
    reason_codes: list[str] = Field(default_factory=list)
    allowed_actions: list[PlannedAction] = Field(default_factory=list)
    approval_required_actions: list[PlannedAction] = Field(default_factory=list)
    blocked_actions: list[BlockedAction] = Field(default_factory=list)
    routes: list[RouteDecision] = Field(default_factory=list)
    selected_workflow: dict[str, Any] | None = None
    redactions: list[Redaction] = Field(default_factory=list)
    conflicts_resolved: list[dict[str, Any]] = Field(default_factory=list)
    alternatives_considered: list[dict[str, Any]] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    dry_run: bool = False
    explanation: str = ""


class AssessmentFindingWorkflowRequest(BaseModel):
    user_id: str = "moshe"
    event_id: str
    occurred_at: datetime
    idempotency_key: str
    domain: str
    finding_type: str
    severity: Literal["low", "medium", "high", "critical"] = "medium"
    confidence: float
    current_state: str | None = None
    evidence: list[str] = Field(default_factory=list)
    recommended_capability: str | None = None
    source: str = "personal_Assessment"
    dry_run: bool = False
    auto_create_approval: bool = True
    execute_self_manage: bool = False
    approval_confirmed: bool = False
    open_ui: bool = False
    self_manage_profile: dict[str, Any] = Field(default_factory=dict)


class AssessmentFindingWorkflowResponse(BaseModel):
    success: bool = True
    status: str
    rules_result: RuleEvaluationResponse
    approval_request_id: str | None = None
    self_manage_route: RouteDecision | None = None
    self_manage_preview: dict[str, Any] = Field(default_factory=dict)
    self_manage_profile: dict[str, Any] = Field(default_factory=dict)
    self_manage_plan: dict[str, Any] = Field(default_factory=dict)
    ui_url: str | None = None
    ui_urls: dict[str, str] = Field(default_factory=dict)
    ui_opened: bool = False
    ui_open_method: str | None = None
    executed_actions: list[dict[str, Any]] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
