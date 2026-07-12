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
