from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends

from app.auth import require_actions_key
from app.repository import CompassRepository
from app.schemas.common import WriteResult
from app.schemas.daily_plan import SaveDailyPlanRequest
from app.services.frogs_service import FrogsService
from app.services.rules_engine import RulesEngineAdapter

router = APIRouter(tags=["daily-plan"], dependencies=[Depends(require_actions_key)])


def _estimate_planned_minutes(scheduled_tasks: list[dict]) -> int:
    total = 0
    for item in scheduled_tasks:
        if isinstance(item, dict):
            total += int(item.get("minutes") or item.get("estimated_minutes") or item.get("duration_minutes") or 30)
    return total


@router.post("/api/daily-plan", response_model=WriteResult, operation_id="saveDailyPlan")
def save_daily_plan(request: SaveDailyPlanRequest) -> dict:
    repo = CompassRepository()
    if request.idempotency_key and (cached := repo.get_idempotent_response(request.idempotency_key)):
        return {**cached, "already_existed": True}

    payload = request.model_dump(mode="json")
    available_minutes = request.available_minutes if request.available_minutes is not None else 180
    energy_level = request.energy_level if request.energy_level is not None else 3

    frogs_svc = FrogsService()
    active_frogs_info = frogs_svc.list_frogs(user_id=request.user_id, status="active")
    active_frogs_count = active_frogs_info["active_count"]
    selected_frog_info = None

    has_frog_task = any(
        isinstance(t, dict) and (t.get("is_frog") or t.get("category") == "frog")
        for t in payload.get("scheduled_tasks", [])
    )
    if active_frogs_count > 0 and not has_frog_task:
        selected_frog_info = frogs_svc.select_daily_frog(
            user_id=request.user_id,
            target_date=request.date,
            energy_level=energy_level,
            available_minutes=available_minutes,
            sync_to_task_commander=True,
        )
        if selected_frog_info.get("selected") and selected_frog_info.get("selected_frog"):
            f = selected_frog_info["selected_frog"]
            payload["scheduled_tasks"] = [
                {
                    "title": f"🐸 צפרדע יומית: {f['name']}",
                    "frog_id": f["frog_id"],
                    "is_frog": True,
                    "category": "frog",
                    "domain": f["domain"],
                    "slot": selected_frog_info["recommended_slot"],
                    "minutes": f["estimated_minutes"],
                }
            ] + list(payload.get("scheduled_tasks", []))

    planned_minutes = _estimate_planned_minutes(payload.get("scheduled_tasks", []))
    is_overloaded = planned_minutes > available_minutes

    core_domains_count = sum(
        1
        for item in payload.get("scheduled_tasks", [])
        if isinstance(item, dict) and str(item.get("domain") or "").lower() in {"mental", "physical", "ai", "ai_professional", "core"}
    )

    structured_event = {
        "event_id": f"evt_plan_{uuid4().hex[:10]}",
        "event_type": "daily_plan.evaluate",
        "event_version": "1.0",
        "source": "compass.daily_plan",
        "user_id": request.user_id,
        "occurred_at": datetime.now(timezone.utc).isoformat(),
        "idempotency_key": f"plan_eval_{request.idempotency_key or uuid4().hex[:10]}",
        "payload": {
            "date": str(request.date),
            "energy_level": energy_level,
            "available_minutes": available_minutes,
            "planned_minutes": planned_minutes,
            "is_overloaded": is_overloaded,
            "core_domains_scheduled_count": core_domains_count,
            "active_frogs_count": active_frogs_count,
            "resistance_level": int(payload.get("resistance_level") or 0),
        },
        "metadata": {"dry_run": False, "requested_actions": []},
    }

    rules_adapter = RulesEngineAdapter()
    structured_eval = rules_adapter.evaluate_event(structured_event, actor=request.user_id)
    legacy_eval = rules_adapter.evaluate(
        {
            "event_type": "daily_plan_saved",
            "user_id": request.user_id,
            "date": str(request.date),
            "energy_level": request.energy_level,
            "available_minutes": request.available_minutes,
            "outcomes": request.outcomes,
            "scheduled_tasks": request.scheduled_tasks,
            "risks": request.risks,
        },
        actor=request.user_id,
    )

    warnings: list[str] = []
    if not structured_eval.get("connected") and not legacy_eval.get("connected"):
        warnings.append(str(structured_eval.get("warning") or legacy_eval.get("warning") or "rules engine unavailable"))
        payload["status"] = "rules_engine_unavailable"
        result = repo.save_daily_plan(payload)
        result["status"] = "rules_engine_unavailable"
        result["warnings"] = warnings
        result["downstream"] = {"rules_engine": structured_eval}
        repo.audit("daily_plan.rules_unavailable", request.user_id, payload)
        return result

    eval_result = structured_eval.get("result", {}) if isinstance(structured_eval, dict) else {}
    if structured_eval.get("connected") and eval_result:
        repo.save_rule_evaluation(structured_event, eval_result)

    legacy_payload = legacy_eval.get("result") if isinstance(legacy_eval, dict) else {}
    requires_approval = (
        eval_result.get("final_decision") == "require_approval"
        or bool(eval_result.get("approval_required_actions"))
        or (isinstance(legacy_payload, dict) and bool(legacy_payload.get("requires_review")))
    )

    # Low energy automatic adaptation (PLAN-001)
    if energy_level <= 2:
        adapted_tasks = []
        for t in payload.get("scheduled_tasks", []):
            if isinstance(t, dict):
                t_copy = dict(t)
                orig_min = int(t_copy.get("minutes") or t_copy.get("estimated_minutes") or 30)
                t_copy["minutes"] = max(5, orig_min // 2)
                t_copy["adapted_for_low_energy"] = True
                adapted_tasks.append(t_copy)
            else:
                adapted_tasks.append(t)
        payload["scheduled_tasks"] = adapted_tasks
        warnings.append("PLAN-001: התוכנית הותאמה אוטומטית לאנרגיה נמוכה (גרסאות קצרות/מינימליות).")

    if requires_approval:
        payload["status"] = "pending_approval"
    else:
        payload["status"] = "active" if request.status == "approved" else request.status

    result = repo.save_daily_plan(payload)
    result["status"] = payload["status"]

    if requires_approval:
        approval = repo.create_approval_request(
            {
                "user_id": request.user_id,
                "title": f"Review daily plan for {request.date}",
                "description": eval_result.get("explanation") or "rules_engine marked this daily plan as requiring review.",
                "requested_by": "rules_engine",
                "action_type": "daily_plan.review",
                "risk_level": eval_result.get("risk_level", "medium"),
                "proposed_action": {"plan_id": result["resource_id"], **payload},
                "rule_result": eval_result or legacy_payload,
            }
        )
        warnings.append("daily plan requires approval before activation")
        result["approval_request_id"] = approval["resource_id"]

    if warnings:
        result["warnings"] = warnings
    result["downstream"] = {
        "rules_engine": structured_eval if structured_eval.get("connected") else legacy_eval,
        "evaluation_id": eval_result.get("evaluation_id"),
        "daily_frog": selected_frog_info,
    }
    repo.log_ai_usage(
        {
            "user_id": request.user_id,
            "usage_type": "deterministic_bypass",
            "purpose": "daily_plan.evaluate_and_save",
            "reason": "Rule Engine First deterministic evaluation (0 LLM tokens)",
        }
    )
    repo.audit("daily_plan.save", request.user_id, payload)
    repo.remember_idempotent_response(request.idempotency_key, "daily_plan.save", result)
    return result
