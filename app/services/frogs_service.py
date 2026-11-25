from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any
from uuid import uuid4

from app.database import db, json_dump, json_load, resource_id, utc_now
from app.repository import CompassRepository
from app.services.rules_engine import RulesEngineAdapter
from app.services.task_commander import TaskCommanderAdapter


class FrogsService:
    """
    Deterministic 'Eat That Frog' Engine (Section 5 of specification).
    Operates with 0 LLM tokens:
    - Distinguishes `one_time` vs. `ongoing` frogs.
    - Enforces minimum pool of 4 active frogs during evening check (`FROG-001`) without inventing frogs.
    - Selects daily morning frog (`FROG-002`) based on importance, resistance, urgency, available time,
      energy level, execution history, and safety constraints.
    - Automatically closes completed `one_time` frogs (`FROG-003`).
    - Keeps completed `ongoing` frogs active and requires user approval (`FROG-004`) before removing them.
    """

    MINIMUM_ACTIVE_FROGS = 4

    def create_frog(self, payload: dict[str, Any]) -> dict[str, Any]:
        repo = CompassRepository()
        idem_key = payload.get("idempotency_key")
        if idem_key and (cached := repo.get_idempotent_response(f"frogs.create:{idem_key}")):
            return {**cached, "already_existed": True}

        now = utc_now()
        frog_id = str(payload.get("frog_id") or resource_id("frog"))
        user_id = str(payload.get("user_id") or "moshe")
        frog_type = str(payload.get("frog_type") or "one_time")
        if frog_type not in {"one_time", "ongoing"}:
            raise ValueError("frog_type must be 'one_time' or 'ongoing'")

        with db() as conn:
            conn.execute(
                """
                insert into frogs
                (frog_id, user_id, name, description, domain, frog_type, importance,
                 resistance_level, difficulty_level, urgency, estimated_minutes,
                 attempts_count, completions_count, last_performed_at, status,
                 completion_condition, safety_constraints_json, created_at, updated_at)
                values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    frog_id,
                    user_id,
                    str(payload["name"]).strip(),
                    str(payload.get("description") or "").strip(),
                    str(payload.get("domain") or "core"),
                    frog_type,
                    int(payload.get("importance", 7)),
                    int(payload.get("resistance_level", 7)),
                    int(payload.get("difficulty_level", 5)),
                    int(payload.get("urgency", 5)),
                    int(payload.get("estimated_minutes", 25)),
                    int(payload.get("attempts_count", 0)),
                    int(payload.get("completions_count", 0)),
                    payload.get("last_performed_at"),
                    str(payload.get("status") or "active"),
                    str(payload.get("completion_condition") or "השלמת הפעולה המוגדרת"),
                    json_dump(payload.get("safety_constraints") or []),
                    now,
                    now,
                ),
            )

        frog = self.get_frog(frog_id)
        res = {"success": True, "frog": frog, "already_existed": False}
        repo.log_ai_usage(
            {
                "user_id": user_id,
                "usage_type": "deterministic_bypass",
                "purpose": "frogs.create",
                "reason": "Deterministic frog creation (0 LLM tokens)",
            }
        )
        repo.audit("frogs.create", user_id, {"frog_id": frog_id, "frog_type": frog_type, "name": payload["name"]})
        if idem_key:
            repo.remember_idempotent_response(f"frogs.create:{idem_key}", "frogs.create", res)
        return res

    def get_frog(self, frog_id: str) -> dict[str, Any] | None:
        with db() as conn:
            row = conn.execute("select * from frogs where frog_id = ?", (frog_id,)).fetchone()
        return self._frog_row(row) if row else None

    def list_frogs(self, user_id: str = "moshe", status: str | None = "active") -> dict[str, Any]:
        with db() as conn:
            if status and status != "all":
                rows = conn.execute(
                    "select * from frogs where user_id = ? and status = ? order by importance desc, resistance_level desc, urgency desc",
                    (user_id, status),
                ).fetchall()
            else:
                rows = conn.execute(
                    "select * from frogs where user_id = ? order by status = 'active' desc, importance desc, resistance_level desc",
                    (user_id,),
                ).fetchall()
        frogs = [self._frog_row(r) for r in rows]
        active_count = sum(1 for f in frogs if f["status"] == "active")
        return {
            "success": True,
            "user_id": user_id,
            "count": len(frogs),
            "active_count": active_count,
            "minimum_required": self.MINIMUM_ACTIVE_FROGS,
            "replenishment_needed": active_count < self.MINIMUM_ACTIVE_FROGS,
            "frogs": frogs,
        }

    def update_frog_scores(self, frog_id: str, patch: dict[str, Any], user_id: str = "moshe") -> dict[str, Any] | None:
        existing = self.get_frog(frog_id)
        if not existing:
            return None
        now = utc_now()
        updated = {
            "name": str(patch.get("name", existing["name"])),
            "description": str(patch.get("description", existing["description"])),
            "domain": str(patch.get("domain", existing["domain"])),
            "importance": int(patch.get("importance", existing["importance"])),
            "resistance_level": int(patch.get("resistance_level", existing["resistance_level"])),
            "difficulty_level": int(patch.get("difficulty_level", existing["difficulty_level"])),
            "urgency": int(patch.get("urgency", existing["urgency"])),
            "estimated_minutes": int(patch.get("estimated_minutes", existing["estimated_minutes"])),
            "completion_condition": str(patch.get("completion_condition", existing["completion_condition"])),
            "safety_constraints": patch.get("safety_constraints", existing["safety_constraints"]),
        }
        with db() as conn:
            conn.execute(
                """
                update frogs
                set name = ?, description = ?, domain = ?, importance = ?,
                    resistance_level = ?, difficulty_level = ?, urgency = ?,
                    estimated_minutes = ?, completion_condition = ?,
                    safety_constraints_json = ?, updated_at = ?
                where frog_id = ?
                """,
                (
                    updated["name"],
                    updated["description"],
                    updated["domain"],
                    updated["importance"],
                    updated["resistance_level"],
                    updated["difficulty_level"],
                    updated["urgency"],
                    updated["estimated_minutes"],
                    updated["completion_condition"],
                    json_dump(updated["safety_constraints"]),
                    now,
                    frog_id,
                ),
            )
        CompassRepository().audit("frogs.update_scores", user_id, {"frog_id": frog_id, **updated})
        return self.get_frog(frog_id)

    def evening_pool_check(self, user_id: str = "moshe") -> dict[str, Any]:
        """
        Section 5.2 & Rule FROG-001:
        Checks during evening review whether at least 4 active frogs exist.
        Never invents frogs to fill the quota; requests user replenishment when count < 4.
        """
        repo = CompassRepository()
        active_list = self.list_frogs(user_id=user_id, status="active")
        active_count = active_list["active_count"]
        missing_count = max(0, self.MINIMUM_ACTIVE_FROGS - active_count)
        replenishment_needed = active_count < self.MINIMUM_ACTIVE_FROGS

        event = {
            "event_id": f"evt_frog_eve_{uuid4().hex[:10]}",
            "event_type": "evening_review.frogs_check",
            "event_version": "1.0",
            "source": "compass.frogs",
            "user_id": user_id,
            "occurred_at": datetime.now(timezone.utc).isoformat(),
            "idempotency_key": f"frog_eve_{uuid4().hex[:10]}",
            "payload": {
                "active_frogs_count": active_count,
                "minimum_required": self.MINIMUM_ACTIVE_FROGS,
                "missing_count": missing_count,
            },
            "metadata": {"dry_run": False, "requested_actions": []},
        }
        eval_res = RulesEngineAdapter().evaluate_event(event, actor=user_id)
        rule_result = eval_res.get("result", {})
        if eval_res.get("connected") and rule_result:
            repo.save_rule_evaluation(event, rule_result)

        prompt_he = (
            f"במאגר הצפרדעים קיימות כעת {active_count} צפרדעים פעילות מתוך מינימום {self.MINIMUM_ACTIVE_FROGS}. "
            f"אנא הוסף {missing_count} צפרדעים אמיתיות שאתה נוטה לדחות (המערכת אינה ממציאה צפרדעים בעצמה)."
            if replenishment_needed
            else f"מאגר הצפרדעים תקין ({active_count} צפרדעים פעילות)."
        )
        repo.log_ai_usage(
            {
                "user_id": user_id,
                "usage_type": "deterministic_bypass",
                "purpose": "frogs.evening_pool_check",
                "reason": "Rule FROG-001 deterministic evening check (0 LLM tokens)",
            }
        )
        return {
            "success": True,
            "user_id": user_id,
            "active_frogs_count": active_count,
            "minimum_required": self.MINIMUM_ACTIVE_FROGS,
            "replenishment_needed": replenishment_needed,
            "missing_count": missing_count,
            "invented_frogs": [],
            "user_prompt_he": prompt_he,
            "active_frogs": active_list["frogs"],
            "rule_evaluation": rule_result,
        }

    def select_daily_frog(
        self,
        *,
        user_id: str = "moshe",
        target_date: date | None = None,
        energy_level: int = 4,
        available_minutes: int = 60,
        active_safety_constraints: list[str] | None = None,
        sync_to_task_commander: bool = True,
    ) -> dict[str, Any]:
        """
        Section 5.4 & Rule FROG-002:
        Deterministically selects the most suitable daily frog for early-day execution
        based on importance, resistance, urgency, available time, energy, execution history,
        and safety constraints.
        """
        repo = CompassRepository()
        plan_date_str = (target_date or date.today()).isoformat()
        constraints_set = {c.strip().lower() for c in (active_safety_constraints or []) if c.strip()}
        active_frogs = self.list_frogs(user_id=user_id, status="active")["frogs"]

        eligible: list[tuple[float, dict[str, Any], str]] = []
        skipped_reasons: list[dict[str, Any]] = []

        for frog in active_frogs:
            if frog["estimated_minutes"] > available_minutes:
                skipped_reasons.append(
                    {
                        "frog_id": frog["frog_id"],
                        "name": frog["name"],
                        "reason": f"דורשת {frog['estimated_minutes']} דקות אך זמינות רק {available_minutes} דקות",
                    }
                )
                continue

            frog_constraints = {str(c).strip().lower() for c in frog.get("safety_constraints", [])}
            violated = constraints_set.intersection(frog_constraints)
            if violated or (
                any(k in constraints_set for k in {"pain", "כאב", "injury", "פציעה"})
                and frog["domain"] == "physical"
                and frog["difficulty_level"] >= 6
            ):
                skipped_reasons.append(
                    {
                        "frog_id": frog["frog_id"],
                        "name": frog["name"],
                        "reason": "מדולגת עקב מגבלת בטיחות או כאב פעיל",
                    }
                )
                continue

            if energy_level <= 2 and frog["difficulty_level"] >= 8:
                skipped_reasons.append(
                    {
                        "frog_id": frog["frog_id"],
                        "name": frog["name"],
                        "reason": f"רמת קושי ({frog['difficulty_level']}) גבוהה מדי לאנרגיה נמוכה ({energy_level})",
                    }
                )
                continue

            # Deterministic scoring formula:
            # High energy (>=3): tackle high importance + high resistance + urgency early ("Eat That Frog").
            # Low energy (<=2): prioritize importance + urgency while moderating difficulty/resistance.
            if energy_level >= 3:
                score = (
                    frog["importance"] * 3.0
                    + frog["resistance_level"] * 2.2
                    + frog["urgency"] * 2.0
                    - frog["completions_count"] * 0.3
                )
            else:
                score = (
                    frog["importance"] * 3.0
                    + frog["urgency"] * 2.5
                    - frog["difficulty_level"] * 1.2
                    - frog["resistance_level"] * 0.5
                )

            # Bonus if never performed or not performed today
            if not frog["last_performed_at"]:
                score += 2.0
            elif str(frog["last_performed_at"])[:10] == plan_date_str:
                score -= 15.0

            reason = (
                f"ציון {score:.1f} (חשיבות={frog['importance']}, התנגדות={frog['resistance_level']}, "
                f"דחיפות={frog['urgency']}, זמן={frog['estimated_minutes']} דק', אנרגיה={energy_level})"
            )
            eligible.append((round(score, 2), frog, reason))

        eligible.sort(key=lambda item: (-item[0], item[1]["estimated_minutes"], item[1]["frog_id"]))

        event = {
            "event_id": f"evt_frog_sel_{uuid4().hex[:10]}",
            "event_type": "morning_plan.select_frog",
            "event_version": "1.0",
            "source": "compass.frogs",
            "user_id": user_id,
            "occurred_at": datetime.now(timezone.utc).isoformat(),
            "idempotency_key": f"frog_sel_{uuid4().hex[:10]}",
            "payload": {
                "active_frogs_count": len(active_frogs),
                "eligible_frogs_count": len(eligible),
                "energy_level": energy_level,
                "available_minutes": available_minutes,
            },
            "metadata": {"dry_run": False, "requested_actions": []},
        }
        eval_res = RulesEngineAdapter().evaluate_event(event, actor=user_id)
        rule_result = eval_res.get("result", {})
        if eval_res.get("connected") and rule_result:
            repo.save_rule_evaluation(event, rule_result)

        if not eligible:
            return {
                "success": True,
                "selected": False,
                "plan_date": plan_date_str,
                "selected_frog": None,
                "skipped_candidates": skipped_reasons,
                "explanation": "לא נמצאה צפרדע מתאימה לאילוצי הזמן, האנרגיה או הבטיחות הנוכחיים.",
                "rule_evaluation": rule_result,
            }

        top_score, chosen_frog, explanation = eligible[0]
        recommended_slot = "morning_early" if energy_level >= 3 else "morning_gentle_start"
        now = utc_now()
        selection_id = resource_id("frog_sel")

        with db() as conn:
            existing_sel = conn.execute(
                "select selection_id from daily_frog_selections where user_id = ? and plan_date = ?",
                (user_id, plan_date_str),
            ).fetchone()
            if existing_sel:
                selection_id = existing_sel["selection_id"]
                conn.execute(
                    """
                    update daily_frog_selections
                    set frog_id = ?, recommended_slot = ?, selection_score = ?,
                        status = ?, explanation = ?, rule_evaluation_id = ?, updated_at = ?
                    where selection_id = ?
                    """,
                    (
                        chosen_frog["frog_id"],
                        recommended_slot,
                        top_score,
                        "selected",
                        explanation,
                        rule_result.get("evaluation_id"),
                        now,
                        selection_id,
                    ),
                )
            else:
                conn.execute(
                    """
                    insert into daily_frog_selections
                    (selection_id, user_id, plan_date, frog_id, recommended_slot,
                     selection_score, status, explanation, rule_evaluation_id, created_at, updated_at)
                    values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        selection_id,
                        user_id,
                        plan_date_str,
                        chosen_frog["frog_id"],
                        recommended_slot,
                        top_score,
                        "selected",
                        explanation,
                        rule_result.get("evaluation_id"),
                        now,
                        now,
                    ),
                )

        tc_instance = None
        if sync_to_task_commander:
            tc_instance = TaskCommanderAdapter().create_task(
                {
                    "task_id": f"tc_frog_{chosen_frog['frog_id']}",
                    "user_id": user_id,
                    "title": f"🐸 צפרדע יומית: {chosen_frog['name']}",
                    "description": chosen_frog["completion_condition"],
                    "priority": "high",
                    "category": "frog",
                    "estimated_minutes": chosen_frog["estimated_minutes"],
                    "occurrence_date": plan_date_str,
                    "due_at": f"{plan_date_str}T08:30:00+00:00",
                    "source": "compass.frogs",
                }
            )

        repo.log_ai_usage(
            {
                "user_id": user_id,
                "usage_type": "deterministic_bypass",
                "purpose": "frogs.select_daily_frog",
                "reason": "Rule FROG-002 deterministic frog selection (0 LLM tokens)",
            }
        )
        return {
            "success": True,
            "selected": True,
            "selection_id": selection_id,
            "plan_date": plan_date_str,
            "recommended_slot": recommended_slot,
            "selection_score": top_score,
            "selected_frog": chosen_frog,
            "alternatives": [
                {"frog_id": f["frog_id"], "name": f["name"], "score": s, "reason": r}
                for s, f, r in eligible[1:]
            ],
            "skipped_candidates": skipped_reasons,
            "explanation": explanation,
            "task_commander_instance": tc_instance,
            "rule_evaluation": rule_result,
        }

    def override_daily_selection(
        self,
        *,
        user_id: str = "moshe",
        plan_date: str | None = None,
        action: str,
        replacement_frog_id: str | None = None,
        reason: str = "",
    ) -> dict[str, Any]:
        """Allows user to replace, defer, or cancel the daily frog selection (Section 5.4)."""
        if action not in {"replace", "defer", "cancel"}:
            raise ValueError("action must be 'replace', 'defer', or 'cancel'")
        date_str = plan_date or date.today().isoformat()
        now = utc_now()
        new_frog = None
        if action == "replace":
            if not replacement_frog_id:
                raise ValueError("replacement_frog_id is required when action='replace'")
            new_frog = self.get_frog(replacement_frog_id)
            if not new_frog:
                raise ValueError("Replacement frog not found")

        status_map = {"replace": "replaced_by_user", "defer": "deferred_by_user", "cancel": "cancelled_by_user"}
        new_status = status_map[action]
        target_frog_id = new_frog["frog_id"] if new_frog else None

        with db() as conn:
            row = conn.execute(
                "select selection_id from daily_frog_selections where user_id = ? and plan_date = ?",
                (user_id, date_str),
            ).fetchone()
            if row:
                conn.execute(
                    """
                    update daily_frog_selections
                    set frog_id = coalesce(?, frog_id), status = ?, explanation = ?, updated_at = ?
                    where selection_id = ?
                    """,
                    (
                        target_frog_id,
                        new_status,
                        reason or f"User override: {action}",
                        now,
                        row["selection_id"],
                    ),
                )
                selection_id = row["selection_id"]
            else:
                selection_id = resource_id("frog_sel")
                conn.execute(
                    """
                    insert into daily_frog_selections
                    (selection_id, user_id, plan_date, frog_id, recommended_slot,
                     selection_score, status, explanation, rule_evaluation_id, created_at, updated_at)
                    values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        selection_id,
                        user_id,
                        date_str,
                        target_frog_id,
                        "user_override",
                        0.0,
                        new_status,
                        reason or f"User override: {action}",
                        None,
                        now,
                        now,
                    ),
                )
        CompassRepository().audit(
            "frogs.daily_selection.override",
            user_id,
            {"plan_date": date_str, "action": action, "replacement_frog_id": replacement_frog_id, "reason": reason},
        )
        return {
            "success": True,
            "selection_id": selection_id,
            "plan_date": date_str,
            "status": new_status,
            "selected_frog": new_frog,
        }

    def report_frog_execution(
        self,
        frog_id: str,
        *,
        outcome: str,
        user_id: str = "moshe",
        notes: str | None = None,
        energy_level: int | None = None,
        tension_before: int | None = None,
        tension_after: int | None = None,
        approval_confirmed: bool = False,
    ) -> dict[str, Any]:
        """
        Section 5.5 & Rules FROG-003, FROG-004:
        Allowed outcomes:
        - `completed` (בוצע)
        - `partial` (בוצע חלקית)
        - `not_done` (לא בוצע)
        - `deferred` (נדחה)
        - `no_longer_resisted` (כבר אינו מעורר התנגדות)
        """
        allowed_outcomes = {"completed", "partial", "not_done", "deferred", "no_longer_resisted"}
        if outcome not in allowed_outcomes:
            raise ValueError(f"outcome must be one of {sorted(allowed_outcomes)}")

        frog = self.get_frog(frog_id)
        if not frog:
            return {"success": False, "error": "frog_not_found"}

        repo = CompassRepository()
        now = utc_now()
        today_str = date.today().isoformat()
        log_id = resource_id("frog_log")

        with db() as conn:
            conn.execute(
                """
                insert into frog_logs
                (log_id, frog_id, user_id, plan_date, outcome, notes,
                 energy_level, tension_before, tension_after, occurred_at)
                values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    log_id,
                    frog_id,
                    user_id,
                    today_str,
                    outcome,
                    notes,
                    energy_level,
                    tension_before,
                    tension_after,
                    now,
                ),
            )

        attempts_delta = 1 if outcome in {"completed", "partial"} else 0
        completions_delta = 1 if outcome == "completed" else 0
        new_status = frog["status"]
        rule_result: dict[str, Any] = {}
        approval_request_id = None

        if outcome == "completed":
            # Evaluate FROG-003
            event = {
                "event_id": f"evt_frog_done_{uuid4().hex[:10]}",
                "event_type": "frog.completed",
                "event_version": "1.0",
                "source": "compass.frogs",
                "user_id": user_id,
                "occurred_at": datetime.now(timezone.utc).isoformat(),
                "idempotency_key": f"frog_done_{log_id}",
                "payload": {"frog_id": frog_id, "frog_type": frog["frog_type"], "name": frog["name"]},
                "metadata": {"dry_run": False, "requested_actions": []},
            }
            eval_res = RulesEngineAdapter().evaluate_event(event, actor=user_id)
            rule_result = eval_res.get("result", {})
            if eval_res.get("connected") and rule_result:
                repo.save_rule_evaluation(event, rule_result)

            if frog["frog_type"] == "one_time":
                new_status = "completed"
            else:
                # Ongoing frog stays active in pool! (Acceptance Criterion #3)
                new_status = "active"

        elif outcome == "no_longer_resisted":
            if frog["frog_type"] == "ongoing":
                return self.request_remove_frog(
                    frog_id=frog_id,
                    user_id=user_id,
                    reason=notes or "המשתמש דיווח שהפעולה כבר אינה מעוררת התנגדות",
                    approval_confirmed=approval_confirmed,
                )
            new_status = "graduated"

        with db() as conn:
            conn.execute(
                """
                update frogs
                set attempts_count = attempts_count + ?,
                    completions_count = completions_count + ?,
                    last_performed_at = case when ? > 0 then ? else last_performed_at end,
                    status = ?,
                    updated_at = ?
                where frog_id = ?
                """,
                (
                    attempts_delta,
                    completions_delta,
                    attempts_delta,
                    now,
                    new_status,
                    now,
                    frog_id,
                ),
            )

        feedback_map = {
            "completed": (
                "כל הכבוד על צליחת ההתנגדות! הצפרדע החד-פעמית הושלמה ונסגרה."
                if frog["frog_type"] == "one_time"
                else "הצפרדע המתמשכת בוצעה היום ונשארת במאגר הפעיל להמשך ביסוס ההרגל."
            ),
            "partial": "התחלה וביצוע חלקי הם ניצחון ישיר מול הימנעות.",
            "not_done": "נרשם ללא שיפוטיות. נבדוק אם כדאי להתאים את הזמן, האנרגיה או פרוטוקול ההכנה.",
            "deferred": "הצפרדע נדחתה למועד מתאים יותר ללא ענישה.",
            "no_longer_resisted": "הפעולה כבר אינה מעוררת התנגדות.",
        }

        updated_frog = self.get_frog(frog_id)
        if outcome in {"completed", "partial"} and frog.get("domain"):
            try:
                from app.services.growth_service import GrowthChallengesAndPlayService
                GrowthChallengesAndPlayService().record_domain_activity(user_id, str(frog["domain"]), occurred_at=now)
            except Exception:
                pass
        repo.audit("frogs.report", user_id, {"frog_id": frog_id, "outcome": outcome, "new_status": new_status})
        return {
            "success": True,
            "log_id": log_id,
            "outcome": outcome,
            "frog": updated_frog,
            "judgment_free_feedback": feedback_map[outcome],
            "approval_request_id": approval_request_id,
            "rule_evaluation": rule_result,
        }

    def request_remove_frog(
        self,
        frog_id: str,
        *,
        user_id: str = "moshe",
        reason: str = "",
        approval_confirmed: bool = False,
    ) -> dict[str, Any]:
        """
        Section 5.5 & Rule FROG-004 (Acceptance Criteria #3, #4):
        Removing an ongoing frog requires explicit user approval.
        """
        frog = self.get_frog(frog_id)
        if not frog:
            return {"success": False, "error": "frog_not_found"}

        repo = CompassRepository()
        event = {
            "event_id": f"evt_frog_rm_{uuid4().hex[:10]}",
            "event_type": "frog.remove_requested",
            "event_version": "1.0",
            "source": "compass.frogs",
            "user_id": user_id,
            "occurred_at": datetime.now(timezone.utc).isoformat(),
            "idempotency_key": f"frog_rm_{uuid4().hex[:10]}",
            "payload": {
                "frog_id": frog_id,
                "frog_type": frog["frog_type"],
                "name": frog["name"],
                "reason": reason,
            },
            "metadata": {"dry_run": False, "requested_actions": []},
        }
        eval_res = RulesEngineAdapter().evaluate_event(event, actor=user_id)
        rule_result = eval_res.get("result", {})
        if eval_res.get("connected") and rule_result:
            repo.save_rule_evaluation(event, rule_result)

        if frog["frog_type"] == "ongoing" and not approval_confirmed:
            approval = repo.create_approval_request(
                {
                    "user_id": user_id,
                    "title": f"אישור הסרת צפרדע מתמשכת: {frog['name']} (FROG-004)",
                    "description": reason or "אישור שהפעולה המתמשכת כבר אינה מעוררת התנגדות וניתן להסירה ממאגר הצפרדעים.",
                    "requested_by": user_id,
                    "action_type": "frogs.remove_ongoing",
                    "risk_level": "medium",
                    "proposed_action": {"frog_id": frog_id, "name": frog["name"], "reason": reason},
                    "rule_result": rule_result,
                }
            )
            return {
                "success": True,
                "status": "approval_required",
                "approval_request_id": approval["resource_id"],
                "frog": frog,
                "rule_evaluation": rule_result,
            }

        now = utc_now()
        new_status = "graduated" if frog["frog_type"] == "ongoing" else "removed"
        with db() as conn:
            conn.execute(
                "update frogs set status = ?, updated_at = ? where frog_id = ?",
                (new_status, now, frog_id),
            )
        updated = self.get_frog(frog_id)
        repo.audit("frogs.removed", user_id, {"frog_id": frog_id, "new_status": new_status, "reason": reason})
        return {
            "success": True,
            "status": new_status,
            "frog": updated,
            "rule_evaluation": rule_result,
        }

    def _frog_row(self, row: Any) -> dict[str, Any]:
        return {
            "frog_id": row["frog_id"],
            "user_id": row["user_id"],
            "name": row["name"],
            "description": row["description"],
            "domain": row["domain"],
            "frog_type": row["frog_type"],
            "importance": int(row["importance"]),
            "resistance_level": int(row["resistance_level"]),
            "difficulty_level": int(row["difficulty_level"]),
            "urgency": int(row["urgency"]),
            "estimated_minutes": int(row["estimated_minutes"]),
            "attempts_count": int(row["attempts_count"]),
            "completions_count": int(row["completions_count"]),
            "last_performed_at": row["last_performed_at"],
            "status": row["status"],
            "completion_condition": row["completion_condition"],
            "safety_constraints": json_load(row["safety_constraints_json"], []),
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }
