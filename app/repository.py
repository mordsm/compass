from __future__ import annotations

from typing import Any

from app.database import db, json_dump, json_load, resource_id, utc_now


class CompassRepository:
    def get_idempotent_response(self, key: str) -> dict[str, Any] | None:
        with db() as conn:
            row = conn.execute("select response_json from idempotency_keys where key = ?", (key,)).fetchone()
        return json_load(row["response_json"], None) if row else None

    def remember_idempotent_response(self, key: str | None, endpoint: str, response: dict[str, Any]) -> None:
        if not key:
            return
        with db() as conn:
            conn.execute(
                """
                insert or ignore into idempotency_keys (key, endpoint, response_json, created_at)
                values (?, ?, ?, ?)
                """,
                (key, endpoint, json_dump(response), utc_now()),
            )

    def audit(self, action: str, user_id: str | None, payload: dict[str, Any]) -> None:
        with db() as conn:
            conn.execute(
                "insert into audit_log (id, action, user_id, payload_json, created_at) values (?, ?, ?, ?, ?)",
                (resource_id("audit"), action, user_id, json_dump(payload), utc_now()),
            )

    def save_rule_evaluation(self, request: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
        evaluation_id = str(result.get("evaluation_id") or resource_id("eval"))
        with db() as conn:
            conn.execute(
                """
                insert into rule_evaluations
                (id, event_id, user_id, event_type, source, final_decision, risk_level, dry_run,
                 request_json, result_json, created_at)
                values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    evaluation_id,
                    request["event_id"],
                    request["user_id"],
                    request["event_type"],
                    request["source"],
                    str(result.get("final_decision") or result.get("decision") or "recommendation_only"),
                    str(result.get("risk_level") or "low"),
                    1 if bool(result.get("dry_run")) else 0,
                    json_dump(request),
                    json_dump(result),
                    utc_now(),
                ),
            )
        return {"success": True, "status": "created", "resource_id": evaluation_id, "already_existed": False}

    def save_conversation_event(self, payload: dict[str, Any]) -> dict[str, Any]:
        event_id = resource_id("event")
        with db() as conn:
            conn.execute(
                """
                insert into conversation_events
                (id, user_id, conversation_id, event_type, content, importance, structured_payload_json, created_at)
                values (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event_id,
                    payload["user_id"],
                    payload.get("conversation_id"),
                    payload["event_type"],
                    payload["content"],
                    payload.get("importance", "medium"),
                    json_dump(payload.get("structured_payload", {})),
                    utc_now(),
                ),
            )
        return {"success": True, "status": "created", "resource_id": event_id, "already_existed": False}

    def finalize_conversation(self, payload: dict[str, Any]) -> dict[str, Any]:
        summary_id = resource_id("summary")
        with db() as conn:
            conn.execute(
                """
                insert into conversation_summaries
                (id, user_id, conversation_id, summary, decisions_json, tasks_json, open_questions_json, created_at)
                values (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    summary_id,
                    payload["user_id"],
                    payload.get("conversation_id"),
                    payload["summary"],
                    json_dump(payload.get("decisions", [])),
                    json_dump(payload.get("tasks", [])),
                    json_dump(payload.get("open_questions", [])),
                    utc_now(),
                ),
            )
        return {"success": True, "status": "created", "resource_id": summary_id, "already_existed": False}

    def upsert_task(self, payload: dict[str, Any]) -> dict[str, Any]:
        now = utc_now()
        task_id = payload.get("task_id")
        with db() as conn:
            existing = None
            if task_id:
                existing = conn.execute("select id from tasks where id = ?", (task_id,)).fetchone()
            if existing:
                conn.execute(
                    """
                    update tasks
                    set title = ?, description = ?, status = ?, due_date = ?, priority = ?,
                        source = ?, metadata_json = ?, updated_at = ?
                    where id = ?
                    """,
                    (
                        payload["title"],
                        payload.get("description"),
                        payload.get("status", "proposed"),
                        payload.get("due_date"),
                        payload.get("priority"),
                        payload.get("source", "gpt"),
                        json_dump(payload.get("metadata", {})),
                        now,
                        task_id,
                    ),
                )
                return {"success": True, "status": "updated", "resource_id": task_id, "already_existed": True}

            task_id = task_id or resource_id("task")
            conn.execute(
                """
                insert into tasks
                (id, user_id, title, description, status, due_date, priority, source, metadata_json, created_at, updated_at)
                values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    task_id,
                    payload["user_id"],
                    payload["title"],
                    payload.get("description"),
                    payload.get("status", "proposed"),
                    payload.get("due_date"),
                    payload.get("priority"),
                    payload.get("source", "gpt"),
                    json_dump(payload.get("metadata", {})),
                    now,
                    now,
                ),
            )
        return {"success": True, "status": "created", "resource_id": task_id, "already_existed": False}

    def save_daily_plan(self, payload: dict[str, Any]) -> dict[str, Any]:
        now = utc_now()
        plan_id = payload.get("plan_id") or resource_id("plan")
        with db() as conn:
            conn.execute(
                """
                insert into daily_plans
                (id, user_id, plan_date, status, energy_level, available_minutes, outcomes_json,
                 scheduled_tasks_json, deferred_items_json, risks_json, raw_payload_json, created_at, updated_at)
                values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    plan_id,
                    payload["user_id"],
                    payload["date"],
                    payload.get("status", "approved"),
                    payload.get("energy_level"),
                    payload.get("available_minutes"),
                    json_dump(payload.get("outcomes", [])),
                    json_dump(payload.get("scheduled_tasks", [])),
                    json_dump(payload.get("deferred_items", [])),
                    json_dump(payload.get("risks", [])),
                    json_dump(payload),
                    now,
                    now,
                ),
            )
        return {"success": True, "status": "created", "resource_id": plan_id, "already_existed": False}

    def create_approval_request(self, payload: dict[str, Any]) -> dict[str, Any]:
        now = utc_now()
        approval_id = resource_id("approval")
        with db() as conn:
            conn.execute(
                """
                insert into approval_requests
                (id, user_id, title, description, requested_by, action_type, status, risk_level,
                 proposed_action_json, rule_result_json, created_at, updated_at)
                values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    approval_id,
                    payload["user_id"],
                    payload["title"],
                    payload.get("description"),
                    payload.get("requested_by", "gpt"),
                    payload["action_type"],
                    "pending",
                    payload.get("risk_level", "medium"),
                    json_dump(payload.get("proposed_action", {})),
                    json_dump(payload.get("rule_result", {})),
                    now,
                    now,
                ),
            )
        return {"success": True, "status": "pending", "resource_id": approval_id, "already_existed": False}

    def list_approval_requests(
        self,
        user_id: str,
        status: str = "pending",
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        with db() as conn:
            rows = conn.execute(
                """
                select * from approval_requests
                where user_id = ? and status = ?
                order by created_at desc
                limit ?
                """,
                (user_id, status, limit),
            ).fetchall()
        return [self._approval_row(row) for row in rows]

    def get_approval_request(self, approval_id: str) -> dict[str, Any] | None:
        with db() as conn:
            row = conn.execute("select * from approval_requests where id = ?", (approval_id,)).fetchone()
        return self._approval_row(row) if row else None

    def decide_approval_request(
        self,
        approval_id: str,
        status: str,
        decision_by: str,
        decision_notes: str | None = None,
    ) -> dict[str, Any] | None:
        now = utc_now()
        with db() as conn:
            row = conn.execute("select id from approval_requests where id = ?", (approval_id,)).fetchone()
            if not row:
                return None
            conn.execute(
                """
                update approval_requests
                set status = ?, updated_at = ?, decided_at = ?, decision_by = ?, decision_notes = ?
                where id = ?
                """,
                (status, now, now, decision_by, decision_notes, approval_id),
            )
        return self.get_approval_request(approval_id)

    def list_open_tasks(self, user_id: str, limit: int = 20) -> list[dict[str, Any]]:
        with db() as conn:
            rows = conn.execute(
                """
                select * from tasks
                where user_id = ? and status in ('mentioned', 'proposed', 'approved', 'active', 'open')
                order by due_date is null, due_date asc, updated_at desc
                limit ?
                """,
                (user_id, limit),
            ).fetchall()
        return [self._task_row(row) for row in rows]

    def list_recent_events(self, user_id: str, limit: int = 10) -> list[dict[str, Any]]:
        with db() as conn:
            rows = conn.execute(
                """
                select * from conversation_events
                where user_id = ?
                order by created_at desc
                limit ?
                """,
                (user_id, limit),
            ).fetchall()
        return [
            {
                "id": row["id"],
                "event_type": row["event_type"],
                "content": row["content"],
                "importance": row["importance"],
                "created_at": row["created_at"],
                "structured_payload": json_load(row["structured_payload_json"], {}),
            }
            for row in rows
        ]

    def list_recent_daily_plans(self, user_id: str, limit: int = 5) -> list[dict[str, Any]]:
        with db() as conn:
            rows = conn.execute(
                """
                select id, plan_date, status, energy_level, available_minutes, outcomes_json, risks_json
                from daily_plans
                where user_id = ?
                order by plan_date desc, created_at desc
                limit ?
                """,
                (user_id, limit),
            ).fetchall()
        return [
            {
                "id": row["id"],
                "date": row["plan_date"],
                "status": row["status"],
                "energy_level": row["energy_level"],
                "available_minutes": row["available_minutes"],
                "outcomes": json_load(row["outcomes_json"], []),
                "risks": json_load(row["risks_json"], []),
            }
            for row in rows
        ]

    def _task_row(self, row: Any) -> dict[str, Any]:
        return {
            "id": row["id"],
            "title": row["title"],
            "description": row["description"],
            "status": row["status"],
            "due_date": row["due_date"],
            "priority": row["priority"],
            "source": row["source"],
            "metadata": json_load(row["metadata_json"], {}),
            "updated_at": row["updated_at"],
        }

    def _approval_row(self, row: Any) -> dict[str, Any]:
        return {
            "id": row["id"],
            "user_id": row["user_id"],
            "title": row["title"],
            "description": row["description"],
            "requested_by": row["requested_by"],
            "action_type": row["action_type"],
            "status": row["status"],
            "risk_level": row["risk_level"],
            "proposed_action": json_load(row["proposed_action_json"], {}),
            "rule_result": json_load(row["rule_result_json"], {}),
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
            "decided_at": row["decided_at"],
            "decision_by": row["decision_by"],
            "decision_notes": row["decision_notes"],
        }

    def get_weekly_progress(self, user_id: str, week_start: str | None = None) -> dict[str, Any]:
        from datetime import date, timedelta

        anchor = date.fromisoformat(week_start) if week_start else date.today()
        monday = anchor - timedelta(days=anchor.weekday())
        sunday = monday + timedelta(days=6)
        start_str = monday.isoformat()
        end_str = sunday.isoformat()
        start_ts = f"{start_str}T00:00:00"
        end_ts = f"{end_str}T23:59:59.999999+99:99"

        with db() as conn:
            task_rows = conn.execute(
                "select status, due_date, updated_at from tasks where user_id = ?",
                (user_id,),
            ).fetchall()
            plan_rows = conn.execute(
                "select plan_date, outcomes_json from daily_plans where user_id = ? and plan_date >= ? and plan_date <= ?",
                (user_id, start_str, end_str),
            ).fetchall()
            pending_approvals_row = conn.execute(
                "select count(*) as cnt from approval_requests where user_id = ? and status = 'pending'",
                (user_id,),
            ).fetchone()
            training_rows = conn.execute(
                "select completed_at, status from msp_training_sessions where user_id = ? and status in ('completed', 'completed_with_safety_note')",
                (user_id,),
            ).fetchall()

        tasks_touched = 0
        tasks_completed = 0
        overdue_open_tasks = 0
        for r in task_rows:
            upd_date = str(r["updated_at"] or "")[:10]
            st = str(r["status"] or "").lower()
            if start_str <= upd_date <= end_str:
                tasks_touched += 1
                if st in {"completed", "done"}:
                    tasks_completed += 1
            if st in {"mentioned", "proposed", "approved", "active", "open"}:
                due = str(r["due_date"] or "")[:10]
                if due and due <= end_str:
                    overdue_open_tasks += 1

        planned_days = len({str(r["plan_date"]) for r in plan_rows})
        outcomes_planned = sum(len(json_load(r["outcomes_json"], [])) for r in plan_rows)
        training_completed = sum(
            1 for r in training_rows if start_str <= str(r["completed_at"] or "")[:10] <= end_str
        )
        completion_rate = round((tasks_completed / tasks_touched) * 100.0, 1) if tasks_touched else 0.0
        coverage_pct = round((planned_days / 7.0) * 100.0, 1)
        pending_approvals = int(pending_approvals_row["cnt"]) if pending_approvals_row else 0

        return {
            "user_id": user_id,
            "period": {"start": start_str, "end": end_str},
            "metrics": {
                "tasks_completed": tasks_completed,
                "tasks_touched": tasks_touched,
                "task_completion_rate_pct": completion_rate,
                "planned_days": planned_days,
                "planning_coverage_pct": coverage_pct,
                "outcomes_planned": outcomes_planned,
                "overdue_open_tasks": overdue_open_tasks,
                "pending_approvals": pending_approvals,
                "training_sessions_completed": training_completed,
            },
            "definitions": {
                "task_completion_rate_pct": "משימות שהושלמו מתוך משימות שעודכנו בשבוע",
                "planning_coverage_pct": "ימים עם תוכנית יומית מתוך 7 ימי השבוע",
            },
        }

    # --- Phase 1: Rule Catalog Overrides, Versioning & Rollback ---

    def get_rule_overrides_map(self) -> dict[str, dict[str, Any]]:
        with db() as conn:
            rows = conn.execute("select rule_id, override_json from rule_catalog_overrides").fetchall()
        return {row["rule_id"]: json_load(row["override_json"], {}) for row in rows}

    def save_rule_override(
        self,
        rule_id: str,
        snapshot: dict[str, Any],
        updated_by: str = "user",
        change_note: str = "Rule updated",
        baseline_snapshot: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        now = utc_now()
        with db() as conn:
            hist_rows = conn.execute(
                "select max(version) as max_v from rule_version_history where rule_id = ?",
                (rule_id,),
            ).fetchone()
            max_v = int(hist_rows["max_v"] or 0) if hist_rows else 0
            if max_v == 0:
                # Seed version 1 baseline before applying first modification
                base_snapshot = dict(baseline_snapshot or snapshot)
                base_snapshot["version"] = 1
                conn.execute(
                    """
                    insert into rule_version_history
                    (id, rule_id, version, snapshot_json, change_note, updated_by, updated_at)
                    values (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (resource_id("rule_ver"), rule_id, 1, json_dump(base_snapshot), "Initial version", "system", now),
                )
                max_v = 1
            next_v = max_v + 1
            snapshot = dict(snapshot)
            snapshot["version"] = next_v
            snapshot["updated_at"] = now

            existing = conn.execute(
                "select rule_id from rule_catalog_overrides where rule_id = ?",
                (rule_id,),
            ).fetchone()
            if existing:
                conn.execute(
                    """
                    update rule_catalog_overrides
                    set version = ?, override_json = ?, updated_by = ?, updated_at = ?
                    where rule_id = ?
                    """,
                    (next_v, json_dump(snapshot), updated_by, now, rule_id),
                )
            else:
                conn.execute(
                    """
                    insert into rule_catalog_overrides (rule_id, version, override_json, updated_by, updated_at)
                    values (?, ?, ?, ?, ?)
                    """,
                    (rule_id, next_v, json_dump(snapshot), updated_by, now),
                )

            conn.execute(
                """
                insert into rule_version_history
                (id, rule_id, version, snapshot_json, change_note, updated_by, updated_at)
                values (?, ?, ?, ?, ?, ?, ?)
                """,
                (resource_id("rule_ver"), rule_id, next_v, json_dump(snapshot), change_note, updated_by, now),
            )
        return snapshot

    def list_rule_versions(self, rule_id: str, initial_snapshot: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        with db() as conn:
            rows = conn.execute(
                "select * from rule_version_history where rule_id = ? order by version asc",
                (rule_id,),
            ).fetchall()
        if not rows and initial_snapshot:
            return [
                {
                    "rule_id": rule_id,
                    "version": int(initial_snapshot.get("version", 1)),
                    "snapshot": initial_snapshot,
                    "change_note": "Initial catalog version",
                    "updated_by": "system",
                    "updated_at": initial_snapshot.get("updated_at", "2026-11-24T00:00:00Z"),
                }
            ]
        return [
            {
                "rule_id": row["rule_id"],
                "version": int(row["version"]),
                "snapshot": json_load(row["snapshot_json"], {}),
                "change_note": row["change_note"],
                "updated_by": row["updated_by"],
                "updated_at": row["updated_at"],
            }
            for row in rows
        ]

    # --- Phase 1: Decision Explanations & History ---

    def list_recent_rule_evaluations(self, user_id: str, limit: int = 20) -> list[dict[str, Any]]:
        with db() as conn:
            rows = conn.execute(
                """
                select * from rule_evaluations
                where user_id = ?
                order by created_at desc
                limit ?
                """,
                (user_id, limit),
            ).fetchall()
        return [self._evaluation_row(row) for row in rows]

    def get_rule_evaluation(self, evaluation_id: str) -> dict[str, Any] | None:
        with db() as conn:
            row = conn.execute(
                "select * from rule_evaluations where id = ?",
                (evaluation_id,),
            ).fetchone()
        return self._evaluation_row(row) if row else None

    def _evaluation_row(self, row: Any) -> dict[str, Any]:
        req = json_load(row["request_json"], {})
        res = json_load(row["result_json"], {})
        return {
            "decision_id": row["id"],
            "evaluation_id": row["id"],
            "event_id": row["event_id"],
            "user_id": row["user_id"],
            "event_type": row["event_type"],
            "source": row["source"],
            "final_decision": row["final_decision"],
            "risk_level": row["risk_level"],
            "dry_run": bool(row["dry_run"]),
            "created_at": row["created_at"],
            "trigger_event": req,
            "relevant_data": req.get("payload", {}),
            "matched_rules": res.get("matched_rules", []),
            "alternatives_considered": res.get("alternatives_considered", []),
            "conflicts_resolved": res.get("conflicts_resolved", []),
            "chosen_actions": res.get("allowed_actions", []) + res.get("approval_required_actions", []),
            "blocked_actions": res.get("blocked_actions", []),
            "requires_approval": row["final_decision"] == "require_approval" or bool(res.get("approval_required_actions")),
            "explanation": res.get("explanation", ""),
            "execution_status": res.get("execution_status", "evaluated"),
            "raw_result": res,
        }

    def cancel_rule_evaluation(self, evaluation_id: str, cancelled_by: str, reason: str = "") -> dict[str, Any] | None:
        with db() as conn:
            row = conn.execute("select * from rule_evaluations where id = ?", (evaluation_id,)).fetchone()
            if not row:
                return None
            res = json_load(row["result_json"], {})
            res["execution_status"] = "cancelled_before_execution"
            res["cancelled_by"] = cancelled_by
            res["cancel_reason"] = reason
            conn.execute(
                "update rule_evaluations set final_decision = ?, result_json = ? where id = ?",
                ("cancelled", json_dump(res), evaluation_id),
            )
        return self.get_rule_evaluation(evaluation_id)

    # --- Phase 1: Autonomy Boundaries & Planner/Executor Policy ---

    def get_user_autonomy_policy(self, user_id: str) -> dict[str, Any]:
        now = utc_now()
        default_weights = {"mental": 10, "physical": 10, "ai_professional": 10, "enrichment": 4}
        with db() as conn:
            row = conn.execute(
                "select * from user_autonomy_policy where user_id = ?",
                (user_id,),
            ).fetchone()
            if not row:
                conn.execute(
                    """
                    insert into user_autonomy_policy
                    (user_id, active_role, automation_paused, max_daily_minutes,
                     max_challenge_difficulty, allow_auto_order_actions, allow_auto_minimum_viable,
                     priority_weights_json, version, updated_at)
                    values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (user_id, "planner", 0, 180, 5, 1, 1, json_dump(default_weights), 1, now),
                )
                row = conn.execute(
                    "select * from user_autonomy_policy where user_id = ?",
                    (user_id,),
                ).fetchone()
        return {
            "user_id": row["user_id"],
            "active_role": row["active_role"],
            "automation_paused": bool(row["automation_paused"]),
            "max_daily_minutes": int(row["max_daily_minutes"]),
            "max_challenge_difficulty": int(row["max_challenge_difficulty"]),
            "allow_auto_order_actions": bool(row["allow_auto_order_actions"]),
            "allow_auto_minimum_viable": bool(row["allow_auto_minimum_viable"]),
            "priority_weights": json_load(row["priority_weights_json"], default_weights),
            "version": int(row["version"]),
            "updated_at": row["updated_at"],
        }

    def update_user_autonomy_policy(self, user_id: str, patch: dict[str, Any]) -> dict[str, Any]:
        current = self.get_user_autonomy_policy(user_id)
        now = utc_now()
        next_version = current["version"] + 1
        updated = {
            "active_role": str(patch.get("active_role", current["active_role"])),
            "automation_paused": 1 if bool(patch.get("automation_paused", current["automation_paused"])) else 0,
            "max_daily_minutes": int(patch.get("max_daily_minutes", current["max_daily_minutes"])),
            "max_challenge_difficulty": int(patch.get("max_challenge_difficulty", current["max_challenge_difficulty"])),
            "allow_auto_order_actions": 1 if bool(patch.get("allow_auto_order_actions", current["allow_auto_order_actions"])) else 0,
            "allow_auto_minimum_viable": 1 if bool(patch.get("allow_auto_minimum_viable", current["allow_auto_minimum_viable"])) else 0,
            "priority_weights": patch.get("priority_weights", current["priority_weights"]),
        }
        with db() as conn:
            conn.execute(
                """
                update user_autonomy_policy
                set active_role = ?, automation_paused = ?, max_daily_minutes = ?,
                    max_challenge_difficulty = ?, allow_auto_order_actions = ?,
                    allow_auto_minimum_viable = ?, priority_weights_json = ?,
                    version = ?, updated_at = ?
                where user_id = ?
                """,
                (
                    updated["active_role"],
                    updated["automation_paused"],
                    updated["max_daily_minutes"],
                    updated["max_challenge_difficulty"],
                    updated["allow_auto_order_actions"],
                    updated["allow_auto_minimum_viable"],
                    json_dump(updated["priority_weights"]),
                    next_version,
                    now,
                    user_id,
                ),
            )
        return self.get_user_autonomy_policy(user_id)

    # --- Phase 1: AI Usage & Deterministic Bypass Tracking ---

    def log_ai_usage(self, payload: dict[str, Any]) -> dict[str, Any]:
        entry_id = resource_id("ai_use")
        now = utc_now()
        with db() as conn:
            conn.execute(
                """
                insert into ai_usage_log
                (id, user_id, usage_type, provider, model, purpose, reason,
                 tokens_or_seconds, estimated_cost_usd, created_at)
                values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    entry_id,
                    payload.get("user_id", "moshe"),
                    payload.get("usage_type", "deterministic_bypass"),
                    payload.get("provider", "compass_deterministic"),
                    payload.get("model", "none"),
                    payload["purpose"],
                    payload.get("reason", "rule_engine_first"),
                    int(payload.get("tokens_or_seconds", 0)),
                    float(payload.get("estimated_cost_usd", 0.0)),
                    now,
                ),
            )
        return {"id": entry_id, "created_at": now}

    def get_ai_usage_summary(self, user_id: str) -> dict[str, Any]:
        with db() as conn:
            rows = conn.execute(
                "select * from ai_usage_log where user_id = ? order by created_at desc limit 100",
                (user_id,),
            ).fetchall()
        llm_calls = [r for r in rows if r["usage_type"] == "llm"]
        speech_calls = [r for r in rows if r["usage_type"] in {"stt", "tts"}]
        deterministic_bypasses = [r for r in rows if r["usage_type"] == "deterministic_bypass"]
        return {
            "user_id": user_id,
            "llm_call_count": len(llm_calls),
            "llm_cost_usd": round(sum(float(r["estimated_cost_usd"]) for r in llm_calls), 4),
            "speech_stt_tts_call_count": len(speech_calls),
            "speech_stt_tts_cost_usd": round(sum(float(r["estimated_cost_usd"]) for r in speech_calls), 4),
            "deterministic_bypass_count": len(deterministic_bypasses),
            "recent_logs": [
                {
                    "id": r["id"],
                    "usage_type": r["usage_type"],
                    "provider": r["provider"],
                    "model": r["model"],
                    "purpose": r["purpose"],
                    "reason": r["reason"],
                    "tokens_or_seconds": int(r["tokens_or_seconds"]),
                    "estimated_cost_usd": float(r["estimated_cost_usd"]),
                    "created_at": r["created_at"],
                }
                for r in rows[:20]
            ],
        }
