from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.repository import CompassRepository
from app.services.frogs_service import FrogsService
from app.services.growth_service import GrowthChallengesAndPlayService
from app.services.mental_skills import MentalSkillsService
from app.services.routines_service import RoutinesAndExecutionService
from app.services.rules_engine import RulesEngineAdapter
from app.services.system_status import local_system_status
from app.services.task_commander import TaskCommanderAdapter

router = APIRouter(prefix="/api/control-center", tags=["control-center"])


class RuleUpdateRequest(BaseModel):
    user_id: str = "moshe"
    name: str | None = None
    description: str | None = None
    priority: int | None = None
    enabled: bool | None = None
    approval_required: bool | None = None
    explanation_template: str | None = None
    conditions: list[dict[str, Any]] | None = None
    effects: list[dict[str, Any]] | None = None
    change_note: str = "Updated via System Control Center"


class RuleRollbackRequest(BaseModel):
    user_id: str = "moshe"
    target_version: int


class CancelDecisionRequest(BaseModel):
    user_id: str = "moshe"
    reason: str = "Cancelled by user before execution"


class PolicyUpdateRequest(BaseModel):
    user_id: str = "moshe"
    active_role: str | None = None
    automation_paused: bool | None = None
    max_daily_minutes: int | None = None
    max_challenge_difficulty: int | None = None
    allow_auto_order_actions: bool | None = None
    allow_auto_minimum_viable: bool | None = None
    priority_weights: dict[str, int] | None = None
    approval_confirmed: bool = False


@router.get("/overview", operation_id="getSystemControlCenterOverview")
def get_control_center_overview(user_id: str = Query(default="moshe")) -> dict[str, Any]:
    repo = CompassRepository()
    rules_adapter = RulesEngineAdapter()
    tc = TaskCommanderAdapter()

    catalog = rules_adapter.get_catalog()
    policy = repo.get_user_autonomy_policy(user_id)
    recent_decisions = repo.list_recent_rule_evaluations(user_id=user_id, limit=20)
    pending_approvals = repo.list_approval_requests(user_id=user_id, status="pending", limit=25)
    weekly_progress = repo.get_weekly_progress(user_id=user_id)
    ai_usage = repo.get_ai_usage_summary(user_id=user_id)
    tc_status = tc.status(limit=15, user_id=user_id)
    recent_plans = repo.list_recent_daily_plans(user_id=user_id, limit=5)
    frogs_status = FrogsService().list_frogs(user_id=user_id, status="active")
    routines_svc = RoutinesAndExecutionService()
    routines_status = routines_svc.list_routines(user_id=user_id, status="active")
    prep_protocol = routines_svc.get_or_create_prep_protocol(user_id=user_id)
    growth_svc = GrowthChallengesAndPlayService()
    growth_domains = growth_svc.list_domains(user_id=user_id)
    active_challenges = growth_svc.list_challenges(user_id=user_id, status="active")
    playful_state = growth_svc.get_playful_state(user_id=user_id)
    mental_assessment = MentalSkillsService().generate_monthly_mental_assessment(user_id=user_id)

    try:
        services_status = local_system_status()
    except Exception:
        services_status = {}
    services_status["task_commander"] = tc.health()
    services_status["rules_engine"] = {"connected": len(catalog) > 0, "mode": "in_process", "rules_count": len(catalog)}

    return {
        "success": True,
        "user_id": user_id,
        "policy": policy,
        "rules_summary": {
            "total_rules": len(catalog),
            "enabled_rules": sum(1 for r in catalog if r.get("enabled", True)),
            "disabled_rules": sum(1 for r in catalog if not r.get("enabled", True)),
        },
        "rules_catalog": catalog,
        "recent_decisions": recent_decisions,
        "pending_approvals": pending_approvals,
        "frogs": frogs_status,
        "routines": routines_status,
        "prep_protocol": prep_protocol,
        "growth_domains": growth_domains,
        "challenges": active_challenges,
        "playful_engagement": playful_state,
        "mental_progress_assessment": mental_assessment,
        "task_commander": tc_status,
        "recent_daily_plans": recent_plans,
        "weekly_progress": weekly_progress,
        "ai_usage": ai_usage,
        "connected_services": services_status,
    }


@router.get("/rules", operation_id="listRulesCatalog")
def list_rules_catalog(domain: str | None = None) -> dict[str, Any]:
    catalog = RulesEngineAdapter().get_catalog()
    if domain:
        catalog = [r for r in catalog if str(r.get("domain", "")).lower() == domain.lower()]
    return {"success": True, "count": len(catalog), "rules": catalog}


@router.patch("/rules/{rule_id}", operation_id="updateCatalogRule")
def update_catalog_rule(rule_id: str, request: RuleUpdateRequest) -> dict[str, Any]:
    repo = CompassRepository()
    catalog = RulesEngineAdapter().get_catalog()
    target = next((r for r in catalog if r["rule_id"] == rule_id), None)
    if not target:
        raise HTTPException(status_code=404, detail="rule-not-found")

    # Ensure version 1 baseline is recorded before applying update
    existing_versions = repo.list_rule_versions(rule_id, initial_snapshot=target)
    if len(existing_versions) == 1 and not repo.get_rule_overrides_map().get(rule_id):
        pass

    patch_data = request.model_dump(exclude_none=True, exclude={"user_id", "change_note"})
    updated_snapshot = dict(target)
    updated_snapshot.update(patch_data)

    saved = repo.save_rule_override(
        rule_id=rule_id,
        snapshot=updated_snapshot,
        updated_by=request.user_id,
        change_note=request.change_note,
        baseline_snapshot=target,
    )
    repo.audit("control_center.rule.update", request.user_id, {"rule_id": rule_id, "patch": patch_data, "version": saved["version"]})
    return {"success": True, "rule": saved}


@router.get("/rules/{rule_id}/versions", operation_id="getCatalogRuleVersions")
def get_catalog_rule_versions(rule_id: str) -> dict[str, Any]:
    repo = CompassRepository()
    catalog = RulesEngineAdapter().get_catalog()
    target = next((r for r in catalog if r["rule_id"] == rule_id), None)
    if not target:
        raise HTTPException(status_code=404, detail="rule-not-found")

    versions = repo.list_rule_versions(rule_id, initial_snapshot=target)
    return {"success": True, "rule_id": rule_id, "current_version": target["version"], "versions": versions}


@router.post("/rules/{rule_id}/rollback", operation_id="rollbackCatalogRuleVersion")
def rollback_catalog_rule_version(rule_id: str, request: RuleRollbackRequest) -> dict[str, Any]:
    repo = CompassRepository()
    catalog = RulesEngineAdapter().get_catalog()
    target = next((r for r in catalog if r["rule_id"] == rule_id), None)
    if not target:
        raise HTTPException(status_code=404, detail="rule-not-found")

    versions = repo.list_rule_versions(rule_id, initial_snapshot=target)
    match = next((v for v in versions if int(v["version"]) == int(request.target_version)), None)
    if not match:
        raise HTTPException(status_code=400, detail=f"version-{request.target_version}-not-found")

    restored_snapshot = dict(match["snapshot"])
    saved = repo.save_rule_override(
        rule_id=rule_id,
        snapshot=restored_snapshot,
        updated_by=request.user_id,
        change_note=f"Rollback to version {request.target_version}",
    )
    repo.audit(
        "control_center.rule.rollback",
        request.user_id,
        {"rule_id": rule_id, "restored_from_version": request.target_version, "new_version": saved["version"]},
    )
    return {
        "success": True,
        "rule_id": rule_id,
        "restored_from_version": request.target_version,
        "rule": saved,
    }


@router.get("/decisions/{evaluation_id}/explain", operation_id="explainRuleDecision")
def explain_rule_decision(evaluation_id: str) -> dict[str, Any]:
    repo = CompassRepository()
    decision = repo.get_rule_evaluation(evaluation_id)
    if not decision:
        raise HTTPException(status_code=404, detail="decision-not-found")

    matched = decision["matched_rules"]
    primary_rule = matched[0] if matched else None
    readable_lines = [
        f"מזהה החלטה: {decision['decision_id']}",
        f"זמן: {decision['created_at']}",
        f"אירוע מפעיל: {decision['event_type']} (מקור: {decision['source']})",
        f"החלטה סופית: {decision['final_decision']} (רמת סיכון: {decision['risk_level']})",
    ]
    if primary_rule:
        readable_lines.append(
            f"הכלל המוביל שהופעל: {primary_rule['rule_id']} — {primary_rule['name']} (גרסה v{primary_rule['version']}, עדיפות {primary_rule['priority']})"
        )
    else:
        readable_lines.append("הכלל שהופעל: לא נמצא כלל תואם (הופעלה ברירת מחדל).")

    if decision["conflicts_resolved"]:
        for c in decision["conflicts_resolved"]:
            readable_lines.append(
                f"הכרעת התנגשות: הכלל {c['winning_rule_id']} (עדיפות {c['winning_priority']}) גבר על {c['overridden_rule_id']} (עדיפות {c['overridden_priority']})."
            )

    readable_lines.append(f"נתונים בפועל שנבדקו: {decision['relevant_data']}")
    readable_lines.append(f"נימוק דטרמיניסטי: {decision['explanation']}")

    return {
        "success": True,
        "decision_id": decision["decision_id"],
        "timestamp": decision["created_at"],
        "trigger_event_type": decision["event_type"],
        "primary_rule": primary_rule,
        "matched_rules": matched,
        "relevant_data": decision["relevant_data"],
        "alternatives_considered": decision["alternatives_considered"],
        "conflicts_resolved": decision["conflicts_resolved"],
        "chosen_actions": decision["chosen_actions"],
        "blocked_actions": decision["blocked_actions"],
        "requires_approval": decision["requires_approval"],
        "execution_status": decision["execution_status"],
        "explanation": decision["explanation"],
        "readable_explanation_he": "\n".join(readable_lines),
    }


@router.post("/decisions/{evaluation_id}/cancel", operation_id="cancelDecisionBeforeExecution")
def cancel_decision_before_execution(evaluation_id: str, request: CancelDecisionRequest) -> dict[str, Any]:
    repo = CompassRepository()
    cancelled = repo.cancel_rule_evaluation(evaluation_id, cancelled_by=request.user_id, reason=request.reason)
    if not cancelled:
        raise HTTPException(status_code=404, detail="decision-not-found")
    repo.audit("control_center.decision.cancel", request.user_id, {"evaluation_id": evaluation_id, "reason": request.reason})
    return {"success": True, "decision": cancelled}


@router.patch("/policy", operation_id="updateUserAutonomyPolicy")
def update_user_autonomy_policy(request: PolicyUpdateRequest) -> dict[str, Any]:
    repo = CompassRepository()
    patch = request.model_dump(exclude_none=True, exclude={"user_id", "approval_confirmed"})

    material_fields = {"max_daily_minutes", "max_challenge_difficulty", "priority_weights"}
    is_material_change = any(k in patch for k in material_fields)

    if is_material_change and not request.approval_confirmed:
        event = {
            "event_id": f"evt_policy_{uuid4().hex[:10]}",
            "event_type": "policy.change_requested",
            "event_version": "1.0",
            "source": "compass.control_center",
            "user_id": request.user_id,
            "occurred_at": datetime.now(timezone.utc).isoformat(),
            "idempotency_key": f"policy_chg_{uuid4().hex[:10]}",
            "payload": {"is_material_change": True, "proposed_patch": patch},
            "metadata": {"dry_run": False, "requested_actions": []},
        }
        eval_res = RulesEngineAdapter().evaluate_event(event, actor=request.user_id)
        rule_result = eval_res.get("result", {})
        if eval_res.get("connected") and rule_result:
            repo.save_rule_evaluation(event, rule_result)

        if rule_result.get("final_decision") == "require_approval":
            approval = repo.create_approval_request(
                {
                    "user_id": request.user_id,
                    "title": "אישור שינוי מדיניות וגבולות אוטונומיה (CONTROL-001)",
                    "description": "שינוי מהותי בגבולות האוטונומיה או סדרי העדיפויות דורש אישור מפורש.",
                    "requested_by": request.user_id,
                    "action_type": "policy.update",
                    "risk_level": "high",
                    "proposed_action": patch,
                    "rule_result": rule_result,
                }
            )
            return {
                "success": True,
                "status": "approval_required",
                "approval_request_id": approval["resource_id"],
                "policy": repo.get_user_autonomy_policy(request.user_id),
                "rule_evaluation": rule_result,
            }

    updated = repo.update_user_autonomy_policy(request.user_id, patch)
    repo.audit("control_center.policy.update", request.user_id, updated)
    return {"success": True, "status": "updated", "policy": updated}
