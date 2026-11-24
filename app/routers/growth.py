from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.auth import require_actions_key
from app.services.growth_service import GrowthChallengesAndPlayService

router = APIRouter(prefix="/api/growth", tags=["growth"], dependencies=[Depends(require_actions_key)])


class UpsertDomainRequest(BaseModel):
    user_id: str = "moshe"
    slug: str
    name: str | None = None
    tier: Literal["core", "enrichment"] | None = None
    tier_weight: int | None = None
    long_term_goal: str | None = None
    importance: int | None = Field(default=None, ge=1, le=10)
    intervention_level: Literal["low", "medium", "high"] | None = None
    current_level: int | None = Field(default=None, ge=1, le=10)
    desired_level: int | None = Field(default=None, ge=1, le=10)
    progress_metrics: list[str] | None = None
    desired_frequency_per_week: int | None = Field(default=None, ge=1, le=14)
    constraints: list[str] | None = None
    next_evaluation_date: str | None = None


class RecordDomainActivityRequest(BaseModel):
    user_id: str = "moshe"
    slug: str
    occurred_at: str | None = None


class CreateChallengeRequest(BaseModel):
    user_id: str = "moshe"
    challenge_id: str | None = None
    domain_slug: str = "physical"
    challenge_type: Literal["mental", "physical", "professional", "cognitive", "creative", "learning"] = "physical"
    title: str
    goal: str = ""
    current_level: int = Field(default=1, ge=1, le=10)
    difficulty_level: int = Field(default=3, ge=1, le=10)
    max_approved_difficulty: int = Field(default=5, ge=1, le=10)
    duration_days: int = Field(default=14, ge=1, le=180)
    start_condition: str = "אנרגיה >= 3 וללא כאב"
    success_condition: str = "3 השלמות עקביות"
    progress_metric: str = "חזרות / דקות איכות"
    constraints: list[str] = Field(default_factory=list)
    stop_condition: str = "כאב, סחרחורת או בקשת עצירה"
    review_date: str | None = None


class EvaluateChallengeRequest(BaseModel):
    user_id: str = "moshe"
    outcome: Literal["completed", "stalled", "failed", "not_done"] = "completed"
    pain_or_limitation: bool = False
    perceived_effort: int = Field(default=5, ge=1, le=10)
    resistance_level: int = Field(default=4, ge=1, le=10)
    requested_difficulty_delta: int = Field(default=0, ge=-3, le=3)
    notes: str | None = None


@router.get("/domains", operation_id="listGrowthDomains")
def list_growth_domains(user_id: str = "moshe", tier: str | None = None) -> dict[str, Any]:
    return GrowthChallengesAndPlayService().list_domains(user_id=user_id, tier=tier)


@router.post("/domains", operation_id="upsertGrowthDomain")
def upsert_growth_domain(request: UpsertDomainRequest) -> dict[str, Any]:
    return GrowthChallengesAndPlayService().upsert_domain(request.model_dump(exclude_none=True))


@router.post("/domains/activity", operation_id="recordGrowthDomainActivity")
def record_domain_activity(request: RecordDomainActivityRequest) -> dict[str, Any]:
    return GrowthChallengesAndPlayService().record_domain_activity(
        user_id=request.user_id,
        slug=request.slug,
        occurred_at=request.occurred_at,
    )


@router.post("/domains/neglect-check", operation_id="checkNeglectedGrowthDomains")
def check_neglected_domains(user_id: str = "moshe", neglect_threshold_days: int = 7) -> dict[str, Any]:
    return GrowthChallengesAndPlayService().check_neglected_domains(
        user_id=user_id,
        neglect_threshold_days=neglect_threshold_days,
    )


@router.post("/challenges", operation_id="createChallenge")
def create_challenge(request: CreateChallengeRequest) -> dict[str, Any]:
    return GrowthChallengesAndPlayService().create_challenge(request.model_dump(mode="json"))


@router.get("/challenges", operation_id="listChallenges")
def list_challenges(user_id: str = "moshe", status: str = "active") -> dict[str, Any]:
    return GrowthChallengesAndPlayService().list_challenges(user_id=user_id, status=status)


@router.post("/challenges/{challenge_id}/evaluate", operation_id="evaluateAndAdaptChallenge")
def evaluate_challenge(challenge_id: str, request: EvaluateChallengeRequest) -> dict[str, Any]:
    res = GrowthChallengesAndPlayService().evaluate_and_adapt_challenge(
        challenge_id,
        user_id=request.user_id,
        outcome=request.outcome,
        pain_or_limitation=request.pain_or_limitation,
        perceived_effort=request.perceived_effort,
        resistance_level=request.resistance_level,
        requested_difficulty_delta=request.requested_difficulty_delta,
        notes=request.notes,
    )
    if not res.get("success"):
        raise HTTPException(status_code=404, detail=res.get("error", "challenge-not-found"))
    return res


@router.get("/playful-state", operation_id="getPlayfulEngagementState")
def get_playful_state(user_id: str = "moshe") -> dict[str, Any]:
    return {"success": True, "playful_state": GrowthChallengesAndPlayService().get_playful_state(user_id=user_id)}
