from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Query

from app.auth import require_actions_key
from app.schemas.gpt import (
    GptAssessmentStartRequest,
    GptAssessmentStartResponse,
    GptMorningFlatResponse,
    GptMorningResponse,
    GptEchoResponse,
    GptStatusFlatResponse,
    GptStatusResponse,
    GptTrainingSessionRequest,
    GptTrainingSessionResponse,
)
from app.services.assessment import AssessmentAdapter
from app.services.context_service import ContextService
from app.services.self_trainer import SelfTrainerAdapter
from app.services.system_status import local_system_status

router = APIRouter(prefix="/api/gpt", tags=["gpt"], dependencies=[Depends(require_actions_key)])


@router.get("/status", response_model=GptStatusResponse, operation_id="getGptSystemStatus")
def get_gpt_system_status() -> dict:
    return {"success": True, "service": "compass", "systems": local_system_status()}


@router.get("/echo", response_model=GptEchoResponse, operation_id="compassEcho")
def compass_echo() -> dict:
    return {
        "success": True,
        "message": "COMPASS_ECHO_OK",
        "number": 42,
        "connected_systems": "echo_system",
    }


@router.get("/status-flat", response_model=GptStatusFlatResponse, operation_id="getCompassStatusFlatV2")
def get_compass_status_flat_v2() -> dict:
    systems = local_system_status()
    connected = sorted(name for name, status in systems.items() if status["connected"])
    disconnected = sorted(name for name, status in systems.items() if not status["connected"])
    lines = [
        f"{name}: {'connected' if status['connected'] else 'disconnected'}"
        + (f" ({status['warning']})" if status["warning"] else "")
        for name, status in sorted(systems.items())
    ]
    return {
        "success": True,
        "service": "compass",
        "connected_systems": ", ".join(connected),
        "disconnected_systems": ", ".join(disconnected),
        "systems_text": "\n".join(lines),
        "connected_count": len(connected),
        "disconnected_count": len(disconnected),
    }


@router.get("/morning", response_model=GptMorningResponse, operation_id="getGptMorningBrief")
def get_gpt_morning_brief(
    user_id: str = Query(default="moshe"),
    target_date: date = Query(alias="date"),
    timezone: str = Query(default="Asia/Jerusalem"),
    include: str = Query(default="training,economic_manager,assessment,task_commander,administrative"),
) -> dict:
    include_list = [item.strip() for item in include.split(",") if item.strip()]
    context = ContextService().morning_context(
        user_id=user_id,
        target_date=target_date,
        timezone=timezone,
        include=include_list,
    )
    systems = local_system_status()
    training_progress = context.get("training", {}).get("progress", {}).get("result", {})
    if not isinstance(training_progress, dict):
        training_progress = {}
    suggested_focus = context.get("suggested_focus", [])
    warnings = context.get("warnings", [])
    connected = sorted(name for name, status in systems.items() if status["connected"])
    disconnected = sorted(name for name, status in systems.items() if not status["connected"])
    summary = (
        f"Connected systems: {', '.join(connected) or 'none'}. "
        f"Disconnected systems: {', '.join(disconnected) or 'none'}. "
        f"Open Compass tasks: {len(context.get('open_tasks', []))}. "
        f"Recent Compass events: {len(context.get('recent_events', []))}."
    )
    return {
        "success": True,
        "user_id": user_id,
        "date": target_date,
        "timezone": timezone,
        "systems": systems,
        "warnings": warnings[:10],
        "summary": summary,
        "suggested_focus": suggested_focus[:5],
        "counts": {
            "open_tasks": len(context.get("open_tasks", [])),
            "recent_events": len(context.get("recent_events", [])),
            "recent_daily_plans": len(context.get("recent_daily_plans", [])),
            "warnings": len(warnings),
        },
        "training_sessions_completed": int(training_progress.get("sessions_completed") or 0),
        "training_next_focus": str(training_progress.get("suggested_next_focus") or ""),
    }


@router.get("/morning-flat", response_model=GptMorningFlatResponse, operation_id="getCompassMorningFlatV2")
def get_compass_morning_flat_v2(
    user_id: str = Query(default="moshe"),
    target_date: date = Query(alias="date"),
    timezone: str = Query(default="Asia/Jerusalem"),
    include: str = Query(default="training,economic_manager,assessment,task_commander,administrative"),
) -> dict:
    include_list = [item.strip() for item in include.split(",") if item.strip()]
    context = ContextService().morning_context(
        user_id=user_id,
        target_date=target_date,
        timezone=timezone,
        include=include_list,
    )
    systems = local_system_status()
    connected = sorted(name for name, status in systems.items() if status["connected"])
    disconnected = sorted(name for name, status in systems.items() if not status["connected"])
    training_progress = context.get("training", {}).get("progress", {}).get("result", {})
    if not isinstance(training_progress, dict):
        training_progress = {}
    warnings = [str(item) for item in context.get("warnings", [])[:10]]
    open_task_count = len(context.get("open_tasks", []))
    recent_event_count = len(context.get("recent_events", []))
    recent_daily_plan_count = len(context.get("recent_daily_plans", []))
    summary = (
        f"Compass morning brief for {user_id} on {target_date}. "
        f"Connected: {', '.join(connected) or 'none'}. "
        f"Disconnected: {', '.join(disconnected) or 'none'}. "
        f"Open tasks: {open_task_count}. Recent events: {recent_event_count}. "
        f"Warnings: {len(warnings)}."
    )
    return {
        "success": True,
        "user_id": user_id,
        "date": target_date,
        "timezone": timezone,
        "summary": summary,
        "connected_systems": ", ".join(connected),
        "disconnected_systems": ", ".join(disconnected),
        "warnings_text": "\n".join(warnings),
        "open_task_count": open_task_count,
        "recent_event_count": recent_event_count,
        "recent_daily_plan_count": recent_daily_plan_count,
        "training_sessions_completed": int(training_progress.get("sessions_completed") or 0),
        "training_next_focus": str(training_progress.get("suggested_next_focus") or ""),
    }


@router.post(
    "/training/session",
    response_model=GptTrainingSessionResponse,
    operation_id="saveGptTrainingSession",
)
def save_gpt_training_session(request: GptTrainingSessionRequest) -> dict:
    result = SelfTrainerAdapter().save_session(request.model_dump(mode="json"))
    body = result.get("result", {}) if isinstance(result.get("result"), dict) else {}
    return {
        "success": bool(result.get("connected") and body.get("success", True)),
        "connected": bool(result.get("connected")),
        "session_id": str(body.get("session_id") or ""),
        "message": str(body.get("message") or ""),
        "warning": str(result.get("warning") or ""),
    }


@router.post(
    "/assessment/start",
    response_model=GptAssessmentStartResponse,
    operation_id="startGptAssessment",
)
def start_gpt_assessment(request: GptAssessmentStartRequest) -> dict:
    context = {**request.context, "days": request.days, "dry_run": request.dry_run}
    assessment = AssessmentAdapter()
    result = assessment.invoke_agent(
        {
            "task": request.task,
            "user_id": request.user_id,
            "context": context,
            "expected_output": request.expected_output,
            "risk_level": request.risk_level,
        }
    )
    ui_urls = assessment.ui_urls()
    ui_result = assessment.open_ui(request.ui_target) if request.open_ui else {"opened": False, "url": ui_urls[request.ui_target]}
    body = result.get("result", {}) if isinstance(result.get("result"), dict) else result
    return {
        "success": bool(result.get("connected")),
        "connected": bool(result.get("connected")),
        "task": request.task,
        "summary": str(body.get("summary") or ""),
        "confidence": str(body.get("confidence") or ""),
        "findings": body.get("findings", []) if isinstance(body.get("findings", []), list) else [],
        "signals": body.get("signals", []) if isinstance(body.get("signals", []), list) else [],
        "recommendations": body.get("recommendations", []) if isinstance(body.get("recommendations", []), list) else [],
        "proposed_actions": body.get("proposed_actions", []) if isinstance(body.get("proposed_actions", []), list) else [],
        "requires_approval": bool(body.get("requires_approval")),
        "ui_url": str(ui_result.get("url") or ui_urls[request.ui_target]),
        "ui_urls": ui_urls,
        "ui_opened": bool(ui_result.get("opened")),
        "user_instruction": (
            f"Open the {request.ui_target} assessment UI and run one objective check. "
            "Use the returned assessment finding before creating a self_manage exercise."
        ),
        "warning": str(result.get("warning") or ""),
    }
