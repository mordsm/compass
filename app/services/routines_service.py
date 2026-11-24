from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any
from uuid import uuid4

from app.database import db, json_dump, json_load, resource_id, utc_now
from app.repository import CompassRepository
from app.services.frogs_service import FrogsService
from app.services.rules_engine import RulesEngineAdapter
from app.services.task_commander import TaskCommanderAdapter

DEFAULT_PREP_STEPS: list[dict[str, Any]] = [
    {"step": 1, "title": "עצירה קצרה", "instruction": "עצור לרגע לפני תחילת הפעולה והנח להסחות הדעת."},
    {"step": 2, "title": "זיהוי תחושה גופנית", "instruction": "שים לב היכן בגוף מורגש מתח, כיווץ או אי-נוחות קלה."},
    {"step": 3, "title": "נשימה טבעית ורגועה (30–60 שניות)", "instruction": "נשום באופן טבעי ורגוע במשך 30–60 שניות ללא מאמץ."},
    {"step": 4, "title": "הפניית קשב לפעולה עצמה", "instruction": "הפנה את תשומת הלב לתנועה או לפעולה הראשונה עצמה ולא לתוצאה הסופית."},
    {"step": 5, "title": "התחלת הפעולה בהתאם ליכולת ולבטיחות", "instruction": "התחל בצעד הראשון בקצב שלך ובכפוף למגבלות הבטיחות."},
    {"step": 6, "title": "זיהוי התחושה לאחר הביצוע", "instruction": "בסיום, שים לב לתחושה בגוף ובהכרה לאחר שהפעולה בוצעה."},
]


class RoutinesAndExecutionService:
    """
    Phase 3 Deterministic Engine (Sections 6, 7, 10 of specification):
    1. Pre-Action Resistance Reduction Protocol (6 steps + periodic tension sampling + bounded pleasant starter).
    2. Routines & Habits Management (distinguishing beneficial habit automation from automatic emotional reactivity,
       with automatic minimum viable version `HABIT-001` and penalty-free skipping).
    3. Planner vs. Executor Role Separation & deterministic `next-action` guidance.
    """

    # --- 1. Pre-Action Preparation Protocol (Section 6 & MENTAL-001) ---

    def get_or_create_prep_protocol(self, user_id: str = "moshe") -> dict[str, Any]:
        now = utc_now()
        protocol_id = f"prep_{user_id}"
        with db() as conn:
            row = conn.execute("select * from prep_protocols where user_id = ?", (user_id,)).fetchone()
            if not row:
                conn.execute(
                    """
                    insert into prep_protocols
                    (protocol_id, user_id, name, steps_json, breathing_seconds,
                     pleasant_starter_action, pleasant_starter_max_seconds,
                     sampling_interval, executions_count, updated_at)
                    values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        protocol_id,
                        user_id,
                        "פרוטוקול הכנה קצר להפחתת התנגדות",
                        json_dump(DEFAULT_PREP_STEPS),
                        45,
                        "לגימת מים או מתיחה נעימה של 20 שניות",
                        45,
                        3,
                        0,
                        now,
                    ),
                )
                row = conn.execute("select * from prep_protocols where user_id = ?", (user_id,)).fetchone()
        return self._protocol_row(row)

    def update_prep_protocol(self, user_id: str, patch: dict[str, Any]) -> dict[str, Any]:
        current = self.get_or_create_prep_protocol(user_id)
        now = utc_now()
        breathing_seconds = min(120, max(20, int(patch.get("breathing_seconds", current["breathing_seconds"]))))
        # Bound pleasant starter to max 90 seconds so it never becomes a procrastination excuse (Section 6)
        starter_max = min(90, max(10, int(patch.get("pleasant_starter_max_seconds", current["pleasant_starter_max_seconds"]))))
        sampling_interval = max(1, int(patch.get("sampling_interval", current["sampling_interval"])))
        steps = patch.get("steps") or current["steps"]
        starter_action = patch.get("pleasant_starter_action", current["pleasant_starter_action"])
        name = str(patch.get("name", current["name"]))

        with db() as conn:
            conn.execute(
                """
                update prep_protocols
                set name = ?, steps_json = ?, breathing_seconds = ?,
                    pleasant_starter_action = ?, pleasant_starter_max_seconds = ?,
                    sampling_interval = ?, updated_at = ?
                where user_id = ?
                """,
                (
                    name,
                    json_dump(steps),
                    breathing_seconds,
                    starter_action,
                    starter_max,
                    sampling_interval,
                    now,
                    user_id,
                ),
            )
        CompassRepository().audit("prep_protocol.update", user_id, {"name": name, "breathing_seconds": breathing_seconds})
        return self.get_or_create_prep_protocol(user_id)

    def log_prep_execution(self, payload: dict[str, Any]) -> dict[str, Any]:
        user_id = str(payload.get("user_id") or "moshe")
        protocol = self.get_or_create_prep_protocol(user_id)
        now = utc_now()
        log_id = resource_id("prep_log")
        next_exec_num = protocol["executions_count"] + 1
        sampled = (next_exec_num % protocol["sampling_interval"] == 1) or any(
            payload.get(k) is not None for k in ("tension_before", "tension_after_prep", "feeling_after_execution")
        )

        with db() as conn:
            conn.execute(
                """
                insert into prep_protocol_logs
                (log_id, protocol_id, user_id, target_type, target_id, sampled,
                 tension_before, tension_after_prep, feeling_after_execution,
                 action_started, action_completed, occurred_at)
                values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    log_id,
                    protocol["protocol_id"],
                    user_id,
                    str(payload.get("target_type") or "frog"),
                    payload.get("target_id"),
                    1 if sampled else 0,
                    payload.get("tension_before"),
                    payload.get("tension_after_prep"),
                    payload.get("feeling_after_execution"),
                    1 if bool(payload.get("action_started", True)) else 0,
                    1 if bool(payload.get("action_completed", False)) else 0,
                    now,
                ),
            )
            conn.execute(
                "update prep_protocols set executions_count = ?, updated_at = ? where protocol_id = ?",
                (next_exec_num, now, protocol["protocol_id"]),
            )

        tension_delta = None
        if payload.get("tension_before") is not None and payload.get("tension_after_prep") is not None:
            tension_delta = int(payload["tension_after_prep"]) - int(payload["tension_before"])

        return {
            "success": True,
            "log_id": log_id,
            "sampled_this_run": sampled,
            "next_sample_in_executions": protocol["sampling_interval"] - ((next_exec_num - 1) % protocol["sampling_interval"]),
            "tension_delta": tension_delta,
            "action_started": bool(payload.get("action_started", True)),
            "action_completed": bool(payload.get("action_completed", False)),
        }

    # --- 2. Routines & Habits Management (Section 7 & HABIT-001) ---

    def create_routine(self, payload: dict[str, Any]) -> dict[str, Any]:
        repo = CompassRepository()
        user_id = str(payload.get("user_id") or "moshe")
        policy = repo.get_user_autonomy_policy(user_id)
        if policy["active_role"] == "executor" and not payload.get("allow_in_executor_mode", False):
            return {
                "success": False,
                "status": "planner_role_required",
                "message": "יצירת שגרה חדשה או שינוי מדיניות מתבצעים בתפקיד המתכנן (Planner) בלבד.",
            }

        now = utc_now()
        routine_id = str(payload.get("routine_id") or resource_id("routine"))
        action_sequence = payload.get("action_sequence") or ["הכנה קצרה", "ביצוע השגרה", "סימון השלמה"]
        estimated_minutes = int(payload.get("estimated_minutes") or 20)
        minimum_minutes = int(payload.get("minimum_minutes") or max(2, estimated_minutes // 4))

        with db() as conn:
            conn.execute(
                """
                insert into routines
                (routine_id, user_id, name, domain, automation_kind, start_condition,
                 action_sequence_json, trigger_time_or_event, frequency,
                 minimum_viable_version, estimated_minutes, minimum_minutes,
                 skip_condition, completion_condition, difficulty_level,
                 flexible_streak_count, completions_count, skips_count,
                 last_completed_at, status, created_at, updated_at)
                values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    routine_id,
                    user_id,
                    str(payload["name"]).strip(),
                    str(payload.get("domain") or "physical"),
                    "beneficial_habit_trigger",
                    str(payload.get("start_condition") or "זמן בוקר או סיום קפה"),
                    json_dump(action_sequence),
                    str(payload.get("trigger_time_or_event") or "08:00"),
                    str(payload.get("frequency") or "daily"),
                    str(payload.get("minimum_viable_version") or "2 דקות של תנועה קלה / סט בודד"),
                    estimated_minutes,
                    minimum_minutes,
                    str(payload.get("skip_condition") or "כאב חריג, מחלה או אירוע חירום"),
                    str(payload.get("completion_condition") or "ביצוע הרצף המלא או הגרסה המינימלית"),
                    int(payload.get("difficulty_level", 4)),
                    0,
                    0,
                    0,
                    None,
                    "active",
                    now,
                    now,
                ),
            )

        routine = self.get_routine(routine_id)
        repo.log_ai_usage(
            {
                "user_id": user_id,
                "usage_type": "deterministic_bypass",
                "purpose": "routines.create",
                "reason": "Deterministic routine creation (0 LLM tokens)",
            }
        )
        repo.audit("routines.create", user_id, {"routine_id": routine_id, "name": payload["name"]})
        return {"success": True, "routine": routine}

    def get_routine(self, routine_id: str) -> dict[str, Any] | None:
        with db() as conn:
            row = conn.execute("select * from routines where routine_id = ?", (routine_id,)).fetchone()
        return self._routine_row(row) if row else None

    def list_routines(self, user_id: str = "moshe", status: str = "active") -> dict[str, Any]:
        with db() as conn:
            if status and status != "all":
                rows = conn.execute(
                    "select * from routines where user_id = ? and status = ? order by created_at asc",
                    (user_id, status),
                ).fetchall()
            else:
                rows = conn.execute(
                    "select * from routines where user_id = ? order by created_at asc",
                    (user_id,),
                ).fetchall()
        items = [self._routine_row(r) for r in rows]
        return {"success": True, "user_id": user_id, "count": len(items), "routines": items}

    def report_routine_execution(
        self,
        routine_id: str,
        *,
        outcome: str,
        user_id: str = "moshe",
        used_minimum_version: bool = False,
        resistance_level: int | None = None,
        energy_level: int | None = None,
        notes: str | None = None,
    ) -> dict[str, Any]:
        """
        Section 7, Section 9 & Acceptance Criterion #8:
        Records routine execution (`completed`, `minimum_completed`, `skipped`).
        Never penalizes skipping: flexible streak is preserved on valid skip!
        """
        if outcome not in {"completed", "minimum_completed", "skipped"}:
            raise ValueError("outcome must be 'completed', 'minimum_completed', or 'skipped'")

        routine = self.get_routine(routine_id)
        if not routine:
            return {"success": False, "error": "routine_not_found"}

        repo = CompassRepository()
        now = utc_now()
        log_id = resource_id("routine_log")
        used_min = used_minimum_version or (outcome == "minimum_completed")

        rule_result: dict[str, Any] = {}
        if (resistance_level is not None and resistance_level >= 7) or used_min:
            event = {
                "event_id": f"evt_hab_{uuid4().hex[:10]}",
                "event_type": "routine.resistance_detected",
                "event_version": "1.0",
                "source": "compass.routines",
                "user_id": user_id,
                "occurred_at": datetime.now(timezone.utc).isoformat(),
                "idempotency_key": f"hab_{log_id}",
                "payload": {
                    "routine_id": routine_id,
                    "resistance_level": resistance_level if resistance_level is not None else 7,
                    "energy_level": energy_level or 2,
                },
                "metadata": {"dry_run": False, "requested_actions": []},
            }
            eval_res = RulesEngineAdapter().evaluate_event(event, actor=user_id)
            rule_result = eval_res.get("result", {})
            if eval_res.get("connected") and rule_result:
                repo.save_rule_evaluation(event, rule_result)

        with db() as conn:
            conn.execute(
                """
                insert into routine_logs
                (log_id, routine_id, user_id, outcome, used_minimum_version,
                 resistance_level, energy_level, notes, occurred_at)
                values (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    log_id,
                    routine_id,
                    user_id,
                    outcome,
                    1 if used_min else 0,
                    resistance_level,
                    energy_level,
                    notes,
                    now,
                ),
            )

            if outcome in {"completed", "minimum_completed"}:
                conn.execute(
                    """
                    update routines
                    set flexible_streak_count = flexible_streak_count + 1,
                        completions_count = completions_count + 1,
                        last_completed_at = ?,
                        updated_at = ?
                    where routine_id = ?
                    """,
                    (now, now, routine_id),
                )
            else:
                # Acceptance Criterion #8: Skipping applies NO penalty and does NOT reset flexible_streak_count to 0!
                conn.execute(
                    """
                    update routines
                    set skips_count = skips_count + 1,
                        updated_at = ?
                    where routine_id = ?
                    """,
                    (now, routine_id),
                )

        updated = self.get_routine(routine_id)
        feedback = (
            f"השגרה הושלמה בגרסה המינימלית ('{routine['minimum_viable_version']}') – שמירה מצוינת על עקביות!"
            if used_min
            else (
                "השגרה הושלמה בהצלחה!"
                if outcome == "completed"
                else "הדילוג תועד ללא ענישה וללא איפוס הרצף הגמיש."
            )
        )
        return {
            "success": True,
            "log_id": log_id,
            "outcome": outcome,
            "used_minimum_version": used_min,
            "penalty_applied": False,
            "streak_preserved": True,
            "routine": updated,
            "feedback_he": feedback,
            "rule_evaluation": rule_result,
        }

    # --- 3. Executor Next-Action Guidance (Section 10) ---

    def get_executor_next_action(
        self,
        *,
        user_id: str = "moshe",
        energy_level: int = 3,
        available_minutes: int = 45,
        resistance_level: int = 4,
        active_safety_constraints: list[str] | None = None,
    ) -> dict[str, Any]:
        """
        Section 10:
        Guides the user in Executor Mode (`EXECUTOR_MODE`) to the single most appropriate
        next action within the approved policy boundaries, without asking the user to replan.
        - Automatically scales down to `minimum_viable_version` on high resistance (`HABIT-001`) or low energy (`PLAN-001`).
        - Attaches the 6-step Preparation Protocol (`MENTAL-001`) when starting a challenging frog or high-resistance action.
        """
        repo = CompassRepository()
        policy = repo.get_user_autonomy_policy(user_id)
        prep_protocol = self.get_or_create_prep_protocol(user_id)
        use_minimum = (energy_level <= 2 or resistance_level >= 7) and policy["allow_auto_minimum_viable"]

        rule_result: dict[str, Any] = {}
        if resistance_level >= 7:
            event = {
                "event_id": f"evt_exec_hab_{uuid4().hex[:10]}",
                "event_type": "routine.resistance_detected",
                "event_version": "1.0",
                "source": "compass.executor",
                "user_id": user_id,
                "occurred_at": datetime.now(timezone.utc).isoformat(),
                "idempotency_key": f"exec_hab_{uuid4().hex[:10]}",
                "payload": {"resistance_level": resistance_level, "energy_level": energy_level},
                "metadata": {"dry_run": False, "requested_actions": []},
            }
            eval_res = RulesEngineAdapter().evaluate_event(event, actor=user_id)
            rule_result = eval_res.get("result", {})
            if eval_res.get("connected") and rule_result:
                repo.save_rule_evaluation(event, rule_result)

        # Priority 1: If energy >= 3 and an active frog fits available_minutes, guide the daily frog first
        if energy_level >= 3:
            frog_sel = FrogsService().select_daily_frog(
                user_id=user_id,
                energy_level=energy_level,
                available_minutes=available_minutes,
                active_safety_constraints=active_safety_constraints,
                sync_to_task_commander=False,
            )
            if frog_sel.get("selected") and frog_sel.get("selected_frog"):
                frog = frog_sel["selected_frog"]
                attach_prep = frog["resistance_level"] >= 6 or resistance_level >= 6
                if attach_prep:
                    prep_evt = {
                        "event_id": f"evt_prep_{uuid4().hex[:10]}",
                        "event_type": "frog.starting",
                        "event_version": "1.0",
                        "source": "compass.executor",
                        "user_id": user_id,
                        "occurred_at": datetime.now(timezone.utc).isoformat(),
                        "idempotency_key": f"prep_{uuid4().hex[:10]}",
                        "payload": {"frog_id": frog["frog_id"], "expected_resistance": max(frog["resistance_level"], resistance_level)},
                        "metadata": {"dry_run": False, "requested_actions": []},
                    }
                    prep_eval = RulesEngineAdapter().evaluate_event(prep_evt, actor=user_id)
                    if prep_eval.get("connected") and prep_eval.get("result"):
                        repo.save_rule_evaluation(prep_evt, prep_eval["result"])
                        rule_result = prep_eval["result"]

                return {
                    "success": True,
                    "role": "executor",
                    "action_source": "frog",
                    "next_action": {
                        "id": frog["frog_id"],
                        "title": f"🐸 {frog['name']}",
                        "domain": frog["domain"],
                        "minutes": frog["estimated_minutes"],
                        "instruction_he": f"התמקד כעת בצעד הראשון בלבד: {frog['completion_condition']}",
                        "used_minimum_viable_version": False,
                    },
                    "preparation_protocol": prep_protocol if attach_prep else None,
                    "should_sample_prep_metrics": (prep_protocol["executions_count"] % prep_protocol["sampling_interval"] == 0),
                    "rule_evaluation": rule_result,
                }

        # Priority 2: Active routine (automatically scaled to minimum_viable_version when resistance is high or energy is low)
        routines = self.list_routines(user_id=user_id, status="active")["routines"]
        for r in routines:
            target_minutes = r["minimum_minutes"] if use_minimum else r["estimated_minutes"]
            if target_minutes <= available_minutes:
                instruction = (
                    f"גרסה מינימלית (HABIT-001): {r['minimum_viable_version']}"
                    if use_minimum
                    else f"רצף פעולות: {' -> '.join(r['action_sequence'])}"
                )
                return {
                    "success": True,
                    "role": "executor",
                    "action_source": "routine",
                    "next_action": {
                        "id": r["routine_id"],
                        "title": r["name"],
                        "domain": r["domain"],
                        "minutes": target_minutes,
                        "instruction_he": instruction,
                        "used_minimum_viable_version": use_minimum,
                    },
                    "preparation_protocol": prep_protocol if resistance_level >= 6 else None,
                    "should_sample_prep_metrics": (prep_protocol["executions_count"] % prep_protocol["sampling_interval"] == 0),
                    "rule_evaluation": rule_result,
                }

        # Priority 3: TaskCommander pending today instance
        tc_today = TaskCommanderAdapter().today(limit=5, user_id=user_id)["items"]
        for inst in tc_today:
            if inst["estimated_minutes"] <= available_minutes:
                return {
                    "success": True,
                    "role": "executor",
                    "action_source": "task_commander",
                    "next_action": {
                        "id": inst["instance_id"],
                        "title": inst["title"],
                        "domain": inst.get("category") or "operations",
                        "minutes": inst["estimated_minutes"],
                        "instruction_he": inst.get("description") or f"בצע את המשימה: {inst['title']}",
                        "used_minimum_viable_version": False,
                    },
                    "preparation_protocol": None,
                    "should_sample_prep_metrics": False,
                    "rule_evaluation": rule_result,
                }

        return {
            "success": True,
            "role": "executor",
            "action_source": "recovery_or_short_break",
            "next_action": {
                "id": "micro_recovery",
                "title": "נשימה והתאוששות קצרה (2 דקות)",
                "domain": "mental",
                "minutes": min(5, available_minutes),
                "instruction_he": "אין משימה שנכנסת בחלון הזמן/האנרגיה הנוכחי. בצע 60 שניות של נשימה רגועה.",
                "used_minimum_viable_version": True,
            },
            "preparation_protocol": None,
            "should_sample_prep_metrics": False,
            "rule_evaluation": rule_result,
        }

    def _protocol_row(self, row: Any) -> dict[str, Any]:
        return {
            "protocol_id": row["protocol_id"],
            "user_id": row["user_id"],
            "name": row["name"],
            "steps": json_load(row["steps_json"], DEFAULT_PREP_STEPS),
            "breathing_seconds": int(row["breathing_seconds"]),
            "pleasant_starter_action": row["pleasant_starter_action"],
            "pleasant_starter_max_seconds": int(row["pleasant_starter_max_seconds"]),
            "sampling_interval": int(row["sampling_interval"]),
            "executions_count": int(row["executions_count"]),
            "updated_at": row["updated_at"],
        }

    def _routine_row(self, row: Any) -> dict[str, Any]:
        return {
            "routine_id": row["routine_id"],
            "user_id": row["user_id"],
            "name": row["name"],
            "domain": row["domain"],
            "automation_kind": row["automation_kind"],
            "start_condition": row["start_condition"],
            "action_sequence": json_load(row["action_sequence_json"], []),
            "trigger_time_or_event": row["trigger_time_or_event"],
            "frequency": row["frequency"],
            "minimum_viable_version": row["minimum_viable_version"],
            "estimated_minutes": int(row["estimated_minutes"]),
            "minimum_minutes": int(row["minimum_minutes"]),
            "skip_condition": row["skip_condition"],
            "completion_condition": row["completion_condition"],
            "difficulty_level": int(row["difficulty_level"]),
            "flexible_streak_count": int(row["flexible_streak_count"]),
            "completions_count": int(row["completions_count"]),
            "skips_count": int(row["skips_count"]),
            "last_completed_at": row["last_completed_at"],
            "status": row["status"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }
