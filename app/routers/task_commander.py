from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from app.auth import require_actions_key
from app.services.task_commander import TaskCommanderAdapter

router = APIRouter(prefix="/api/task-commander", tags=["task-commander"], dependencies=[Depends(require_actions_key)])


class CreateOperationalTaskRequest(BaseModel):
    user_id: str = "moshe"
    task_id: str | None = None
    title: str
    description: str | None = None
    priority: str = "normal"
    category: str | None = None
    task_type: str | None = None
    due_at: str | None = None
    deadline_at: str | None = None
    recurrence_rule: str | None = None
    estimated_minutes: int = 25
    occurrence_date: str | None = None
    source: str = "compass"


class SnoozeInstanceRequest(BaseModel):
    minutes: int = 60


@router.get("/health", operation_id="getTaskCommanderHealth")
def get_health() -> dict[str, Any]:
    return TaskCommanderAdapter().health()


@router.get("/status", operation_id="getTaskCommanderStatus")
def get_status(limit: int = 10, user_id: str = "moshe") -> dict[str, Any]:
    return TaskCommanderAdapter().status(limit=limit, user_id=user_id)


@router.get("/today", operation_id="getTaskCommanderToday")
def get_today(limit: int = 20, user_id: str = "moshe") -> dict[str, Any]:
    return TaskCommanderAdapter().today(limit=limit, user_id=user_id)


@router.get("/overdue", operation_id="getTaskCommanderOverdue")
def get_overdue(limit: int = 20, user_id: str = "moshe") -> dict[str, Any]:
    return TaskCommanderAdapter().overdue(limit=limit, user_id=user_id)


@router.post("/tasks", operation_id="createTaskCommanderTask")
def create_task(request: CreateOperationalTaskRequest) -> dict[str, Any]:
    return TaskCommanderAdapter().create_task(request.model_dump(mode="json"))


@router.post("/instances/generate", operation_id="generateTaskCommanderInstances")
def generate_instances(days: int = 2, user_id: str = "moshe") -> dict[str, Any]:
    return TaskCommanderAdapter().generate_instances(days=days, user_id=user_id)


@router.post("/instances/{instance_id}/done", operation_id="markTaskCommanderInstanceDone")
def mark_instance_done(instance_id: str) -> dict[str, Any]:
    return TaskCommanderAdapter().mark_done(instance_id)


@router.post("/instances/{instance_id}/snooze", operation_id="snoozeTaskCommanderInstance")
def snooze_instance(instance_id: str, request: SnoozeInstanceRequest) -> dict[str, Any]:
    return TaskCommanderAdapter().snooze(instance_id, minutes=request.minutes)


@router.post("/instances/{instance_id}/skip", operation_id="skipTaskCommanderInstance")
def skip_instance(instance_id: str) -> dict[str, Any]:
    return TaskCommanderAdapter().skip(instance_id)
