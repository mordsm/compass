from __future__ import annotations

from datetime import date
from typing import Any, Literal

from pydantic import BaseModel, Field


class GptServiceStatus(BaseModel):
    connected: bool
    base_url: str
    latency_ms: int = 0
    warning: str = ""


class GptStatusResponse(BaseModel):
    success: bool = True
    service: str = "compass"
    systems: dict[str, GptServiceStatus] = Field(default_factory=dict)


class GptMorningResponse(BaseModel):
    success: bool = True
    user_id: str
    date: date
    timezone: str
    systems: dict[str, GptServiceStatus] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
    summary: str
    suggested_focus: list[str] = Field(default_factory=list)
    counts: dict[str, int] = Field(default_factory=dict)
    training_sessions_completed: int = 0
    training_next_focus: str = ""


class GptTrainingSessionRequest(BaseModel):
    user_id: str = "moshe"
    session_date: date
    session_type: str
    event_summary: str = ""
    key_insight: str = ""
    distress_before: int | None = Field(default=None, ge=0, le=10)
    distress_after: int | None = Field(default=None, ge=0, le=10)


class GptTrainingSessionResponse(BaseModel):
    success: bool
    connected: bool
    session_id: str = ""
    message: str = ""
    warning: str = ""


class GptStatusFlatResponse(BaseModel):
    success: bool = True
    service: str = "compass"
    connected_systems: str = ""
    disconnected_systems: str = ""
    systems_text: str = ""
    connected_count: int = 0
    disconnected_count: int = 0


class GptMorningFlatResponse(BaseModel):
    success: bool = True
    user_id: str
    date: date
    timezone: str
    summary: str
    connected_systems: str = ""
    disconnected_systems: str = ""
    warnings_text: str = ""
    open_task_count: int = 0
    recent_event_count: int = 0
    recent_daily_plan_count: int = 0
    training_sessions_completed: int = 0
    training_next_focus: str = ""


class GptEchoResponse(BaseModel):
    success: bool = True
    message: str = "COMPASS_ECHO_OK"
    number: int = 42
    connected_systems: str = "echo_system"


class GptAssessmentStartRequest(BaseModel):
    user_id: str = "moshe"
    task: Literal["analyze", "morning_context", "recommend_next", "generate_review"] = "analyze"
    days: int = Field(default=30, ge=1, le=365)
    expected_output: str | None = None
    risk_level: str = "medium"
    dry_run: bool = True
    open_ui: bool = False
    ui_target: Literal["home", "assessments", "battery", "focus", "energy", "mental", "physical"] = "battery"
    context: dict[str, Any] = Field(default_factory=dict)


class GptAssessmentStartResponse(BaseModel):
    success: bool
    connected: bool
    task: str
    summary: str = ""
    confidence: str = ""
    findings: list[dict[str, Any]] = Field(default_factory=list)
    signals: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    proposed_actions: list[dict[str, Any]] = Field(default_factory=list)
    requires_approval: bool = False
    ui_url: str = ""
    ui_urls: dict[str, str] = Field(default_factory=dict)
    ui_opened: bool = False
    user_instruction: str = ""
    warning: str = ""
