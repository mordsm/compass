from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.auth import require_actions_key
from app.repository import CompassRepository
from app.schemas.agents import InvokeAgentRequest
from app.services.assessment import AssessmentAdapter
from app.services.economic_spending import EconomicSpendingAdapter
from app.services.mail_manager import MailManagerAdapter
from app.services.rules_engine import RulesEngineAdapter
from app.services.self_management import SelfManagementAdapter
from app.services.task_commander import TaskCommanderAdapter
from app.services.administrative import AdministrativeAdapter

router = APIRouter(prefix="/api/agents", tags=["agents"], dependencies=[Depends(require_actions_key)])


@router.post("/invoke", operation_id="invokeAgent")
def invoke_agent(request: InvokeAgentRequest) -> dict:
    if request.require_approval:
        result = CompassRepository().create_approval_request(
            {
                "user_id": request.user_id,
                "title": f"Approve {request.agent_id}: {request.task}",
                "description": request.expected_output,
                "requested_by": request.agent_id,
                "action_type": f"agent.{request.agent_id}.{request.task}",
                "risk_level": request.risk_level,
                "proposed_action": {
                    "agent_id": request.agent_id,
                    "task": request.task,
                    "context": request.context,
                    "expected_output": request.expected_output,
                },
                "rule_result": {},
            }
        )
        CompassRepository().audit("agents.propose", request.user_id, result)
        return {
            "connected": True,
            "status": "approval_required",
            "approval_request_id": result["resource_id"],
            "result": result,
        }

    if request.agent_id == "rules_engine":
        context = {**request.context, "task": request.task, "user_id": request.user_id}
        return RulesEngineAdapter().evaluate(context=context, actor=request.user_id)
    if request.agent_id == "self_manage":
        return {
            "connected": True,
            "result": {
                "today": SelfManagementAdapter().get_today(),
                "hourly_reminder": SelfManagementAdapter().get_hourly_reminder(),
            },
        }
    if request.agent_id == "assessment":
        return {
            "connected": True,
            "result": {
                "recent": AssessmentAdapter().list_recent(),
                "objective_results": AssessmentAdapter().list_objective_results(),
            },
        }
    if request.agent_id == "mail_manager":
        mail = MailManagerAdapter()
        return {
            "connected": True,
            "result": {
                "health": mail.health(),
                "recent_emails": mail.recent_emails(limit=10),
                "financial_items": mail.financial_items(limit=20),
            },
        }
    if request.agent_id == "economic_spending":
        economic = EconomicSpendingAdapter()
        payload = {**request.context, "user_id": request.user_id, "task": request.task}
        if request.task == "record_event":
            return economic.record_event(payload)
        return economic.summary(user_id=request.user_id)
    if request.agent_id == "task_commander":
        task_commander = TaskCommanderAdapter()
        if request.task == "create_task":
            return task_commander.create_task({**request.context, "source": "compass"})
        if request.task == "generate_instances":
            return task_commander.generate_instances(days=int(request.context.get("days", 2)))
        if request.task == "mark_done":
            return task_commander.mark_done(str(request.context["instance_id"]))
        if request.task == "snooze":
            return task_commander.snooze(
                str(request.context["instance_id"]),
                int(request.context.get("minutes", 60)),
            )
        if request.task == "skip":
            return task_commander.skip(str(request.context["instance_id"]))
        return {
            "connected": True,
            "result": {
                "health": task_commander.health(),
                "status": task_commander.status(limit=10),
                "today": task_commander.today(limit=20),
                "overdue": task_commander.overdue(limit=20),
            },
        }
    if request.agent_id == "administrative":
        administrative = AdministrativeAdapter()
        if request.task == "record_obligation":
            return administrative.record_obligation({**request.context, "user_id": request.user_id})
        return {
            "connected": True,
            "result": {
                "health": administrative.health(),
                "obligations": administrative.obligations(user_id=request.user_id),
                "cases": administrative.cases(user_id=request.user_id),
            },
        }
    raise HTTPException(status_code=400, detail="unknown-agent")
