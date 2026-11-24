from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.auth import require_actions_key
from app.repository import CompassRepository
from app.schemas.agents import InvokeAgentRequest
from app.services.accountability_coach import AccountabilityCoachAdapter
from app.services.assessment import AssessmentAdapter
from app.services.economic_manager import EconomicManagerAdapter
from app.services.mail_manager import MailManagerAdapter
from app.services.rules_engine import RulesEngineAdapter
from app.services.self_management import SelfManagementAdapter
from app.services.self_trainer import SelfTrainerAdapter
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
    if request.agent_id == "self_trainer":
        trainer = SelfTrainerAdapter()
        if request.task == "save_session":
            return trainer.save_session({**request.context, "user_id": request.user_id})
        if request.task == "search_history":
            return trainer.search_history({**request.context, "user_id": request.user_id})
        return {
            "connected": True,
            "result": {
                "context": trainer.context(user_id=request.user_id),
                "progress": trainer.progress(
                    user_id=request.user_id,
                    period=str(request.context.get("period", "last_30_days")),
                ),
            },
        }
    if request.agent_id == "assessment":
        assessment = AssessmentAdapter()
        payload = {
            "task": request.task,
            "user_id": request.user_id,
            "context": request.context,
            "expected_output": request.expected_output,
            "risk_level": request.risk_level,
        }
        result = assessment.invoke_agent(payload)
        if result.get("connected"):
            return result
        return {
            "connected": True,
            "warning": result.get("warning", "assessment agent endpoint unavailable; using raw assessment context"),
            "result": {
                "recent": assessment.list_recent(),
                "objective_results": assessment.list_objective_results(),
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
    if request.agent_id == "economic_manager":
        if request.task == "sync_mail_financial_items":
            mail = MailManagerAdapter()
            economic = EconomicManagerAdapter()
            if request.context.get("ingest_mail"):
                mail.ingest(
                    query=request.context.get("mail_query"),
                    max_results=request.context.get("mail_max_results"),
                )
            financial_items = mail.financial_items(
                limit=int(request.context.get("limit", 50)),
                status=request.context.get("status"),
            )
            items = financial_items.get("items") or financial_items.get("result", {}).get("items", [])
            result = economic.import_financial_items(
                {
                    "household_id": request.context.get("household_id", f"{request.user_id}_household"),
                    "user_id": request.user_id,
                    "items": items,
                    "source": "email",
                    "default_category": request.context.get("default_category", "bills"),
                }
            )
            CompassRepository().audit(
                "agents.invoke.economic_manager.sync_mail_financial_items",
                request.user_id,
                {
                    "connected": True,
                    "items_seen": len(items),
                    "created": result.get("created"),
                    "duplicates": result.get("duplicates"),
                },
            )
            return {
                "connected": True,
                "mail_financial_items": financial_items,
                "result": result,
            }
        result = EconomicManagerAdapter().invoke_agent(
            {
                "task": request.task,
                "user_id": request.user_id,
                "context": request.context,
                "expected_output": request.expected_output,
                "risk_level": request.risk_level,
            }
        )
        CompassRepository().audit(
            "agents.invoke.economic_manager",
            request.user_id,
            {
                "requested_agent_id": request.agent_id,
                "task": request.task,
                "connected": bool(result.get("connected")),
            },
        )
        return result
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
        if request.task == "open_case":
            return administrative.open_case({**request.context, "user_id": request.user_id})
        if request.task == "add_case_event":
            return administrative.add_case_event(str(request.context["case_id"]), request.context.get("event", {}))
        if request.task == "add_case_document":
            return administrative.add_case_document(str(request.context["case_id"]), request.context.get("document", {}))
        if request.task == "add_case_checklist_item":
            return administrative.add_case_checklist_item(str(request.context["case_id"]), request.context.get("item", {}))
        if request.task == "draft_case_communication":
            return administrative.draft_case_communication(str(request.context["case_id"]), request.context.get("draft", {}))
        return {
            "connected": True,
            "result": {
                "health": administrative.health(),
                "obligations": administrative.obligations(user_id=request.user_id),
                "cases": administrative.cases(user_id=request.user_id),
            },
        }
    if request.agent_id == "accountability_coach":
        coach = AccountabilityCoachAdapter()
        if request.task in ("morning_briefing", "morning"):
            return coach.morning_briefing(user_id=request.user_id, context=request.context)
        if request.task in ("mark_item_done", "done"):
            return coach.mark_item_done(user_id=request.user_id, context=request.context)
        if request.task in ("intraday_check", "checkin", "intraday"):
            return coach.intraday_check(user_id=request.user_id, context=request.context)
        if request.task in ("evening_debrief", "evening"):
            return coach.evening_debrief(user_id=request.user_id, context=request.context)
        return coach.morning_briefing(user_id=request.user_id, context=request.context)
    raise HTTPException(status_code=400, detail="unknown-agent")
