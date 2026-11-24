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
from app.services.unified_v6_service import UnifiedV6Service

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


class CreateCatalogRuleRequest(BaseModel):
    user_id: str = "moshe"
    rule_id: str
    name: str
    domain: str = "custom"
    event_type: str = "daily_plan.evaluate"
    field: str = "payload.energy_level"
    operator: str = "lte"
    value: Any = 2
    effect_type: str = "recommendation_only"
    reason_code: str = "CUSTOM_RULE_MATCHED"
    priority: int = Field(default=75, ge=1, le=200)
    approval_required: bool = False
    explanation_template: str | None = None


class UIAddFrogRequest(BaseModel):
    user_id: str = "moshe"
    name: str
    domain: str = "physical"
    frog_type: str = "one_time"
    importance: int = 8
    resistance_level: int = 7
    urgency: int = 6
    estimated_minutes: int = 20


class UIAddRoutineRequest(BaseModel):
    user_id: str = "moshe"
    name: str
    domain: str = "physical"
    minimum_viable_version: str = "2 דקות גרסה מינימלית"
    estimated_minutes: int = 15
    trigger_time_or_event: str = "08:00"


class UIUpdatePrepRequest(BaseModel):
    user_id: str = "moshe"
    breathing_seconds: int = 45
    pleasant_starter_action: str = "לגימת מים או מתיחה נעימה"
    pleasant_starter_max_seconds: int = 45


class UIUpdateDomainRequest(BaseModel):
    user_id: str = "moshe"
    slug: str
    long_term_goal: str | None = None
    current_level: int | None = None
    desired_level: int | None = None
    intervention_level: str | None = None


class UIAddChallengeRequest(BaseModel):
    user_id: str = "moshe"
    domain_slug: str = "physical"
    challenge_type: str = "physical"
    title: str
    difficulty_level: int = 3
    max_approved_difficulty: int = 5
    duration_days: int = 14


class UIEvaluateChallengeRequest(BaseModel):
    user_id: str = "moshe"
    outcome: str = "completed"
    pain_or_limitation: bool = False
    perceived_effort: int = 5
    resistance_level: int = 4
    requested_difficulty_delta: int = 0


class UIRecordMentalEventRequest(BaseModel):
    user_id: str = "moshe"
    short_description: str
    trigger_text: str = "אירוע יומיומי"
    actual_response: str = "עצירה ובחירה מודעת"
    is_silent_win: bool = False
    initial_emotion_intensity: int | None = None
    defensive_or_attack_urge: int | None = None
    curiosity_ability: int | None = None
    choice_ability: int | None = None
    recovery_duration_minutes: int | None = None


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
    v6_svc = UnifiedV6Service()
    v6_today = v6_svc.get_today_screen(user_id=user_id)
    v6_messages = v6_svc.list_scheduled_messages(user_id=user_id)
    v6_media = v6_svc.list_media_assets(user_id=user_id)
    v6_inbox = v6_svc.list_inbox_items(user_id=user_id)
    v6_onboarding = v6_svc.get_next_onboarding_question(user_id=user_id)
    v6_intent = v6_svc.get_morning_intent(user_id=user_id)
    v6_energy = v6_svc.get_energy_4d_summary(user_id=user_id)
    v6_learning = v6_svc.analyze_anti_drift_and_recommendations(user_id=user_id)

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
        "v6_today_screen": v6_today,
        "v6_scheduled_messages": v6_messages,
        "v6_media_assets": v6_media,
        "v6_inbox": v6_inbox,
        "v6_onboarding": v6_onboarding,
        "v6_morning_intent": v6_intent,
        "v6_energy_4d": v6_energy,
        "v6_learning": v6_learning,
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


@router.post("/rules", operation_id="createCatalogRule")
def create_catalog_rule(request: CreateCatalogRuleRequest) -> dict[str, Any]:
    repo = CompassRepository()
    policy = repo.get_user_autonomy_policy(request.user_id)
    if policy["active_role"] == "executor":
        raise HTTPException(status_code=403, detail="planner-role-required-to-create-rules")

    now = datetime.now(timezone.utc).isoformat()
    snapshot = {
        "rule_id": request.rule_id.strip().upper(),
        "name": request.name.strip(),
        "description": request.name.strip(),
        "category": "policy",
        "domain": request.domain.strip(),
        "trigger": request.event_type.strip(),
        "priority": request.priority,
        "version": 1,
        "status": "active",
        "enabled": True,
        "stop_processing": False,
        "approval_required": request.approval_required or (request.effect_type == "require_approval"),
        "explanation_template": request.explanation_template
        or f"הכלל {request.rule_id.strip().upper()} ({request.name.strip()}) הופעל בעקבות {request.event_type}.",
        "owner": request.user_id,
        "updated_at": now,
        "event_types": [request.event_type.strip()],
        "conditions": [
            {
                "field": request.field.strip(),
                "operator": request.operator.strip(),
                "value": request.value,
            }
        ],
        "effects": [
            {
                "effect_type": request.effect_type.strip(),
                "reason_code": request.reason_code.strip(),
                "parameters": {},
            }
        ],
    }
    saved = repo.save_rule_override(
        rule_id=snapshot["rule_id"],
        snapshot=snapshot,
        updated_by=request.user_id,
        change_note="Created custom rule via System Control Center",
    )
    repo.audit("control_center.rule.create", request.user_id, {"rule_id": snapshot["rule_id"]})
    return {"success": True, "rule": saved}


@router.post("/frogs", operation_id="createFrogFromControlCenter")
def create_frog_from_control_center(request: UIAddFrogRequest) -> dict[str, Any]:
    return FrogsService().create_frog(request.model_dump())


@router.post("/frogs/{frog_id}/report", operation_id="reportFrogFromControlCenter")
def report_frog_from_control_center(frog_id: str, outcome: str = "completed", user_id: str = "moshe") -> dict[str, Any]:
    return FrogsService().report_frog_execution(frog_id, user_id=user_id, outcome=outcome)


@router.post("/routines", operation_id="createRoutineFromControlCenter")
def create_routine_from_control_center(request: UIAddRoutineRequest) -> dict[str, Any]:
    return RoutinesAndExecutionService().create_routine(request.model_dump())


@router.post("/routines/{routine_id}/report", operation_id="reportRoutineFromControlCenter")
def report_routine_from_control_center(routine_id: str, outcome: str = "completed", user_id: str = "moshe") -> dict[str, Any]:
    return RoutinesAndExecutionService().report_routine_execution(
        routine_id,
        user_id=user_id,
        outcome=outcome,
        used_minimum_version=(outcome == "minimum_completed"),
    )


@router.patch("/prep-protocol", operation_id="updatePrepProtocolFromControlCenter")
def update_prep_from_control_center(request: UIUpdatePrepRequest) -> dict[str, Any]:
    patch = request.model_dump(exclude={"user_id"})
    return {"success": True, "protocol": RoutinesAndExecutionService().update_prep_protocol(request.user_id, patch)}


@router.post("/domains", operation_id="updateDomainFromControlCenter")
def update_domain_from_control_center(request: UIUpdateDomainRequest) -> dict[str, Any]:
    return GrowthChallengesAndPlayService().upsert_domain(request.model_dump(exclude_none=True))


@router.post("/challenges", operation_id="createChallengeFromControlCenter")
def create_challenge_from_control_center(request: UIAddChallengeRequest) -> dict[str, Any]:
    return GrowthChallengesAndPlayService().create_challenge(request.model_dump())


@router.post("/challenges/{challenge_id}/evaluate", operation_id="evaluateChallengeFromControlCenter")
def evaluate_challenge_from_control_center(challenge_id: str, request: UIEvaluateChallengeRequest) -> dict[str, Any]:
    return GrowthChallengesAndPlayService().evaluate_and_adapt_challenge(
        challenge_id,
        user_id=request.user_id,
        outcome=request.outcome,
        pain_or_limitation=request.pain_or_limitation,
        perceived_effort=request.perceived_effort,
        resistance_level=request.resistance_level,
        requested_difficulty_delta=request.requested_difficulty_delta,
    )


@router.post("/mental-events", operation_id="recordMentalEventFromControlCenter")
def record_mental_event_from_control_center(request: UIRecordMentalEventRequest) -> dict[str, Any]:
    return MentalSkillsService().record_mental_event(request.model_dump(exclude_none=True))


@router.post("/approvals/{approval_id}/decide", operation_id="decideApprovalFromControlCenter")
def decide_approval_from_control_center(approval_id: str, decision: str = "approved", user_id: str = "moshe") -> dict[str, Any]:
    repo = CompassRepository()
    item = repo.decide_approval_request(approval_id, status=decision, decision_by=user_id, decision_notes="Decided via Control Center")
    if not item:
        raise HTTPException(status_code=404, detail="approval-not-found")
    if decision == "approved" and item.get("action_type") in {"policy.update", "monthly_policy.update"}:
        proposed = item.get("proposed_action") or {}
        if isinstance(proposed, dict) and proposed:
            repo.update_user_autonomy_policy(user_id, proposed)
    return {"success": True, "approval": item}

