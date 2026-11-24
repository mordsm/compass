from __future__ import annotations

from datetime import date as dt_date
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.auth import require_actions_key
from app.services.frogs_service import FrogsService

router = APIRouter(prefix="/api/frogs", tags=["frogs"], dependencies=[Depends(require_actions_key)])


class CreateFrogRequest(BaseModel):
    user_id: str = "moshe"
    frog_id: str | None = None
    name: str
    description: str = ""
    domain: str = "core"
    frog_type: Literal["one_time", "ongoing"] = "one_time"
    importance: int = Field(default=7, ge=1, le=10)
    resistance_level: int = Field(default=7, ge=1, le=10)
    difficulty_level: int = Field(default=5, ge=1, le=10)
    urgency: int = Field(default=5, ge=1, le=10)
    estimated_minutes: int = Field(default=25, ge=5, le=240)
    completion_condition: str = "השלמת הפעולה המוגדרת"
    safety_constraints: list[str] = Field(default_factory=list)
    idempotency_key: str | None = None


class UpdateFrogScoresRequest(BaseModel):
    user_id: str = "moshe"
    name: str | None = None
    description: str | None = None
    domain: str | None = None
    importance: int | None = Field(default=None, ge=1, le=10)
    resistance_level: int | None = Field(default=None, ge=1, le=10)
    difficulty_level: int | None = Field(default=None, ge=1, le=10)
    urgency: int | None = Field(default=None, ge=1, le=10)
    estimated_minutes: int | None = Field(default=None, ge=5, le=240)
    completion_condition: str | None = None
    safety_constraints: list[str] | None = None


class DailyFrogSelectRequest(BaseModel):
    user_id: str = "moshe"
    date: dt_date | None = None
    energy_level: int = Field(default=4, ge=1, le=5)
    available_minutes: int = Field(default=60, ge=5)
    active_safety_constraints: list[str] = Field(default_factory=list)
    sync_to_task_commander: bool = True


class OverrideDailyFrogRequest(BaseModel):
    user_id: str = "moshe"
    plan_date: str | None = None
    action: Literal["replace", "defer", "cancel"]
    replacement_frog_id: str | None = None
    reason: str = ""


class ReportFrogExecutionRequest(BaseModel):
    user_id: str = "moshe"
    outcome: Literal["completed", "partial", "not_done", "deferred", "no_longer_resisted"]
    notes: str | None = None
    energy_level: int | None = Field(default=None, ge=1, le=5)
    tension_before: int | None = Field(default=None, ge=0, le=10)
    tension_after: int | None = Field(default=None, ge=0, le=10)
    approval_confirmed: bool = False


class RemoveFrogRequest(BaseModel):
    user_id: str = "moshe"
    reason: str = ""
    approval_confirmed: bool = False


@router.post("", operation_id="createFrog")
def create_frog(request: CreateFrogRequest) -> dict[str, Any]:
    return FrogsService().create_frog(request.model_dump(mode="json"))


@router.get("", operation_id="listFrogs")
def list_frogs(user_id: str = "moshe", status: str = "active") -> dict[str, Any]:
    return FrogsService().list_frogs(user_id=user_id, status=status)


@router.get("/{frog_id}", operation_id="getFrog")
def get_frog(frog_id: str) -> dict[str, Any]:
    frog = FrogsService().get_frog(frog_id)
    if not frog:
        raise HTTPException(status_code=404, detail="frog-not-found")
    return {"success": True, "frog": frog}


@router.patch("/{frog_id}", operation_id="updateFrogScores")
def update_frog_scores(frog_id: str, request: UpdateFrogScoresRequest) -> dict[str, Any]:
    patch = request.model_dump(exclude_none=True, exclude={"user_id"})
    updated = FrogsService().update_frog_scores(frog_id, patch, user_id=request.user_id)
    if not updated:
        raise HTTPException(status_code=404, detail="frog-not-found")
    return {"success": True, "frog": updated}


@router.post("/evening-check", operation_id="runEveningFrogPoolCheck")
def run_evening_frog_pool_check(user_id: str = "moshe") -> dict[str, Any]:
    return FrogsService().evening_pool_check(user_id=user_id)


@router.post("/daily-selection", operation_id="selectDailyFrog")
def select_daily_frog(request: DailyFrogSelectRequest) -> dict[str, Any]:
    return FrogsService().select_daily_frog(
        user_id=request.user_id,
        target_date=request.date,
        energy_level=request.energy_level,
        available_minutes=request.available_minutes,
        active_safety_constraints=request.active_safety_constraints,
        sync_to_task_commander=request.sync_to_task_commander,
    )


@router.post("/daily-selection/override", operation_id="overrideDailyFrogSelection")
def override_daily_selection(request: OverrideDailyFrogRequest) -> dict[str, Any]:
    return FrogsService().override_daily_selection(
        user_id=request.user_id,
        plan_date=request.plan_date,
        action=request.action,
        replacement_frog_id=request.replacement_frog_id,
        reason=request.reason,
    )


@router.post("/{frog_id}/report", operation_id="reportFrogExecution")
def report_frog_execution(frog_id: str, request: ReportFrogExecutionRequest) -> dict[str, Any]:
    res = FrogsService().report_frog_execution(
        frog_id,
        outcome=request.outcome,
        user_id=request.user_id,
        notes=request.notes,
        energy_level=request.energy_level,
        tension_before=request.tension_before,
        tension_after=request.tension_after,
        approval_confirmed=request.approval_confirmed,
    )
    if not res.get("success"):
        raise HTTPException(status_code=404, detail=res.get("error", "frog-not-found"))
    return res


@router.post("/{frog_id}/remove", operation_id="requestRemoveFrog")
def request_remove_frog(frog_id: str, request: RemoveFrogRequest) -> dict[str, Any]:
    res = FrogsService().request_remove_frog(
        frog_id,
        user_id=request.user_id,
        reason=request.reason,
        approval_confirmed=request.approval_confirmed,
    )
    if not res.get("success"):
        raise HTTPException(status_code=404, detail=res.get("error", "frog-not-found"))
    return res
