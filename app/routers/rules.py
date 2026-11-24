from __future__ import annotations

from fastapi import APIRouter, Depends

from app.auth import require_actions_key
from app.repository import CompassRepository
from app.schemas.rules import (
    AssessmentFindingWorkflowRequest,
    AssessmentFindingWorkflowResponse,
    RuleEvaluationResponse,
    RulesEventRequest,
    StructuredRulesEventRequest,
)
from app.services.rules_engine import RulesEngineAdapter
from app.services.self_management import SelfManagementAdapter

router = APIRouter(prefix="/api/rules", tags=["rules"], dependencies=[Depends(require_actions_key)])


NON_CARDIO_PHYSICAL_DOMAINS = [
    "balance_coordination",
    "core_posture",
    "mobility",
    "qigong",
    "recovery",
    "strength",
]

MENTAL_FINDING_TYPES = {
    "mental_skill_gap",
    "self_regulation_gap",
    "functional_resilience_gap",
    "stress_regulation_gap",
    "sense_of_control_gap",
}


def _physical_domains_from_self_manage(response: dict) -> list[str]:
    if not response.get("connected"):
        return []
    domains = response.get("result")
    if not isinstance(domains, list):
        return []
    return [
        str(domain.get("slug")).lower()
        for domain in domains
        if isinstance(domain, dict)
        and domain.get("kind") == "physical"
        and domain.get("slug")
        and domain.get("slug") != "cardio"
    ]


def _assessment_finding_self_manage_profile(
    request: AssessmentFindingWorkflowRequest,
    physical_domains: list[str] | None = None,
) -> dict:
    difficulty = 4 if request.current_state == "low" else 6
    if request.severity in {"high", "critical"}:
        difficulty = min(difficulty, 3)

    if _is_mental_self_manage_request(request):
        profile = {
            "difficulty_level": difficulty,
            "excluded_kinds": ["cognitive", "physical"],
            "excluded_domains": [],
            "required_measurement_terms": [],
            "reading_mode": "steps",
            "language": "he",
        }
        profile.update(request.self_manage_profile)
        return profile

    excluded_domains = sorted(set(physical_domains or NON_CARDIO_PHYSICAL_DOMAINS))

    profile = {
        "difficulty_level": difficulty,
        "excluded_kinds": ["cognitive", "mental"],
        "excluded_domains": excluded_domains,
        "required_measurement_terms": ["rpe"],
        "reading_mode": "steps",
        "language": "he",
    }
    profile.update(request.self_manage_profile)
    return profile


def _is_mental_self_manage_request(request: AssessmentFindingWorkflowRequest) -> bool:
    return (
        request.domain.lower() == "mental"
        or request.finding_type in MENTAL_FINDING_TYPES
        or request.recommended_capability in {"mental_training", "mental_practice", "self_regulation_practice"}
    )


def _self_manage_target(request: AssessmentFindingWorkflowRequest) -> dict:
    if _is_mental_self_manage_request(request):
        return {
            "name": "mental",
            "candidate_kinds": ["mental"],
            "selected_kinds": ["mental"],
            "missing_capability": "mental_self_regulation_exercise",
            "purpose": "create_mental_self_manage_plan",
            "message": "No active mental exercise was found in self_manage.",
            "recommended_next_action": "Add a mental exercise to self_manage, or explicitly approve importing one from a trusted source.",
            "suggested_search_query": "short self regulation mental skills exercise implementation intention reset instructions",
        }
    return {
        "name": "cardio",
        "candidate_kinds": ["physical"],
        "selected_kinds": ["physical"],
        "selected_domain_slug": "cardio",
        "missing_capability": "aerobic_cardio_exercise",
        "purpose": "create_aerobic_cardio_plan",
        "message": "No active aerobic cardio exercise was found in self_manage.",
        "recommended_next_action": "Add a cardio exercise to self_manage, or explicitly approve importing one from a trusted source.",
        "suggested_search_query": "beginner low intensity aerobic exercise RPE walking in place instructions",
    }


def _self_manage_plan_summary(response: dict, self_manage: SelfManagementAdapter, target: dict) -> dict:
    result = response.get("result") if isinstance(response, dict) else None
    if not isinstance(result, dict):
        return {}

    items = result.get("items") if isinstance(result.get("items"), list) else []
    selected_items = [
        item
        for item in items
        if isinstance(item, dict)
        and item.get("kind") in target["selected_kinds"]
        and (
            not target.get("selected_domain_slug")
            or (
                isinstance(item.get("domain"), dict)
                and item["domain"].get("slug") == target["selected_domain_slug"]
            )
        )
    ]
    selected_item = selected_items[0] if selected_items else (items[0] if items else None)
    if not isinstance(selected_item, dict):
        return {
            "plan_id": result.get("plan_id"),
            "plan_date": result.get("plan_date"),
            "items": [],
        }

    plan_item_id = selected_item.get("plan_item_id")
    exercise = selected_item.get("exercise") if isinstance(selected_item.get("exercise"), dict) else {}
    urls = self_manage.ui_urls(plan_item_id)
    return {
        "plan_id": result.get("plan_id"),
        "plan_date": result.get("plan_date"),
        "algorithm_version": result.get("algorithm_version"),
        "selected_plan_item_id": plan_item_id,
        "selected_domain": selected_item.get("domain"),
        "selected_exercise": {
            "id": exercise.get("id"),
            "slug": exercise.get("slug"),
            "label": exercise.get("label"),
            "minutes_default": exercise.get("minutes_default"),
            "notes": exercise.get("notes"),
            "how_to": exercise.get("how_to") or [],
            "measurement": exercise.get("measurement"),
            "common_mistakes": exercise.get("common_mistakes") or [],
            "score": exercise.get("score"),
            "media": exercise.get("media") or [],
        },
        "session_url": urls.get("session"),
        "today_url": urls["today"],
        "items": items,
    }


def _cardio_exercises_from_self_manage(response: dict) -> list[dict]:
    if not response.get("connected"):
        return []
    exercises = response.get("result")
    if not isinstance(exercises, list):
        return []

    matches = []
    for exercise in exercises:
        if not isinstance(exercise, dict):
            continue
        domain = exercise.get("domain") if isinstance(exercise.get("domain"), dict) else {}
        measurement = str(exercise.get("measurement") or "").lower()
        if (
            exercise.get("kind") == "physical"
            and domain.get("slug") == "cardio"
            and exercise.get("is_active", True)
            and "rpe" in measurement
        ):
            matches.append(exercise)
    return matches


def _target_exercises_from_self_manage(response: dict, target: dict) -> list[dict]:
    if target["name"] == "cardio":
        return _cardio_exercises_from_self_manage(response)
    if not response.get("connected"):
        return []
    exercises = response.get("result")
    if not isinstance(exercises, list):
        return []
    return [
        exercise
        for exercise in exercises
        if isinstance(exercise, dict)
        and exercise.get("kind") in target["candidate_kinds"]
        and exercise.get("is_active", True)
    ]


def _missing_content_plan(self_manage: SelfManagementAdapter, target: dict) -> dict:
    urls = self_manage.ui_urls()
    return {
        "content_needed": True,
        "missing_capability": target["missing_capability"],
        "required_criteria": {
            "kind": target["candidate_kinds"],
            "domain": target.get("selected_domain_slug", "any"),
        },
        "message": target["message"],
        "recommended_next_action": target["recommended_next_action"],
        "suggested_search_query": target["suggested_search_query"],
        "today_url": urls["today"],
        "profile_url": urls.get("profile"),
    }


@router.post("/events", operation_id="submitEventToRulesEngine")
def submit_event_to_rules_engine(request: RulesEventRequest) -> dict:
    context = {
        **request.context,
        "event_type": request.event_type,
        "user_id": request.user_id,
        "signals": request.signals,
        "dry_run": request.dry_run,
    }
    return RulesEngineAdapter().evaluate(context=context, actor=request.actor or request.user_id)


@router.post("/evaluate", response_model=RuleEvaluationResponse, operation_id="evaluateStructuredRulesEvent")
def evaluate_structured_rules_event(request: StructuredRulesEventRequest) -> dict:
    repo = CompassRepository()
    if request.idempotency_key and (cached := repo.get_idempotent_response(request.idempotency_key)):
        return cached

    event = request.to_structured_event()
    rules_result = RulesEngineAdapter().evaluate_event(
        event=event,
        actor=request.actor or request.user_id,
        dry_run=request.dry_run,
    )
    if not rules_result.get("connected"):
        result = {
            "evaluation_id": f"eval_unavailable_{request.event_id}",
            "event_id": request.event_id,
            "final_decision": "require_approval",
            "risk_level": "medium",
            "matched_rules": [],
            "reason_codes": ["RULES_ENGINE_UNAVAILABLE"],
            "allowed_actions": [],
            "approval_required_actions": [],
            "blocked_actions": [],
            "routes": [],
            "selected_workflow": None,
            "redactions": [],
            "warnings": [str(rules_result.get("warning") or "rules engine unavailable")],
            "dry_run": request.dry_run,
            "explanation": "rules_engine was unavailable; Compass requires approval by default",
        }
    else:
        result = rules_result.get("result", {})

    repo.save_rule_evaluation(event, result)
    repo.audit("rules.evaluate", request.user_id, {"event": event, "result": result})
    repo.remember_idempotent_response(request.idempotency_key, "rules.evaluate", result)
    return result


@router.post(
    "/workflows/assessment-finding",
    response_model=AssessmentFindingWorkflowResponse,
    operation_id="runAssessmentFindingRulesWorkflow",
)
def run_assessment_finding_rules_workflow(request: AssessmentFindingWorkflowRequest) -> dict:
    repo = CompassRepository()
    workflow_key = f"workflow:{request.idempotency_key}"
    if workflow_key and (cached := repo.get_idempotent_response(workflow_key)):
        return cached

    event_request = StructuredRulesEventRequest(
        event_id=request.event_id,
        event_type="assessment_finding_created",
        event_version="1.0",
        source=request.source,
        user_id=request.user_id,
        occurred_at=request.occurred_at,
        idempotency_key=request.idempotency_key,
        dry_run=request.dry_run,
        payload={
            "domain": request.domain,
            "finding_type": request.finding_type,
            "severity": request.severity,
            "confidence": request.confidence,
            "current_state": request.current_state,
            "evidence": request.evidence,
            "recommended_capability": request.recommended_capability,
        },
    )
    rules_result = evaluate_structured_rules_event(event_request)
    self_manage_route = next(
        (route for route in rules_result.get("routes", []) if route.get("component") == "self_manage"),
        None,
    )
    self_manage_preview = {}
    self_manage_profile = {}
    self_manage_plan = {}
    ui_url = None
    ui_urls: dict[str, str] = {}
    ui_opened = False
    ui_open_method = None
    executed_actions: list[dict] = []
    warnings: list[str] = []
    if self_manage_route:
        self_manage = SelfManagementAdapter()
        domains_result = self_manage.list_domains()
        if isinstance(domains_result, dict) and domains_result.get("warning"):
            warnings.append(str(domains_result["warning"]))
        self_manage_profile = _assessment_finding_self_manage_profile(
            request,
            physical_domains=_physical_domains_from_self_manage(domains_result),
        )
        self_manage_preview = {
            "today": self_manage.get_today(),
            "hourly_reminder": self_manage.get_hourly_reminder(),
        }
        for value in self_manage_preview.values():
            if isinstance(value, dict) and value.get("warning"):
                warnings.append(str(value["warning"]))

    approval_request_id = None
    status = "evaluated"
    if (
        request.auto_create_approval
        and not request.dry_run
        and not request.approval_confirmed
        and rules_result.get("final_decision") == "require_approval"
    ):
        first_action = (rules_result.get("approval_required_actions") or [{}])[0]
        approval = repo.create_approval_request(
            {
                "user_id": request.user_id,
                "title": first_action.get("title") or "Approve assessment-driven self_manage planning",
                "description": "rules_engine requires approval before creating or invoking a fitness plan.",
                "requested_by": "rules_engine",
                "action_type": first_action.get("action_type") or "invoke_component",
                "risk_level": rules_result.get("risk_level", "medium"),
                "proposed_action": {
                    "source_event_id": request.event_id,
                    "route": self_manage_route,
                    "action": first_action,
                },
                "rule_result": rules_result,
            }
        )
        approval_request_id = approval["resource_id"]
        repo.audit("rules.workflow.assessment.approval_created", request.user_id, approval)
        status = "approval_required"
    elif rules_result.get("final_decision") == "block":
        status = "blocked"
    elif request.dry_run:
        status = "dry_run"

    can_execute_self_manage = (
        request.execute_self_manage
        and bool(self_manage_route)
        and not request.dry_run
        and rules_result.get("final_decision") != "block"
        and (rules_result.get("final_decision") != "require_approval" or request.approval_confirmed)
    )
    if request.execute_self_manage and not can_execute_self_manage:
        if not self_manage_route:
            warnings.append("rules_engine did not route this finding to self_manage")
        elif request.dry_run:
            warnings.append("dry_run is true; self_manage execution skipped")
        elif rules_result.get("final_decision") == "block":
            warnings.append("rules_engine blocked the requested self_manage execution")
        elif rules_result.get("final_decision") == "require_approval" and not request.approval_confirmed:
            warnings.append("rules_engine requires approval before creating an aerobic self_manage plan")

    if can_execute_self_manage:
        target = _self_manage_target(request)
        exercises_result = self_manage.list_cardio_candidates() if target["name"] == "cardio" else self_manage.list_exercises()
        if isinstance(exercises_result, dict) and exercises_result.get("warning"):
            warnings.append(str(exercises_result["warning"]))
        available_exercises = _target_exercises_from_self_manage(exercises_result, target)
        if not available_exercises:
            self_manage_plan = _missing_content_plan(self_manage, target)
            ui_url = self_manage_plan.get("today_url")
            ui_urls = self_manage.ui_urls()
            warnings.append(self_manage_plan["message"])
            status = "self_manage_content_needed"
        else:
            generated_plan = self_manage.generate_today(profile=self_manage_profile, overwrite=True)
            self_manage_plan = _self_manage_plan_summary(generated_plan, self_manage, target)
            ui_url = self_manage_plan.get("session_url") or self_manage.ui_urls()["today"]
            ui_urls = self_manage.ui_urls(self_manage_plan.get("selected_plan_item_id"))
            executed_actions.append(
                {
                    "action_type": "self_manage.generate_today",
                    "component": "self_manage",
                    "purpose": target["purpose"],
                    "profile": self_manage_profile,
                    "available_exercise_count": len(available_exercises),
                    "result": generated_plan,
                    "plan": self_manage_plan,
                    "ui_url": ui_url,
                }
            )
            if isinstance(generated_plan, dict) and generated_plan.get("warning"):
                warnings.append(str(generated_plan["warning"]))
                status = "self_manage_unavailable"
            elif not self_manage_plan.get("selected_plan_item_id"):
                warnings.append("self_manage did not return a plan_item_id for the generated exercise")
                status = "self_manage_plan_unverified"
            else:
                status = "self_manage_executed"
                if request.open_ui:
                    opened = self_manage.open_ui(self_manage_plan.get("selected_plan_item_id"))
                    ui_opened = bool(opened.get("opened"))
                    ui_url = opened.get("url") or ui_url
                    ui_urls = opened.get("urls") or ui_urls
                    ui_open_method = opened.get("open_method")
                    if opened.get("warning"):
                        warnings.append(str(opened["warning"]))

    result = {
        "success": True,
        "status": status,
        "rules_result": rules_result,
        "approval_request_id": approval_request_id,
        "self_manage_route": self_manage_route,
        "self_manage_preview": self_manage_preview,
        "self_manage_profile": self_manage_profile,
        "self_manage_plan": self_manage_plan,
        "ui_url": ui_url,
        "ui_urls": ui_urls,
        "ui_opened": ui_opened,
        "ui_open_method": ui_open_method,
        "executed_actions": executed_actions,
        "warnings": warnings,
    }
    repo.audit("rules.workflow.assessment", request.user_id, result)
    repo.remember_idempotent_response(workflow_key, "rules.workflow.assessment", result)
    return result
