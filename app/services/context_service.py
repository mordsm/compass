from __future__ import annotations

from datetime import date
from typing import Any

from app.repository import CompassRepository
from app.services.assessment import AssessmentAdapter
from app.services.economic_spending import EconomicSpendingAdapter
from app.services.mail_manager import MailManagerAdapter
from app.services.rules_engine import RulesEngineAdapter
from app.services.self_management import SelfManagementAdapter
from app.services.task_commander import TaskCommanderAdapter
from app.services.administrative import AdministrativeAdapter


class ContextService:
    def __init__(self) -> None:
        self.repo = CompassRepository()
        self.self_management = SelfManagementAdapter()
        self.assessment = AssessmentAdapter()
        self.rules = RulesEngineAdapter()
        self.mail = MailManagerAdapter()
        self.economic_spending = EconomicSpendingAdapter()
        self.task_commander = TaskCommanderAdapter()
        self.administrative = AdministrativeAdapter()

    def morning_context(
        self,
        user_id: str,
        target_date: date,
        timezone: str,
        include: list[str],
    ) -> dict[str, Any]:
        warnings: list[str] = []
        open_tasks = self.repo.list_open_tasks(user_id=user_id)
        recent_events = self.repo.list_recent_events(user_id=user_id)
        recent_daily_plans = self.repo.list_recent_daily_plans(user_id=user_id)

        self_management = {}
        if not include or "self_management" in include:
            self_management = {
                "today": self.self_management.get_today(),
                "hourly_reminder": self.self_management.get_hourly_reminder(),
            }

        assessment = {}
        if not include or "assessment" in include:
            assessment = {
                "recent": self.assessment.list_recent(),
                "objective_results": self.assessment.list_objective_results(),
            }

        mail = {}
        if "mail" in include:
            mail = {
                "health": self.mail.health(),
                "financial_items": self.mail.financial_items(limit=10),
                "daily_report": self.mail.daily_report(str(target_date)),
            }

        economic_spending = {}
        if not include or "economic_spending" in include:
            economic_spending = {
                "health": self.economic_spending.health(),
                "summary": self.economic_spending.summary(user_id=user_id),
            }

        task_commander = {}
        if not include or "task_commander" in include:
            task_commander = {
                "health": self.task_commander.health(),
                "status": self.task_commander.status(limit=10),
                "today": self.task_commander.today(limit=10),
                "overdue": self.task_commander.overdue(limit=10),
            }

        administrative = {}
        if not include or "administrative" in include:
            administrative = {
                "health": self.administrative.health(),
                "obligations": self.administrative.obligations(user_id=user_id),
                "cases": self.administrative.cases(user_id=user_id),
            }

        rule_context = {
            "event_type": "morning_context_loaded",
            "user_id": user_id,
            "date": str(target_date),
            "open_task_count": len(open_tasks),
            "recent_event_count": len(recent_events),
            "recent_daily_plan_count": len(recent_daily_plans),
        }
        rules_backbone = self.rules.evaluate(rule_context, actor=user_id)
        if warning := rules_backbone.get("warning"):
            warnings.append(warning)

        for section in (self_management, assessment, mail, economic_spending, task_commander, administrative):
            for value in section.values():
                if isinstance(value, dict) and value.get("warning"):
                    warnings.append(value["warning"])

        suggested_focus = [task["title"] for task in open_tasks[:3]]
        return {
            "success": True,
            "user_id": user_id,
            "date": target_date,
            "timezone": timezone,
            "calendar": [],
            "open_tasks": open_tasks,
            "overdue_tasks": [],
            "recent_events": recent_events,
            "recent_daily_plans": recent_daily_plans,
            "self_management": self_management,
            "assessment": assessment,
            "mail": mail,
            "economic_spending": economic_spending,
            "task_commander": task_commander,
            "administrative": administrative,
            "rules_backbone": rules_backbone,
            "warnings": warnings,
            "suggested_focus": suggested_focus,
        }
