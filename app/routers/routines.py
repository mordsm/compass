from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.auth import require_actions_key
from app.services.routines_service import RoutinesAndExecutionService

router = APIRouter(prefix="/api/routines", tags=["routines"], dependencies=[Depends(require_actions_key)])


class UpdatePrepProtocolRequest(BaseModel):
    user_id: str = "moshe"
    name: str | None = None
    steps: list[dict[str, Any]] | None = None
    breathing_seconds: int | None = Field(default=None, ge=20, le=120)
    pleasant_starter_action: str | None = None
    pleasant_starter_max_seconds: int | None = Field(default=None, ge=10, le=90)
    sampling_interval: int | None = Field(default=None, ge=1, le=20)


class LogPrepExecutionRequest(BaseModel):
    user_id: str = "moshe"
    target_type: str = "frog"
    target_id: str | None = None
    tension_before: int | None = Field(default=None, ge=0, le=10)
    tension_after_prep: int | None = Field(default=None, ge=0, le=10)
    feeling_after_execution: str | None = None
    action_started: bool = True
    action_completed: bool = False


class CreateRoutineRequest(BaseModel):
    user_id: str = "moshe"
    routine_id: str | None = None
    name: str
    domain: str = "physical"
    start_condition: str = "זמן בוקר או סיום קפה"
    action_sequence: list[str] = Field(default_factory=list)
    trigger_time_or_event: str = "08:00"
    frequency: str = "daily"
    minimum_viable_version: str = "2 דקות של תנועה קלה / סט בודד"
    estimated_minutes: int = Field(default=20, ge=2, le=180)
    minimum_minutes: int | None = Field(default=None, ge=1, le=60)
    skip_condition: str = "כאב חריג, מחלה או אירוע חירום"
    completion_condition: str = "ביצוע הרצף המלא או הגרסה המינימלית"
    difficulty_level: int = Field(default=4, ge=1, le=10)


class ReportRoutineExecutionRequest(BaseModel):
    user_id: str = "moshe"
    outcome: Literal["completed", "minimum_completed", "skipped"]
    used_minimum_version: bool = False
    resistance_level: int | None = Field(default=None, ge=1, le=10)
    energy_level: int | None = Field(default=None, ge=1, le=5)
    notes: str | None = None


@router.get("/prep-protocol", operation_id="getPrepProtocol")
def get_prep_protocol(user_id: str = "moshe") -> dict[str, Any]:
    return {"success": True, "protocol": RoutinesAndExecutionService().get_or_create_prep_protocol(user_id=user_id)}


@router.patch("/prep-protocol", operation_id="updatePrepProtocol")
def update_prep_protocol(request: UpdatePrepProtocolRequest) -> dict[str, Any]:
    patch = request.model_dump(exclude_none=True, exclude={"user_id"})
    updated = RoutinesAndExecutionService().update_prep_protocol(request.user_id, patch)
    return {"success": True, "protocol": updated}


@router.post("/prep-protocol/log", operation_id="logPrepProtocolExecution")
def log_prep_execution(request: LogPrepExecutionRequest) -> dict[str, Any]:
    return RoutinesAndExecutionService().log_prep_execution(request.model_dump(mode="json"))


@router.post("", operation_id="createRoutine")
def create_routine(request: CreateRoutineRequest) -> dict[str, Any]:
    return RoutinesAndExecutionService().create_routine(request.model_dump(mode="json"))


@router.get("", operation_id="listRoutines")
def list_routines(user_id: str = "moshe", status: str = "active") -> dict[str, Any]:
    return RoutinesAndExecutionService().list_routines(user_id=user_id, status=status)


@router.post("/{routine_id}/report", operation_id="reportRoutineExecution")
def report_routine_execution(routine_id: str, request: ReportRoutineExecutionRequest) -> dict[str, Any]:
    res = RoutinesAndExecutionService().report_routine_execution(
        routine_id,
        outcome=request.outcome,
        user_id=request.user_id,
        used_minimum_version=request.used_minimum_version,
        resistance_level=request.resistance_level,
        energy_level=request.energy_level,
        notes=request.notes,
    )
    if not res.get("success"):
        raise HTTPException(status_code=404, detail=res.get("error", "routine-not-found"))
    return res


@router.get("/executor/next-action", operation_id="getExecutorNextAction")
def get_executor_next_action(
    user_id: str = "moshe",
    energy_level: int = 3,
    available_minutes: int = 45,
    resistance_level: int = 4,
    safety_constraints: str = "",
) -> dict[str, Any]:
    constraints = [c.strip() for c in safety_constraints.split(",") if c.strip()]
    return RoutinesAndExecutionService().get_executor_next_action(
        user_id=user_id,
        energy_level=energy_level,
        available_minutes=available_minutes,
        resistance_level=resistance_level,
        active_safety_constraints=constraints,
    )
