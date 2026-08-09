from __future__ import annotations

from datetime import date
from typing import Any

from app.repository import CompassRepository
from app.services.assessment import AssessmentAdapter
from app.services.economic_manager import EconomicManagerAdapter
from app.services.mail_manager import MailManagerAdapter
from app.services.rules_engine import RulesEngineAdapter
from app.services.self_management import SelfManagementAdapter
from app.services.self_trainer import SelfTrainerAdapter
from app.services.task_commander import TaskCommanderAdapter
from app.services.administrative import AdministrativeAdapter


class ContextService:
    def __init__(self) -> None:
        self.repo = CompassRepository()
        self.self_management = SelfManagementAdapter()
        self.self_trainer = SelfTrainerAdapter()
        self.assessment = AssessmentAdapter()
        self.rules = RulesEngineAdapter()
        self.mail = MailManagerAdapter()
        self.economic_manager = EconomicManagerAdapter()
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
        if not include or "self_management" in include or "self_manage" in include:
            self_management = {
                "today": self.self_management.get_today(),
                "hourly_reminder": self.self_management.get_hourly_reminder(),
            }

        training = {}
        if not include or "training" in include or "self_trainer" in include:
            training = {
                "context": self.self_trainer.context(user_id=user_id),
                "progress": self.self_trainer.progress(user_id=user_id),
            }

        assessment = {}
        if not include or "assessment" in include:
            assessment = {
                "recent": self.assessment.list_recent(),
                "objective_results": self.assessment.list_objective_results(),
            }

        mail = {}
        if not include or "mail" in include or "mail_manager" in include:
            mail = {
                "health": self.mail.health(),
                "financial_items": self.mail.financial_items(limit=10),
                "daily_report": self.mail.daily_report(str(target_date)),
            }

        economic_manager = {}
        if not include or "economic_manager" in include:
            economic_manager = {
                "health": self.economic_manager.health(),
                "summary": self.economic_manager.summary(household_id=f"{user_id}_household"),
            }

        task_commander = {}
        if not include or "task_commander" in include:
            health = self.task_commander.health()
            task_commander = {"health": health}
            if health.get("connected"):
                task_commander.update(
                    {
                        "status": self.task_commander.status(limit=10),
                        "today": self.task_commander.today(limit=10),
                        "overdue": self.task_commander.overdue(limit=10),
                    }
                )

        administrative = {}
        if not include or "administrative" in include:
            health = self.administrative.health()
            administrative = {"health": health}
            if health.get("connected"):
                administrative.update(
                    {
                        "obligations": self.administrative.obligations(user_id=user_id),
                        "cases": self.administrative.cases(user_id=user_id),
                    }
                )

        rules_backbone = {}
        if not include or "rules_engine" in include or "rules" in include:
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

        for section in (
            self_management,
            training,
            assessment,
            mail,
            economic_manager,
            task_commander,
            administrative,
        ):
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
            "training": training,
            "assessment": assessment,
            "mail": mail,
            "economic_manager": economic_manager,
            "task_commander": task_commander,
            "administrative": administrative,
            "rules_backbone": rules_backbone,
            "warnings": warnings,
            "suggested_focus": suggested_focus,
        }
