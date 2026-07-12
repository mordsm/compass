from __future__ import annotations

from fastapi import APIRouter, Depends

from app.auth import require_actions_key
from app.repository import CompassRepository
from app.schemas.common import WriteResult
from app.schemas.daily_plan import SaveDailyPlanRequest
from app.services.rules_engine import RulesEngineAdapter

router = APIRouter(tags=["daily-plan"], dependencies=[Depends(require_actions_key)])


@router.post("/api/daily-plan", response_model=WriteResult, operation_id="saveDailyPlan")
def save_daily_plan(request: SaveDailyPlanRequest) -> dict:
    repo = CompassRepository()
    if request.idempotency_key and (cached := repo.get_idempotent_response(request.idempotency_key)):
        return {**cached, "already_existed": True}
    payload = request.model_dump(mode="json")
    result = repo.save_daily_plan(payload)
    rules_result = RulesEngineAdapter().evaluate(
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
    if not rules_result.get("connected"):
        result["warnings"] = [rules_result.get("warning", "rules engine unavailable")]
    rule_payload = rules_result.get("result") if isinstance(rules_result, dict) else {}
    if isinstance(rule_payload, dict) and rule_payload.get("requires_review"):
        approval = repo.create_approval_request(
            {
                "user_id": request.user_id,
                "title": f"Review daily plan for {request.date}",
                "description": "rules_engine marked this daily plan as requiring review.",
                "requested_by": "rules_engine",
                "action_type": "daily_plan.review",
                "risk_level": "medium",
                "proposed_action": payload,
                "rule_result": rule_payload,
            }
        )
        result.setdefault("warnings", []).append("daily plan requires approval")
        result["approval_request_id"] = approval["resource_id"]
    result["downstream"] = {"rules_engine": rules_result}
    repo.audit("daily_plan.save", request.user_id, payload)
    repo.remember_idempotent_response(request.idempotency_key, "daily_plan.save", result)
    return result
