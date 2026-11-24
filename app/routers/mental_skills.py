from __future__ import annotations

from typing import Any, Literal
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.auth import require_actions_key
from app.schemas.mental_skills import (
    CompleteSessionRequest,
    RecordSessionEventRequest,
    SaveObservationRequest,
    SaveReflectionRequest,
    StartSessionRequest,
)
from app.services.mental_skills import MentalSkillsService


router = APIRouter(prefix="/api/msp", tags=["mental-skills"], dependencies=[Depends(require_actions_key)])


class RecordMentalEventRequest(BaseModel):
    user_id: str = "moshe"
    event_id: str | None = None
    occurred_at: str | None = None
    event_type: str = "interpersonal_friction"
    training_stage: Literal["baseline_calm", "pre_event_prep", "realtime_intervention", "post_event_processing"] = "post_event_processing"
    short_description: str = ""
    trigger_text: str = ""
    initial_emotion_intensity: int | None = Field(default=None, ge=0, le=10)
    defensive_or_attack_urge: int | None = Field(default=None, ge=0, le=10)
    curiosity_ability: int | None = Field(default=None, ge=0, le=10)
    choice_ability: int | None = Field(default=None, ge=0, le=10)
    actual_response: str = ""
    recovery_duration_minutes: int | None = Field(default=None, ge=0)
    notes: str | None = None
    reporting_confidence: Literal["high", "medium", "low"] = "high"
    is_silent_win: bool = False
    lesson_learned: str | None = None
    idempotency_key: str | None = None


class WeeklySilentWinsCheckRequest(BaseModel):
    user_id: str = "moshe"
    silent_wins: list[dict[str, Any]] = Field(default_factory=list)
    notes: str = ""


@router.get("/user/context", operation_id="getMentalSkillsUserContext")
def get_user_context(user_id: str = "moshe") -> dict:
    return MentalSkillsService().user_context(user_id)


@router.get("/user/profile", operation_id="getMentalSkillsUserProfile")
def get_user_profile(user_id: str = "moshe") -> dict:
    return MentalSkillsService().profile(user_id)


@router.get("/skills", operation_id="listMentalSkills")
def list_skills(user_id: str = "moshe") -> dict:
    return MentalSkillsService().list_skills(user_id)


@router.get("/skills/{skill_id}/history", operation_id="getMentalSkillHistory")
def get_skill_history(skill_id: str, user_id: str = "moshe", limit: int = 10) -> dict:
    return MentalSkillsService().skill_history(user_id, skill_id, limit=limit)


@router.get("/training/recommendation", operation_id="getMentalTrainingRecommendation")
def get_training_recommendation(user_id: str = "moshe") -> dict:
    return MentalSkillsService().recommendation(user_id)


@router.post("/sessions/start", operation_id="startMentalTrainingSession")
def start_session(request: StartSessionRequest) -> dict:
    return MentalSkillsService().start_session(request.model_dump(mode="json"))


@router.post("/sessions/{session_id}/event", operation_id="recordMentalTrainingSessionEvent")
def record_session_event(session_id: str, request: RecordSessionEventRequest) -> dict:
    return MentalSkillsService().record_event(session_id, request.model_dump(mode="json"))


@router.post("/sessions/{session_id}/complete", operation_id="completeMentalTrainingSession")
def complete_session(session_id: str, request: CompleteSessionRequest) -> dict:
    return MentalSkillsService().complete_session(session_id, request.model_dump(mode="json"))


@router.post("/observations", operation_id="saveMentalSkillsObservation")
def save_observation(request: SaveObservationRequest) -> dict:
    return MentalSkillsService().save_observation(request.model_dump(mode="json"))


@router.get("/patterns", operation_id="getMentalSkillsPatterns")
def get_patterns(user_id: str = "moshe") -> dict:
    return MentalSkillsService().patterns(user_id)


@router.post("/reflection", operation_id="saveMentalSkillsReflection")
def save_reflection(request: SaveReflectionRequest) -> dict:
    return MentalSkillsService().save_reflection(request.model_dump(mode="json"))


@router.get("/progress", operation_id="getMentalSkillsProgress")
def get_progress(user_id: str = "moshe") -> dict:
    return MentalSkillsService().progress(user_id)


@router.get("/proactive/catalog", operation_id="getProactiveMentalTrainingCatalog")
def get_proactive_catalog() -> dict[str, Any]:
    return MentalSkillsService().get_proactive_training_catalog()


@router.post("/proactive/events", operation_id="recordProactiveMentalEvent")
def record_proactive_mental_event(request: RecordMentalEventRequest) -> dict[str, Any]:
    return MentalSkillsService().record_mental_event(request.model_dump(mode="json"))


@router.get("/proactive/events", operation_id="listProactiveMentalEvents")
def list_proactive_mental_events(user_id: str = "moshe", limit: int = 50) -> dict[str, Any]:
    events = MentalSkillsService().list_mental_events(user_id=user_id, limit=limit)
    return {"success": True, "user_id": user_id, "count": len(events), "events": events}


@router.post("/proactive/silent-wins-check", operation_id="runWeeklySilentWinsCheck")
def run_weekly_silent_wins_check(request: WeeklySilentWinsCheckRequest) -> dict[str, Any]:
    return MentalSkillsService().weekly_silent_wins_check(
        user_id=request.user_id,
        silent_wins=request.silent_wins,
        notes=request.notes,
    )


@router.get("/proactive/monthly-assessment", operation_id="getMonthlyMentalAssessment")
def get_monthly_mental_assessment(user_id: str = "moshe", minimum_events: int = 5) -> dict[str, Any]:
    return MentalSkillsService().generate_monthly_mental_assessment(
        user_id=user_id,
        minimum_events_required=minimum_events,
    )
