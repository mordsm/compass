from __future__ import annotations

from fastapi import APIRouter, Depends

from app.auth import require_actions_key
from typing import Any

from app.schemas.context import MorningContextRequest, MorningContextResponse, MorningContextSummaryResponse
from app.services.context_service import ContextService

router = APIRouter(prefix="/api/context", tags=["context"], dependencies=[Depends(require_actions_key)])


@router.post("/morning", response_model=MorningContextResponse, operation_id="getMorningContext")
def get_morning_context(request: MorningContextRequest) -> dict:
    return ContextService().morning_context(
        user_id=request.user_id,
        target_date=request.date,
        timezone=request.timezone,
        include=request.include,
    )


@router.post(
    "/morning/summary",
    response_model=MorningContextSummaryResponse,
    operation_id="getMorningContextSummary",
)
def get_morning_context_summary(request: MorningContextRequest) -> dict:
    context = ContextService().morning_context(
        user_id=request.user_id,
        target_date=request.date,
        timezone=request.timezone,
        include=request.include,
    )
    systems = {
        name: _system_status(context.get(name, {}))
        for name in (
            "self_management",
            "training",
            "assessment",
            "mail",
            "economic_manager",
            "task_commander",
            "administrative",
        )
        if not request.include or name in request.include or (name == "training" and "self_trainer" in request.include)
    }
    training_progress = (
        context.get("training", {})
        .get("progress", {})
        .get("result", {})
    )
    economic_summary = context.get("economic_manager", {}).get("summary", {})
    return {
        "success": True,
        "user_id": context["user_id"],
        "date": context["date"],
        "timezone": context["timezone"],
        "systems": systems,
        "warnings": context.get("warnings", []),
        "open_task_count": len(context.get("open_tasks", [])),
        "recent_event_count": len(context.get("recent_events", [])),
        "recent_daily_plan_count": len(context.get("recent_daily_plans", [])),
        "suggested_focus": context.get("suggested_focus", []),
        "training_sessions_completed": training_progress.get("sessions_completed"),
        "training_next_focus": training_progress.get("suggested_next_focus"),
        "economic_manager_summary": economic_summary if isinstance(economic_summary, dict) else {},
    }


def _system_status(section: dict[str, Any]) -> dict[str, Any]:
    warnings = []
    connected = False
    for value in section.values():
        if isinstance(value, dict):
            if value.get("connected"):
                connected = True
            if value.get("warning"):
                warnings.append(str(value["warning"]))
    return {
        "connected": connected,
        "warning": "; ".join(warnings) if warnings else None,
    }
