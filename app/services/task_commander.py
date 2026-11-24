from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Any

from app.config import get_settings
from app.database import db, json_dump, json_load, resource_id, utc_now
from app.services.http_adapter import get_json, post_json


class TaskCommanderService:
    """
    Native TaskCommander engine running directly under Compass.
    Separates Task templates (`tc_tasks`) from concrete daily executable
    occurrences (`tc_task_instances`) with done/snooze/skip and recurrence generation.
    """

    def create_task(self, payload: dict[str, Any]) -> dict[str, Any]:
        now = utc_now()
        task_id = str(payload.get("task_id") or payload.get("id") or resource_id("tc_task"))
        user_id = str(payload.get("user_id") or "moshe")
        title = str(payload["title"]).strip()
        description = payload.get("description")
        status = str(payload.get("status") or "active")
        priority = str(payload.get("priority") or "normal")
        category = payload.get("category")
        recurrence_rule = payload.get("recurrence_rule")
        task_type = str(payload.get("task_type") or ("recurring" if recurrence_rule else "single"))
        due_at = payload.get("due_at")
        deadline_at = payload.get("deadline_at") or due_at
        estimated_minutes = int(payload.get("estimated_minutes") or 25)
        source = str(payload.get("source") or "compass")
        source_object_id = payload.get("source_object_id")
        source_url = payload.get("source_url")
        metadata = payload.get("metadata") or {}

        with db() as conn:
            conn.execute(
                """
                insert or ignore into tc_tasks
                (id, user_id, title, description, status, priority, category, task_type,
                 due_at, deadline_at, recurrence_rule, estimated_minutes, source,
                 source_object_id, source_url, metadata_json, created_at, updated_at)
                values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    task_id,
                    user_id,
                    title,
                    description,
                    status,
                    priority,
                    category,
                    task_type,
                    due_at,
                    deadline_at,
                    recurrence_rule,
                    estimated_minutes,
                    source,
                    source_object_id,
                    source_url,
                    json_dump(metadata),
                    now,
                    now,
                ),
            )

        occurrence_date = str(payload.get("occurrence_date") or (str(due_at)[:10] if due_at else date.today().isoformat()))
        instance = self._ensure_instance(
            task_id=task_id,
            user_id=user_id,
            occurrence_date=occurrence_date,
            scheduled_at=due_at,
            deadline_at=deadline_at,
        )
        return {
            "connected": True,
            "mode": "in_process_compass",
            "task_id": task_id,
            "instance_id": instance["instance_id"],
            "title": title,
            "task_type": task_type,
            "occurrence_date": occurrence_date,
            "status": "active",
        }

    def _ensure_instance(
        self,
        *,
        task_id: str,
        user_id: str,
        occurrence_date: str,
        scheduled_at: str | None = None,
        deadline_at: str | None = None,
    ) -> dict[str, Any]:
        now = utc_now()
        with db() as conn:
            existing = conn.execute(
                "select * from tc_task_instances where task_id = ? and occurrence_date = ?",
                (task_id, occurrence_date),
            ).fetchone()
            if existing:
                return {"instance_id": existing["id"], "already_existed": True}
            instance_id = resource_id("tc_inst")
            conn.execute(
                """
                insert into tc_task_instances
                (id, task_id, user_id, occurrence_date, scheduled_at, deadline_at, status,
                 completed_at, skipped_at, snoozed_until, alert_count, last_alerted_at, created_at)
                values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    instance_id,
                    task_id,
                    user_id,
                    occurrence_date,
                    scheduled_at,
                    deadline_at,
                    "pending",
                    None,
                    None,
                    None,
                    0,
                    None,
                    now,
                ),
            )
        return {"instance_id": instance_id, "already_existed": False}

    def generate_instances(self, days: int = 2, user_id: str = "moshe", start_date: date | None = None) -> dict[str, Any]:
        anchor = start_date or date.today()
        created_count = 0
        with db() as conn:
            tasks = conn.execute(
                "select * from tc_tasks where user_id = ? and status = 'active' and task_type = 'recurring'",
                (user_id,),
            ).fetchall()

        for task in tasks:
            rule = str(task["recurrence_rule"] or "DAILY").upper()
            hhmm = "09:00"
            if "@" in rule:
                parts = rule.split("@")
                hhmm = parts[-1] if ":" in parts[-1] else "09:00"
            for offset in range(max(1, days)):
                occ_date = (anchor + timedelta(days=offset)).isoformat()
                scheduled = f"{occ_date}T{hhmm}:00+00:00"
                res = self._ensure_instance(
                    task_id=task["id"],
                    user_id=user_id,
                    occurrence_date=occ_date,
                    scheduled_at=scheduled,
                    deadline_at=scheduled,
                )
                if not res["already_existed"]:
                    created_count += 1
        return {"connected": True, "mode": "in_process_compass", "generated_instances": created_count, "days": days}

    def today(self, limit: int = 20, user_id: str = "moshe", target_date: str | None = None) -> dict[str, Any]:
        today_str = target_date or date.today().isoformat()
        now_str = utc_now()
        with db() as conn:
            rows = conn.execute(
                """
                select i.*, t.title, t.description, t.priority, t.category, t.task_type,
                       t.estimated_minutes, t.source, t.recurrence_rule
                from tc_task_instances i
                join tc_tasks t on t.id = i.task_id
                where i.user_id = ?
                  and i.occurrence_date = ?
                  and i.status = 'pending'
                  and (i.snoozed_until is null or i.snoozed_until <= ?)
                order by i.scheduled_at is null, i.scheduled_at asc, i.created_at asc
                limit ?
                """,
                (user_id, today_str, now_str, limit),
            ).fetchall()
        items = [self._instance_row(r) for r in rows]
        return {"connected": True, "mode": "in_process_compass", "date": today_str, "items": items, "count": len(items)}

    def overdue(self, limit: int = 20, user_id: str = "moshe", target_date: str | None = None) -> dict[str, Any]:
        today_str = target_date or date.today().isoformat()
        with db() as conn:
            rows = conn.execute(
                """
                select i.*, t.title, t.description, t.priority, t.category, t.task_type,
                       t.estimated_minutes, t.source, t.recurrence_rule
                from tc_task_instances i
                join tc_tasks t on t.id = i.task_id
                where i.user_id = ?
                  and i.occurrence_date < ?
                  and i.status = 'pending'
                order by i.occurrence_date asc, i.created_at asc
                limit ?
                """,
                (user_id, today_str, limit),
            ).fetchall()
        items = [self._instance_row(r) for r in rows]
        return {"connected": True, "mode": "in_process_compass", "items": items, "count": len(items)}

    def status(self, limit: int = 10, user_id: str = "moshe") -> dict[str, Any]:
        with db() as conn:
            pending = conn.execute(
                "select count(*) as cnt from tc_task_instances where user_id = ? and status = 'pending'",
                (user_id,),
            ).fetchone()["cnt"]
            done = conn.execute(
                "select count(*) as cnt from tc_task_instances where user_id = ? and status = 'done'",
                (user_id,),
            ).fetchone()["cnt"]
            skipped = conn.execute(
                "select count(*) as cnt from tc_task_instances where user_id = ? and status = 'skipped'",
                (user_id,),
            ).fetchone()["cnt"]
        return {
            "connected": True,
            "mode": "in_process_compass",
            "pending_instances": int(pending),
            "done_instances": int(done),
            "skipped_instances": int(skipped),
            "today": self.today(limit=limit, user_id=user_id)["items"],
            "overdue": self.overdue(limit=limit, user_id=user_id)["items"],
        }

    def mark_done(self, instance_id: str) -> dict[str, Any]:
        now = utc_now()
        with db() as conn:
            row = conn.execute("select * from tc_task_instances where id = ?", (instance_id,)).fetchone()
            if not row:
                return {"connected": True, "success": False, "error": "instance_not_found"}
            conn.execute(
                "update tc_task_instances set status = 'done', completed_at = ?, snoozed_until = null where id = ?",
                (now, instance_id),
            )
            task = conn.execute("select * from tc_tasks where id = ?", (row["task_id"],)).fetchone()
        if task and task["task_type"] == "recurring":
            occ = date.fromisoformat(str(row["occurrence_date"])[:10])
            self.generate_instances(days=2, user_id=row["user_id"], start_date=occ + timedelta(days=1))
        return {"connected": True, "mode": "in_process_compass", "success": True, "instance_id": instance_id, "status": "done"}

    def snooze(self, instance_id: str, minutes: int = 60) -> dict[str, Any]:
        until = (datetime.now(timezone.utc) + timedelta(minutes=minutes)).isoformat()
        with db() as conn:
            row = conn.execute("select id from tc_task_instances where id = ?", (instance_id,)).fetchone()
            if not row:
                return {"connected": True, "success": False, "error": "instance_not_found"}
            conn.execute(
                "update tc_task_instances set status = 'pending', snoozed_until = ? where id = ?",
                (until, instance_id),
            )
        return {
            "connected": True,
            "mode": "in_process_compass",
            "success": True,
            "instance_id": instance_id,
            "status": "pending",
            "snoozed_until": until,
        }

    def skip(self, instance_id: str) -> dict[str, Any]:
        now = utc_now()
        with db() as conn:
            row = conn.execute("select id from tc_task_instances where id = ?", (instance_id,)).fetchone()
            if not row:
                return {"connected": True, "success": False, "error": "instance_not_found"}
            conn.execute(
                "update tc_task_instances set status = 'skipped', skipped_at = ? where id = ?",
                (now, instance_id),
            )
        return {
            "connected": True,
            "mode": "in_process_compass",
            "success": True,
            "instance_id": instance_id,
            "status": "skipped",
        }

    def _instance_row(self, row: Any) -> dict[str, Any]:
        return {
            "instance_id": row["id"],
            "id": row["id"],
            "task_id": row["task_id"],
            "user_id": row["user_id"],
            "title": row["title"],
            "description": row["description"],
            "priority": row["priority"],
            "category": row["category"],
            "task_type": row["task_type"],
            "estimated_minutes": int(row["estimated_minutes"]),
            "occurrence_date": row["occurrence_date"],
            "scheduled_at": row["scheduled_at"],
            "deadline_at": row["deadline_at"],
            "status": row["status"],
            "completed_at": row["completed_at"],
            "skipped_at": row["skipped_at"],
            "snoozed_until": row["snoozed_until"],
            "source": row["source"],
        }


class TaskCommanderAdapter:
    """
    Runs TaskCommander natively under Compass by default; falls back to external HTTP only if configured.
    """

    def __init__(self) -> None:
        self.service = TaskCommanderService()

    def health(self) -> dict[str, Any]:
        return {"connected": True, "mode": "in_process_compass", "status": "ok"}

    def status(self, limit: int = 10, user_id: str = "moshe") -> dict[str, Any]:
        return self.service.status(limit=limit, user_id=user_id)

    def today(self, limit: int = 20, user_id: str = "moshe") -> dict[str, Any]:
        return self.service.today(limit=limit, user_id=user_id)

    def overdue(self, limit: int = 20, user_id: str = "moshe") -> dict[str, Any]:
        return self.service.overdue(limit=limit, user_id=user_id)

    def create_task(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self.service.create_task(payload)

    def generate_instances(self, days: int = 2, user_id: str = "moshe") -> dict[str, Any]:
        return self.service.generate_instances(days=days, user_id=user_id)

    def mark_done(self, instance_id: str) -> dict[str, Any]:
        return self.service.mark_done(instance_id)

    def snooze(self, instance_id: str, minutes: int = 60) -> dict[str, Any]:
        return self.service.snooze(instance_id, minutes=minutes)

    def skip(self, instance_id: str) -> dict[str, Any]:
        return self.service.skip(instance_id)
