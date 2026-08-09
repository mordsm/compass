from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field


class TrainingContextRequest(BaseModel):
    user_id: str = "moshe"


class TrainingSessionRequest(BaseModel):
    user_id: str = "moshe"
    session_date: date
    program_week: int | None = None
    session_type: str
    event_summary: str = ""
    trigger: str = ""
    automatic_interpretation: str = ""
    body_signals: list[str] = Field(default_factory=list)
    emotions: list[str] = Field(default_factory=list)
    action_urge: str = ""
    actual_response: str = ""
    working_hypothesis: str = ""
    chosen_value: str = ""
    alternative_response: str = ""
    practice_until_next_session: str = ""
    expected_obstacle: str = ""
    if_then_plan: str = ""
    key_insight: str = ""
    topics_to_revisit: list[str] = Field(default_factory=list)
    distress_before: int | None = Field(default=None, ge=0, le=10)
    distress_after: int | None = Field(default=None, ge=0, le=10)


class TrainingHistorySearchRequest(BaseModel):
    user_id: str = "moshe"
    query: str
    date_from: date | None = None
    date_to: date | None = None
    limit: int = Field(default=10, ge=1, le=50)


class TrainingProgressRequest(BaseModel):
    user_id: str = "moshe"
    period: str = "last_30_days"
