from __future__ import annotations

from typing import Any

from app.repository import CompassRepository
from app.services.assessment import AssessmentAdapter
from app.services.mail_manager import MailManagerAdapter
from app.services.rules_engine import RulesEngineAdapter
from app.services.self_management import SelfManagementAdapter
from app.services.self_trainer import SelfTrainerAdapter
from app.services.task_commander import TaskCommanderAdapter


class AccountabilityCoachAdapter:
    """
    Accountability & Momentum Coach Adapter (Hermes / Telegram Integration).
    Tracks specific named exercises (E1..E6 from `self_manage`) and specific named tasks
    (`T1..Tn` from `task_commander` / `sharons`), logs item-level completions, and enforces
    proactive outreach (including the 10:00 AM no-execution check and 2-day postponement Red Alert).
    """

    REQUIRED_DAILY_EXERCISES = 6
    RED_ALERT_POSTPONEMENT_DAYS = 2

    def _fetch_structured_exercises(self) -> list[dict[str, Any]]:
        sm = SelfManagementAdapter()
        today_data = sm.get_today()
        items = today_data.get("items") or today_data.get("result", {}).get("items", [])
        if not items:
            generated = sm.generate_today(overwrite=False)
            items = generated.get("items") or generated.get("result", {}).get("items", [])

        structured: list[dict[str, Any]] = []
        for idx, item in enumerate(items[: self.REQUIRED_DAILY_EXERCISES], start=1):
            ex = item.get("exercise", {}) if isinstance(item, dict) else {}
            dom = item.get("domain", {}) if isinstance(item, dict) else {}
            structured.append(
                {
                    "code": f"E{idx}",
                    "order": idx,
                    "plan_item_id": item.get("plan_item_id"),
                    "exercise_id": ex.get("id"),
                    "slug": ex.get("slug", f"exercise_{idx}"),
                    "label": ex.get("label") or ex.get("slug") or f"תרגיל {idx}",
                    "domain": dom.get("label") or dom.get("slug") or "כללי",
                    "minutes": int(ex.get("minutes_default") or 10),
                    "status": item.get("status", "pending"),
                }
            )
        return structured

    def _fetch_structured_tasks(self, sharons_tasks: list[Any] | None = None) -> list[dict[str, Any]]:
        tc = TaskCommanderAdapter()
        today_resp = tc.today(limit=15)
        overdue_resp = tc.overdue(limit=10)

        raw_tasks: list[dict[str, Any]] = []
        for item in sharons_tasks or []:
            if isinstance(item, dict):
                raw_tasks.append(
                    {
                        "instance_id": item.get("id"),
                        "title": item.get("title", "משימת Sharons"),
                        "source": "sharons",
                        "status": item.get("status", "pending"),
                    }
                )
            else:
                raw_tasks.append({"instance_id": None, "title": str(item), "source": "sharons", "status": "pending"})

        for bucket, is_overdue in ((overdue_resp, True), (today_resp, False)):
            items = bucket.get("items") or bucket.get("tasks") or bucket.get("result", {}).get("items", [])
            if isinstance(items, list):
                for t in items:
                    if isinstance(t, dict):
                        raw_tasks.append(
                            {
                                "instance_id": t.get("id") or t.get("instance_id"),
                                "title": t.get("title", "משימה יומית"),
                                "source": "task_commander_overdue" if is_overdue else "task_commander",
                                "status": t.get("status", "pending"),
                            }
                        )

        structured: list[dict[str, Any]] = []
        for idx, t in enumerate(raw_tasks[:10], start=1):
            structured.append(
                {
                    "code": f"T{idx}",
                    "instance_id": t["instance_id"],
                    "title": t["title"],
                    "source": t["source"],
                    "status": t["status"],
                }
            )
        return structured

    def morning_briefing(self, user_id: str = "moshe", context: dict[str, Any] | None = None) -> dict[str, Any]:
        ctx = context or {}
        exercises = self._fetch_structured_exercises()
        tasks = self._fetch_structured_tasks(ctx.get("sharons_tasks"))
        recent_emails = MailManagerAdapter().recent_emails(limit=10)
        calendar_events = ctx.get("calendar_events", [])
        anchor_priority = ctx.get("anchor_priority") or (
            tasks[0]["title"] if tasks else "השלמת 6 תרגילי החובה היומיים + משימת הליבה ב-Sharons"
        )

        rule_eval = RulesEngineAdapter().evaluate(
            context={
                "phase": "morning_briefing",
                "user_id": user_id,
                "required_exercises": self.REQUIRED_DAILY_EXERCISES,
                "exercises_loaded": len(exercises),
                "tasks_loaded": len(tasks),
                "calendar_events_count": len(calendar_events),
                "anchor_priority": anchor_priority,
            },
            actor=user_id,
        )

        result = {
            "phase": "MORNING_BRIEFING_AUDIT",
            "user_id": user_id,
            "anchor_priority": anchor_priority,
            "exercises": exercises,
            "tasks": tasks,
            "calendar_events": calendar_events,
            "urgent_emails_24h": recent_emails,
            "rules_evaluation": rule_eval,
            "requires_telegram_ack": True,
        }
        CompassRepository().audit(
            "agents.accountability_coach.morning_briefing",
            user_id,
            {"anchor_priority": anchor_priority, "exercises_count": len(exercises), "tasks_count": len(tasks)},
        )
        return {"connected": True, "result": result}

    def mark_item_done(self, user_id: str = "moshe", context: dict[str, Any] | None = None) -> dict[str, Any]:
        """
        Marks a specific exercise (e.g. E1 / plan_item_id / name) or task (e.g. T1 / instance_id / name)
        as completed in the underlying agent (`self_manage` or `task_commander`).
        """
        ctx = context or {}
        plan_item_id = ctx.get("plan_item_id")
        instance_id = ctx.get("instance_id")
        minutes = int(ctx.get("minutes", 10))
        notes = ctx.get("notes")

        backend_result: dict[str, Any] = {}
        if plan_item_id is not None:
            backend_result = SelfManagementAdapter().log_session(
                plan_item_id=plan_item_id,
                completed=True,
                minutes=minutes,
                notes=notes,
            )
        elif instance_id is not None:
            backend_result = TaskCommanderAdapter().mark_done(str(instance_id))

        CompassRepository().audit(
            "agents.accountability_coach.mark_item_done",
            user_id,
            {"plan_item_id": plan_item_id, "instance_id": instance_id, "notes": notes},
        )
        return {"connected": True, "result": backend_result}

    def intraday_check(self, user_id: str = "moshe", context: dict[str, Any] | None = None) -> dict[str, Any]:
        ctx = context or {}
        exercises = self._fetch_structured_exercises()
        tasks = self._fetch_structured_tasks(ctx.get("sharons_tasks"))
        completed_codes = set(ctx.get("completed_codes", []))

        completed_exercises = [
            e for e in exercises if e["status"] == "completed" or e["code"] in completed_codes
        ]
        pending_exercises = [
            e for e in exercises if e["status"] != "completed" and e["code"] not in completed_codes
        ]
        stalling_detected = bool(ctx.get("stalling_detected", False) or len(completed_exercises) == 0)

        first_pending = pending_exercises[0] if pending_exercises else {"code": "E1", "label": "תרגיל תנועה/נשימה"}
        intervention = None
        if stalling_detected:
            intervention = (
                f"FRICTION_INTERVENTION: עזוב הכל עכשיו ובצע 10 דקות של "
                f"{first_pending['code']} ({first_pending['label']}) כדי לשבור את החיכוך ולהחזיר מומנטום!"
            )

        result = {
            "phase": "INTRADAY_EXECUTION_CHECK",
            "user_id": user_id,
            "completed_exercises": completed_exercises,
            "pending_exercises": pending_exercises,
            "tasks": tasks,
            "stalling_detected": stalling_detected,
            "minimum_viable_engagement": intervention,
        }
        CompassRepository().audit(
            "agents.accountability_coach.intraday_check",
            user_id,
            {"completed_count": len(completed_exercises), "stalling_detected": stalling_detected},
        )
        return {"connected": True, "result": result}

    def evening_debrief(self, user_id: str = "moshe", context: dict[str, Any] | None = None) -> dict[str, Any]:
        ctx = context or {}
        exercises = self._fetch_structured_exercises()
        tasks = self._fetch_structured_tasks(ctx.get("sharons_tasks"))
        completed_codes = set(ctx.get("completed_codes", []))
        postponed_items: list[dict[str, Any]] = ctx.get("postponed_items", [])
        tomorrow_tasks: list[str] = ctx.get("tomorrow_committed_tasks", [])

        completed_exercises = [
            e for e in exercises if e["status"] == "completed" or e["code"] in completed_codes
        ]
        missed_exercises = [
            e for e in exercises if e["status"] != "completed" and e["code"] not in completed_codes
        ]

        red_alerts = [
            item
            for item in postponed_items
            if int(item.get("consecutive_postponed_days", 0)) >= self.RED_ALERT_POSTPONEMENT_DAYS
        ]
        red_alert_triggered = len(red_alerts) > 0
        all_exercises_done = len(completed_exercises) >= self.REQUIRED_DAILY_EXERCISES and len(missed_exercises) == 0

        rule_eval = RulesEngineAdapter().evaluate(
            context={
                "phase": "evening_debrief",
                "user_id": user_id,
                "exercises_completed": len(completed_exercises),
                "missed_exercises": [e["label"] for e in missed_exercises],
                "red_alert_triggered": red_alert_triggered,
                "red_alert_items": red_alerts,
            },
            actor=user_id,
        )

        trainer_log = None
        if completed_exercises:
            trainer_log = SelfTrainerAdapter().save_session(
                {
                    "user_id": user_id,
                    "source": "accountability_coach",
                    "exercises_completed": len(completed_exercises),
                    "completed_labels": [e["label"] for e in completed_exercises],
                    "target_exercises": self.REQUIRED_DAILY_EXERCISES,
                    "all_completed": all_exercises_done,
                }
            )

        assessment_report = AssessmentAdapter().invoke_agent(
            {
                "task": "record_daily_accountability",
                "user_id": user_id,
                "context": {
                    "exercises_completed": len(completed_exercises),
                    "completed_labels": [e["label"] for e in completed_exercises],
                    "missed_labels": [e["label"] for e in missed_exercises],
                    "required_exercises": self.REQUIRED_DAILY_EXERCISES,
                    "red_alert_triggered": red_alert_triggered,
                    "red_alerts": red_alerts,
                },
                "expected_output": "updated_streak_and_fatigue_metrics",
                "risk_level": "high" if red_alert_triggered else "low",
            }
        )

        result = {
            "phase": "EVENING_DEBRIEF_AND_PRE_MORTEM",
            "user_id": user_id,
            "completed_exercises": completed_exercises,
            "missed_exercises": missed_exercises,
            "tasks": tasks,
            "red_alert_triggered": red_alert_triggered,
            "red_alerts": red_alerts,
            "rules_evaluation": rule_eval,
            "self_trainer_log": trainer_log,
            "assessment_sync": assessment_report,
            "tomorrow_committed_tasks": tomorrow_tasks,
            "tomorrow_locked": len(tomorrow_tasks) > 0,
        }
        CompassRepository().audit(
            "agents.accountability_coach.evening_debrief",
            user_id,
            {
                "exercises_completed": len(completed_exercises),
                "red_alert_triggered": red_alert_triggered,
                "tomorrow_locked": len(tomorrow_tasks) > 0,
            },
        )
        return {"connected": True, "result": result}
