from __future__ import annotations

import re
from datetime import date, datetime, timezone
from typing import Any
from uuid import uuid4

from app.database import db, json_dump, json_load, resource_id, utc_now
from app.repository import CompassRepository
from app.services.rules_engine import RulesEngineAdapter

SCHEDULE_STATES = {"planned", "displayed", "in_window", "check_due", "overdue", "closed"}
EXECUTION_OUTCOMES = {
    "unknown",
    "completed",
    "partial",
    "not_done",
    "deferred",
    "cancelled",
    "approved_exception",
}
CONTEXT_MODES = {
    "normal",
    "low_energy",
    "overload",
    "sick",
    "travel",
    "vacation",
    "shabbat",
    "quiet_meeting",
    "focus",
}

ALLOWED_MEDIA_MIME_PREFIXES = {
    "video": ("video/mp4", "video/webm", "video/ogg"),
    "infographic": ("image/png", "image/jpeg", "image/webp", "image/svg+xml", "application/pdf"),
    "image": ("image/png", "image/jpeg", "image/webp", "image/svg+xml"),
    "audio": ("audio/mpeg", "audio/wav", "audio/ogg", "audio/webm", "audio/mp4"),
    "question": ("text/plain", "application/json"),
    "link": ("text/uri-list", "text/html"),
}

SEED_ONBOARDING_QUESTIONS: list[dict[str, Any]] = [
    {
        "code": "ONB-ID-01",
        "category": "identity_values",
        "question_he": "מי תרצה להיות בעוד חמש שנים, ואילו עקרונות לא תקריב בדרך?",
        "importance": 10,
        "is_blocking_infra": 0,
    },
    {
        "code": "ONB-GOAL-01",
        "category": "goals",
        "question_he": "מה ייחשב בעיניך יום מוצלח ומהם יעדי החובה לחצי השנה הקרובה?",
        "importance": 10,
        "is_blocking_infra": 0,
    },
    {
        "code": "ONB-HABIT-01",
        "category": "habits_routine",
        "question_he": "אילו פעילויות בוקר כבר אוטומטיות אצלך (שאינן דורשות מעקב) ומה תרצה לחזק?",
        "importance": 9,
        "is_blocking_infra": 0,
    },
    {
        "code": "ONB-ENERGY-01",
        "category": "energy",
        "question_he": "באילו שעות ביום האנרגיה והריכוז שלך בשיאם, ומתי הכי נוח לך להתאמן?",
        "importance": 9,
        "is_blocking_infra": 0,
    },
    {
        "code": "ONB-COMM-01",
        "category": "communication_media",
        "question_he": "האם אתה מעדיף דיווח בקול או ב-Checkbox, ובאילו שעות אתה בקרבת אנשים ודורש מצב שקט ללא TTS?",
        "importance": 9,
        "is_blocking_infra": 1,
    },
    {
        "code": "ONB-BOUND-01",
        "category": "boundaries_permissions",
        "question_he": "מה אסור למערכת לעשות, מתי אסור להפריע לך, ומהי כמות המשימות היומית הסבירה עבורך?",
        "importance": 10,
        "is_blocking_infra": 1,
    },
]


class UnifiedV6Service:
    """
    Implements Unified Specification v6 (Slices 1A, 1B, 1C, 1D, 1E):
    - Slice 1A: Activity templates & instances with `open_time`, `preferred_time`, `check_time`,
      separated `schedule_state` vs. `execution_outcome` (`unknown` is never failure), append-only
      execution events with linked correction/undo events, 'Stuck' button, one-click approved exception,
      and the daily 11:00 Self Management inquiry task.
    - Slice 1B: Today Screen (Now / Later / Needs Clarification / Completed), Context Modes
      (`Asia/Jerusalem`, Sunday week start, Shabbat, Quiet Meeting), and post-sleep server Catch-up
      without duplicate alerts or artificial failures.
    - Slice 1C: Stable daily voice numbering (`#1`, `#2`, `#3` never recycled on the same day),
      editable local alias/phrase dictionary, ambiguity resolution candidates, and mandatory
      pre-save voice confirmation in POC with quick Undo.
    - Slice 1D: Multimedia as a complete replacement for text (`media_only=True`, server-side MIME
      & size verification, `content_version_id`), Scheduled Messages & TTS Reader form with preview
      and immediate Global Mute (`global_mute_tts`).
    - Slice 1E: Quick Inbox with one-click 'Idea' button (never auto-converted to a task) and
      Compass-owned Progressive Onboarding question engine.
    """

    MAX_MEDIA_SIZE_BYTES = 25 * 1024 * 1024  # 25 MB default configurable limit

    # =========================================================================
    # SLICE 1A: Templates, Instances, State Machine, Append-Only Events & 11:00 Inquiry
    # =========================================================================

    def ensure_self_management_11am_inquiry(self, user_id: str = "moshe") -> dict[str, Any]:
        """
        Section 8: Recurring daily 11:00 inquiry task until completed:
        'האם ביררת מאיפה מגיעים תרגילי הבוקר של Self Management וכיצד ניתן לקבל אותם ישירות לתוך Compass?'
        Non-completion is not a failure. Once completed, closes permanently and stops future instances.
        """
        template_id = f"tpl_sm_inquiry_11am_{user_id}"
        now = utc_now()
        with db() as conn:
            row = conn.execute(
                "select * from v6_activity_templates where template_id = ?",
                (template_id,),
            ).fetchone()
            if not row:
                conn.execute(
                    """
                    insert into v6_activity_templates
                    (template_id, user_id, name, aliases_json, description, open_time,
                     preferred_time, window_end_time, check_time, frequency, content_blocks_json,
                     media_only, completion_condition, evidence_type, estimated_minutes,
                     minimum_viable_version, importance, impact, difficulty, energy_requirement,
                     exception_action, ttl_policy, goal_ids_json, rule_id, is_system_inquiry,
                     max_inquiry_repeats, inquiry_repeats_count, status, created_at, updated_at)
                    values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        template_id,
                        user_id,
                        "בירור מקור תרגילי הבוקר של Self Management",
                        json_dump(["בירור תרגילי בוקר", "בירור self management", "משימת בירור 11"]),
                        "האם ביררת מאיפה מגיעים תרגילי הבוקר של Self Management וכיצד ניתן לקבל אותם ישירות לתוך Compass?",
                        "11:00",
                        "11:00",
                        "18:00",
                        "11:00",
                        "daily",
                        json_dump(
                            [
                                {
                                    "block_type": "question",
                                    "text": "האם ביררת מאיפה מגיעים תרגילי הבוקר של Self Management וכיצד ניתן לקבל אותם ישירות לתוך Compass?",
                                }
                            ]
                        ),
                        0,
                        "תשובת משתמש מאושרת על מקור תרגילי הבוקר",
                        "user_answer",
                        10,
                        "בדיקה של 2 דקות מול הגדרות הטלגרם/Self Manage",
                        8,
                        8,
                        3,
                        3,
                        "ask_continue_defer_or_close",
                        "open_inquiry_by_importance",
                        json_dump([]),
                        None,
                        1,
                        7,
                        0,
                        "active",
                        now,
                        now,
                    ),
                )
                row = conn.execute(
                    "select * from v6_activity_templates where template_id = ?",
                    (template_id,),
                ).fetchone()
        return self._template_row(row)

    def create_activity_template(self, payload: dict[str, Any]) -> dict[str, Any]:
        user_id = str(payload.get("user_id") or "moshe")
        now = utc_now()
        template_id = str(payload.get("template_id") or resource_id("v6_tpl"))
        content_blocks = list(payload.get("content_blocks") or [])
        media_only = bool(payload.get("media_only", False))
        name = str(payload.get("name") or "").strip()
        if not name and media_only and content_blocks:
            first_block = content_blocks[0]
            name = str(first_block.get("title") or f"פעילות מדיה ({first_block.get('block_type', 'media')})")
        if not name:
            raise ValueError("Activity template requires a name or a media_only content block")

        aliases = [str(a).strip() for a in (payload.get("aliases") or []) if str(a).strip()]
        open_time = str(payload.get("open_time") or "06:00")
        preferred_time = str(payload.get("preferred_time") or "09:00")
        window_end_time = str(payload.get("window_end_time") or "21:00")
        check_time = str(payload.get("check_time") or "18:00")

        with db() as conn:
            conn.execute(
                """
                insert into v6_activity_templates
                (template_id, user_id, name, aliases_json, description, open_time,
                 preferred_time, window_end_time, check_time, frequency, content_blocks_json,
                 media_only, completion_condition, evidence_type, estimated_minutes,
                 minimum_viable_version, importance, impact, difficulty, energy_requirement,
                 exception_action, ttl_policy, goal_ids_json, rule_id, is_system_inquiry,
                 max_inquiry_repeats, inquiry_repeats_count, status, created_at, updated_at)
                values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    template_id,
                    user_id,
                    name,
                    json_dump(aliases),
                    str(payload.get("description") or ""),
                    open_time,
                    preferred_time,
                    window_end_time,
                    check_time,
                    str(payload.get("frequency") or "daily"),
                    json_dump(content_blocks),
                    1 if media_only else 0,
                    str(payload.get("completion_condition") or "דיווח עצמי או סימון השלמה"),
                    str(payload.get("evidence_type") or "self_report"),
                    int(payload.get("estimated_minutes", 20)),
                    str(payload.get("minimum_viable_version") or "2 דקות צעד ראשון קטן"),
                    int(payload.get("importance", 7)),
                    int(payload.get("impact", 7)),
                    int(payload.get("difficulty", 5)),
                    int(payload.get("energy_requirement", 3)),
                    str(payload.get("exception_action") or "offer_completion_or_clarify"),
                    str(payload.get("ttl_policy") or "close_daily_without_debt"),
                    json_dump(payload.get("goal_ids") or []),
                    payload.get("rule_id"),
                    1 if bool(payload.get("is_system_inquiry", False)) else 0,
                    int(payload.get("max_inquiry_repeats", 7)),
                    0,
                    "active",
                    now,
                    now,
                ),
            )

        # Register aliases in the local voice dictionary
        for alias in aliases:
            self.add_voice_phrase(
                user_id=user_id,
                phrase=alias,
                target_type="template",
                target_id=template_id,
                target_name=name,
                approved_by_user=True,
            )

        tpl = self.get_activity_template(template_id)
        if payload.get("instantiate_for_today", True):
            inst = self.ensure_daily_instance_for_template(
                tpl,
                target_date=str(payload.get("instance_date") or date.today().isoformat()),
                current_time=str(payload.get("current_time") or "08:00"),
            )
            return {"success": True, "template": tpl, "today_instance": inst}
        return {"success": True, "template": tpl}

    def get_activity_template(self, template_id: str) -> dict[str, Any] | None:
        with db() as conn:
            row = conn.execute("select * from v6_activity_templates where template_id = ?", (template_id,)).fetchone()
        return self._template_row(row) if row else None

    def list_activity_templates(self, user_id: str = "moshe", status: str = "active") -> list[dict[str, Any]]:
        self.ensure_self_management_11am_inquiry(user_id=user_id)
        with db() as conn:
            if status == "all":
                rows = conn.execute(
                    "select * from v6_activity_templates where user_id = ? order by open_time asc, importance desc",
                    (user_id,),
                ).fetchall()
            else:
                rows = conn.execute(
                    "select * from v6_activity_templates where user_id = ? and status = ? order by open_time asc, importance desc",
                    (user_id, status),
                ).fetchall()
        return [self._template_row(r) for r in rows]

    def ensure_daily_instance_for_template(
        self,
        template: dict[str, Any],
        *,
        target_date: str | None = None,
        current_time: str = "08:00",
    ) -> dict[str, Any]:
        day_str = target_date or date.today().isoformat()
        user_id = template["user_id"]
        with db() as conn:
            existing = conn.execute(
                "select * from v6_activity_instances where user_id = ? and template_id = ? and instance_date = ?",
                (user_id, template["template_id"], day_str),
            ).fetchone()
            if existing:
                return self._instance_row(existing)

            # Stable daily voice number: never recycle a number on the same day!
            max_row = conn.execute(
                "select coalesce(max(daily_voice_number), 0) as max_num from v6_activity_instances where user_id = ? and instance_date = ?",
                (user_id, day_str),
            ).fetchone()
            next_voice_number = int(max_row["max_num"]) + 1

            instance_id = resource_id("v6_inst")
            now = utc_now()
            schedule_state = self._compute_schedule_state(
                open_time=template["open_time"],
                preferred_time=template["preferred_time"],
                check_time=template["check_time"],
                current_time=current_time,
                execution_outcome="unknown",
            )
            content_version_id = f"cver_{template['template_id']}_v1"
            conn.execute(
                """
                insert into v6_activity_instances
                (instance_id, template_id, user_id, instance_date, daily_voice_number,
                 name, aliases_json, open_time, preferred_time, window_end_time, check_time,
                 schedule_state, execution_outcome, partial_value, partial_unit,
                 partial_target, partial_note, used_minimum_version, alternative_performed,
                 deferred_until, defer_count, content_blocks_json, content_version_id,
                 media_only, ttl_policy, reported_execution_at, received_at, report_source,
                 entity_version, created_at, updated_at)
                values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    instance_id,
                    template["template_id"],
                    user_id,
                    day_str,
                    next_voice_number,
                    template["name"],
                    json_dump(template["aliases"]),
                    template["open_time"],
                    template["preferred_time"],
                    template["window_end_time"],
                    template["check_time"],
                    schedule_state,
                    "unknown",
                    None,
                    None,
                    None,
                    None,
                    0,
                    None,
                    None,
                    0,
                    json_dump(template["content_blocks"]),
                    content_version_id,
                    1 if template["media_only"] else 0,
                    template["ttl_policy"],
                    None,
                    None,
                    None,
                    1,
                    now,
                    now,
                ),
            )
            row = conn.execute("select * from v6_activity_instances where instance_id = ?", (instance_id,)).fetchone()
        return self._instance_row(row)

    def _compute_schedule_state(
        self,
        *,
        open_time: str,
        preferred_time: str,
        check_time: str,
        current_time: str,
        execution_outcome: str,
    ) -> str:
        if execution_outcome in {"completed", "cancelled", "approved_exception"}:
            return "closed"
        if current_time < open_time:
            return "planned"
        if current_time < preferred_time:
            return "displayed"
        if current_time < check_time:
            return "in_window"
        if current_time == check_time:
            return "check_due"
        return "overdue"

    def get_instance(self, instance_id: str) -> dict[str, Any] | None:
        with db() as conn:
            row = conn.execute("select * from v6_activity_instances where instance_id = ?", (instance_id,)).fetchone()
        return self._instance_row(row) if row else None

    def report_instance_execution(
        self,
        instance_id: str,
        *,
        user_id: str = "moshe",
        outcome: str = "completed",
        source: str = "checkbox_web",
        reported_execution_at: str | None = None,
        partial_value: float | None = None,
        partial_unit: str | None = None,
        partial_target: float | None = None,
        partial_note: str | None = None,
        used_minimum_version: bool = False,
        alternative_performed: str | None = None,
        deferred_until: str | None = None,
        expected_entity_version: int | None = None,
        action_idempotency_key: str | None = None,
        linked_event_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Section 3 & Section 7:
        - Updates execution_outcome (`unknown`, `completed`, `partial`, `not_done`, `deferred`, `cancelled`, `approved_exception`).
        - Stores reported_execution_at separately from received_at (supports late reporting & correction events).
        - Writes an append-only event to `v6_execution_events` without overwriting history.
        - Checks conflict if `expected_entity_version` is provided and mismatches current `entity_version`.
        - If this instance belongs to the 11:00 Self Management inquiry and outcome == 'completed', closes the template permanently!
        """
        if outcome not in EXECUTION_OUTCOMES:
            raise ValueError(f"outcome must be one of {sorted(EXECUTION_OUTCOMES)}")

        inst = self.get_instance(instance_id)
        if not inst:
            return {"success": False, "error": "instance_not_found"}
        if inst["user_id"] != user_id:
            return {"success": False, "error": "unauthorized_user_isolation"}

        idem_key = action_idempotency_key or f"act_{instance_id}_{outcome}_{uuid4().hex[:8]}"
        with db() as conn:
            dup_evt = conn.execute(
                "select * from v6_execution_events where action_idempotency_key = ?",
                (idem_key,),
            ).fetchone()
            if dup_evt:
                return {
                    "success": True,
                    "already_processed": True,
                    "event_id": dup_evt["event_id"],
                    "instance": self.get_instance(instance_id),
                }

        if expected_entity_version is not None and int(expected_entity_version) != int(inst["entity_version"]):
            return {
                "success": False,
                "status": "version_conflict",
                "message_he": "זוהה שינוי סותר ממכשיר אחר. המערכת אינה דורסת שינוי בשקט – אנא רענן ובחר איזו גרסה לשמור.",
                "server_entity_version": inst["entity_version"],
                "client_expected_version": expected_entity_version,
                "server_instance": inst,
            }

        now = utc_now()
        exec_at = reported_execution_at or now
        is_late_report = reported_execution_at is not None and reported_execution_at < now

        # If an alternative was performed, check if it satisfies the rule or requires exception approval
        final_outcome = outcome
        alternative_note = None
        if alternative_performed:
            tpl = self.get_activity_template(inst["template_id"])
            cond_text = (tpl["completion_condition"] if tpl else "").lower()
            if alternative_performed.lower() in cond_text or "חלופה" in cond_text:
                final_outcome = "completed"
                alternative_note = f"בוצעה חלופה העומדת בתנאי הכלל: {alternative_performed}"
            else:
                # Section 3: Do not automatically mark success for an unapproved alternative
                final_outcome = "partial" if outcome == "completed" else outcome
                alternative_note = f"בוצעה חלופה ('{alternative_performed}') שאינה זהה ליעד המלא – נשמרה כביצוע חלקי/חלופי לבחינת חריג מאושר."

        new_schedule_state = (
            "closed"
            if final_outcome in {"completed", "cancelled", "approved_exception"}
            else ("planned" if final_outcome == "deferred" else inst["schedule_state"])
        )
        new_defer_count = inst["defer_count"] + (1 if final_outcome == "deferred" else 0)
        next_version = inst["entity_version"] + 1
        event_id = resource_id("v6_evt")
        event_type = "execution.late_correction" if (is_late_report or linked_event_id) else f"execution.{final_outcome}"

        with db() as conn:
            conn.execute(
                """
                update v6_activity_instances
                set schedule_state = ?,
                    execution_outcome = ?,
                    partial_value = ?,
                    partial_unit = ?,
                    partial_target = ?,
                    partial_note = ?,
                    used_minimum_version = ?,
                    alternative_performed = ?,
                    deferred_until = ?,
                    defer_count = ?,
                    reported_execution_at = ?,
                    received_at = ?,
                    report_source = ?,
                    entity_version = ?,
                    updated_at = ?
                where instance_id = ? and user_id = ?
                """,
                (
                    new_schedule_state,
                    final_outcome,
                    partial_value,
                    partial_unit,
                    partial_target,
                    partial_note or alternative_note,
                    1 if used_minimum_version else 0,
                    alternative_performed,
                    deferred_until,
                    new_defer_count,
                    exec_at,
                    now,
                    source,
                    next_version,
                    now,
                    instance_id,
                    user_id,
                ),
            )

            # Append-only execution event
            conn.execute(
                """
                insert into v6_execution_events
                (event_id, user_id, event_type, source, entity_type, entity_id,
                 linked_event_id, occurred_at, received_at, outcome, payload_json,
                 action_idempotency_key)
                values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event_id,
                    user_id,
                    event_type,
                    source,
                    "activity_instance",
                    instance_id,
                    linked_event_id,
                    exec_at,
                    now,
                    final_outcome,
                    json_dump(
                        {
                            "previous_outcome": inst["execution_outcome"],
                            "new_outcome": final_outcome,
                            "used_minimum_version": used_minimum_version,
                            "alternative_performed": alternative_performed,
                            "partial_value": partial_value,
                            "partial_unit": partial_unit,
                            "deferred_until": deferred_until,
                            "entity_version": next_version,
                        }
                    ),
                    idem_key,
                ),
            )

            # Section 8: If the 11:00 Self Management inquiry task is completed, close the template permanently!
            tpl = self.get_activity_template(inst["template_id"])
            if tpl and tpl["is_system_inquiry"] and final_outcome == "completed":
                conn.execute(
                    "update v6_activity_templates set status = 'completed_closed', updated_at = ? where template_id = ?",
                    (now, tpl["template_id"]),
                )

        updated_inst = self.get_instance(instance_id)
        friction_detected = updated_inst["defer_count"] >= 3
        return {
            "success": True,
            "event_id": event_id,
            "event_type": event_type,
            "instance": updated_inst,
            "alternative_note_he": alternative_note,
            "friction_detected": friction_detected,
            "friction_prompt_he": (
                f"המשימה '{updated_inst['name']}' נדחתה {updated_inst['defer_count']} פעמים. האם תרצה לפרק אותה לצעד ראשון קטן או לעבור לגרסת מינימום?"
                if friction_detected
                else None
            ),
            "undo_available": True,
        }

    def undo_last_instance_report(self, instance_id: str, *, user_id: str = "moshe", source: str = "undo_button") -> dict[str, Any]:
        """
        Section 3 & Section 7:
        Cancels/undoes the last execution report via a linked append-only event (never deletes history).
        """
        with db() as conn:
            last_evt = conn.execute(
                """
                select * from v6_execution_events
                where user_id = ? and entity_id = ?
                order by received_at desc
                limit 1
                """,
                (user_id, instance_id),
            ).fetchone()
        if not last_evt:
            return {"success": False, "error": "no_event_to_undo"}

        payload = json_load(last_evt["payload_json"], {})
        prev_outcome = str(payload.get("previous_outcome") or "unknown")
        return self.report_instance_execution(
            instance_id,
            user_id=user_id,
            outcome=prev_outcome,
            source=source,
            linked_event_id=last_evt["event_id"],
        )

    def get_stuck_assistance(self, instance_id: str, *, user_id: str = "moshe") -> dict[str, Any]:
        """
        Section 3 & Section 17:
        'כפתור נתקעתי' — offers a small first step, breakdown, or minimum viable version without changing the plan automatically.
        """
        inst = self.get_instance(instance_id)
        if not inst:
            return {"success": False, "error": "instance_not_found"}
        tpl = self.get_activity_template(inst["template_id"])
        min_ver = tpl["minimum_viable_version"] if tpl else "2 דקות של צעד ראשון בלבד"
        return {
            "success": True,
            "instance_id": instance_id,
            "name": inst["name"],
            "plan_changed_automatically": False,
            "suggestions": [
                {
                    "option_id": "first_micro_step",
                    "title_he": "צעד ראשון קטן של 2 דקות",
                    "description_he": f"פתח רק את החומר או התחל ל-120 שניות בלבד במשימה '{inst['name']}' בלי מחויבות להמשיך.",
                },
                {
                    "option_id": "minimum_viable_version",
                    "title_he": "מעבר לגרסת מינימום מאושרת",
                    "description_he": min_ver,
                },
                {
                    "option_id": "approved_exception_or_defer",
                    "title_he": "דחייה מכוונת או חריג מאושר",
                    "description_he": "סמן דחייה לשעה מאוחרת יותר או חריג מאושר להיום ללא אשמה.",
                },
            ],
        }

    def evaluate_daily_activity_rule_at_check_time(
        self,
        instance_id: str,
        *,
        user_id: str = "moshe",
        check_time: str = "18:00",
    ) -> dict[str, Any]:
        """
        Section 6 & Section 19 POC Table:
        Example: Daily Physical Activity checked at 18:00:
        - If `completed` -> no unnecessary alert (`alert_needed=False`, `action="none"`).
        - If `not_done` -> alert and offer completion before end of day (`action="offer_completion"`).
        - If `unknown` (no report yet) -> ask a clarification question (`action="ask_clarification"`, NEVER declare failure!).
        - Supports `partial` and `approved_exception`.
        """
        inst = self.get_instance(instance_id)
        if not inst:
            return {"success": False, "error": "instance_not_found"}

        outcome = inst["execution_outcome"]
        context_state = self.get_context_mode(user_id=user_id)
        is_quiet = context_state["active_mode"] in {"quiet_meeting", "shabbat"} or context_state["global_mute_tts"]

        if outcome in {"completed", "approved_exception"}:
            return {
                "success": True,
                "instance_id": instance_id,
                "check_time": check_time,
                "execution_outcome": outcome,
                "alert_sent": False,
                "action": "none",
                "message_he": "הפעילות כבר הושלמה (או אושר חריג) לפני מועד הבדיקה – לא נשלחה התראה מיותרת.",
            }

        if outcome == "unknown":
            return {
                "success": True,
                "instance_id": instance_id,
                "check_time": check_time,
                "execution_outcome": "unknown",
                "declared_failure": False,
                "alert_sent": True,
                "delivery_channel": "quiet_inbox_badge" if is_quiet else "visual_prompt",
                "action": "ask_clarification",
                "question_he": f"השעה {check_time}: עדיין אין דיווח על '{inst['name']}'. האם הפעילות בוצעה, בוצעה חלקית, או שתרצה לתזמן השלמה קצרה להערב?",
            }

        if outcome == "partial":
            return {
                "success": True,
                "instance_id": instance_id,
                "check_time": check_time,
                "execution_outcome": "partial",
                "declared_failure": False,
                "alert_sent": True,
                "delivery_channel": "quiet_inbox_badge" if is_quiet else "visual_prompt",
                "action": "acknowledge_partial_or_complete",
                "message_he": f"תועד ביצוע חלקי של '{inst['name']}'. כל הכבוד על ההתקדמות! תרצה להוסיף השלמה קצרה או לסגור להיום?",
            }

        # outcome in {"not_done", "deferred"}
        tpl = self.get_activity_template(inst["template_id"])
        min_ver = tpl["minimum_viable_version"] if tpl else "10 דקות השלמה קצרה"
        return {
            "success": True,
            "instance_id": instance_id,
            "check_time": check_time,
            "execution_outcome": outcome,
            "declared_failure": False,
            "alert_sent": True,
            "delivery_channel": "quiet_inbox_badge" if is_quiet else "visual_notification",
            "action": "offer_completion",
            "suggested_completion_window": "19:30–20:00",
            "suggested_minimum_viable_version": min_ver,
            "message_he": f"'{inst['name']}' טרם בוצעה היום. מוצע חלון השלמה ב-19:30 או ביצוע גרסת מינימום ({min_ver}).",
        }

    # =========================================================================
    # SLICE 1B: Today Screen (Now / Later / Needs Clarification / Completed), Context Mode & Sleep Catch-Up
    # =========================================================================

    def get_today_screen(
        self,
        *,
        user_id: str = "moshe",
        target_date: str | None = None,
        current_time: str = "09:30",
    ) -> dict[str, Any]:
        """
        Section 17:
        Today Screen divided into 4 clear sections:
        1. `now`: open_time <= current_time < check_time and outcome == 'unknown'
        2. `later`: open_time > current_time or outcome == 'deferred'
        3. `needs_clarification_or_completion`: current_time >= check_time and outcome in {'unknown', 'not_done', 'partial'}
        4. `completed`: outcome in {'completed', 'approved_exception'}
        """
        day_str = target_date or date.today().isoformat()
        templates = self.list_activity_templates(user_id=user_id, status="active")
        for tpl in templates:
            self.ensure_daily_instance_for_template(tpl, target_date=day_str, current_time=current_time)

        with db() as conn:
            rows = conn.execute(
                "select * from v6_activity_instances where user_id = ? and instance_date = ? order by daily_voice_number asc",
                (user_id, day_str),
            ).fetchall()

        now_bucket: list[dict[str, Any]] = []
        later_bucket: list[dict[str, Any]] = []
        clarify_bucket: list[dict[str, Any]] = []
        completed_bucket: list[dict[str, Any]] = []

        for r in rows:
            inst = self._instance_row(r)
            computed_state = self._compute_schedule_state(
                open_time=inst["open_time"],
                preferred_time=inst["preferred_time"],
                check_time=inst["check_time"],
                current_time=current_time,
                execution_outcome=inst["execution_outcome"],
            )
            inst["schedule_state"] = computed_state

            if inst["execution_outcome"] in {"completed", "approved_exception"}:
                completed_bucket.append(inst)
            elif inst["execution_outcome"] == "deferred" or current_time < inst["open_time"]:
                later_bucket.append(inst)
            elif current_time >= inst["check_time"]:
                clarify_bucket.append(inst)
            else:
                now_bucket.append(inst)

        context_mode = self.get_context_mode(user_id=user_id)
        return {
            "success": True,
            "user_id": user_id,
            "date": day_str,
            "current_time": current_time,
            "context_mode": context_mode,
            "sections": {
                "now": now_bucket,
                "later": later_bucket,
                "needs_clarification_or_completion": clarify_bucket,
                "completed": completed_bucket,
            },
            "all_instances": [self._instance_row(r) for r in rows],
        }

    def get_context_mode(self, user_id: str = "moshe") -> dict[str, Any]:
        now = utc_now()
        with db() as conn:
            row = conn.execute("select * from v6_context_mode_state where user_id = ?", (user_id,)).fetchone()
            if not row:
                conn.execute(
                    """
                    insert into v6_context_mode_state
                    (user_id, active_mode, global_mute_tts, quiet_hours_start, quiet_hours_end,
                     max_concurrent_prompts, active_prompts_count, timezone, week_starts_on,
                     server_sleep_start, server_sleep_end, last_active_heartbeat_at, last_catchup_at, updated_at)
                    values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        user_id,
                        "normal",
                        0,
                        "22:30",
                        "06:30",
                        3,
                        0,
                        "Asia/Jerusalem",
                        "Sunday",
                        "00:00",
                        "06:00",
                        now,
                        None,
                        now,
                    ),
                )
                row = conn.execute("select * from v6_context_mode_state where user_id = ?", (user_id,)).fetchone()
        return self._context_mode_row(row)

    def update_context_mode(self, user_id: str, patch: dict[str, Any]) -> dict[str, Any]:
        current = self.get_context_mode(user_id)
        mode = str(patch.get("active_mode", current["active_mode"]))
        if mode not in CONTEXT_MODES:
            raise ValueError(f"active_mode must be one of {sorted(CONTEXT_MODES)}")
        mute = 1 if bool(patch.get("global_mute_tts", current["global_mute_tts"])) else 0
        if mode in {"quiet_meeting", "shabbat"}:
            mute = 1
        now = utc_now()
        with db() as conn:
            conn.execute(
                """
                update v6_context_mode_state
                set active_mode = ?,
                    global_mute_tts = ?,
                    quiet_hours_start = ?,
                    quiet_hours_end = ?,
                    max_concurrent_prompts = ?,
                    server_sleep_start = ?,
                    server_sleep_end = ?,
                    updated_at = ?
                where user_id = ?
                """,
                (
                    mode,
                    mute,
                    str(patch.get("quiet_hours_start", current["quiet_hours_start"])),
                    str(patch.get("quiet_hours_end", current["quiet_hours_end"])),
                    int(patch.get("max_concurrent_prompts", current["max_concurrent_prompts"])),
                    str(patch.get("server_sleep_start", current["server_sleep_start"])),
                    str(patch.get("server_sleep_end", current["server_sleep_end"])),
                    now,
                    user_id,
                ),
            )
        return self.get_context_mode(user_id)

    def run_post_sleep_catchup(
        self,
        *,
        user_id: str = "moshe",
        target_date: str | None = None,
        wake_time: str = "06:15",
    ) -> dict[str, Any]:
        """
        Section 16 & Section 19 POC Table ('שינה בזמן בדיקה'):
        After server wakes from sleep (e.g. 00:00–06:00), checks missed activities and
        surfaces only relevant items without duplicate alerts or artificial failure marking.
        Also applies TTL policy to close previous day's casual daily instances without rolling over debt.
        """
        day_str = target_date or date.today().isoformat()
        now = utc_now()
        context = self.get_context_mode(user_id)
        today_view = self.get_today_screen(user_id=user_id, target_date=day_str, current_time=wake_time)

        surfaced_items: list[dict[str, Any]] = []
        for inst in today_view["all_instances"]:
            if inst["open_time"] <= wake_time and inst["execution_outcome"] == "unknown":
                surfaced_items.append(
                    {
                        "instance_id": inst["instance_id"],
                        "daily_voice_number": inst["daily_voice_number"],
                        "name": inst["name"],
                        "open_time": inst["open_time"],
                        "status": "recovered_after_sleep",
                        "marked_as_failed": False,
                    }
                )

        # Close expired previous-day instances according to TTL policy without creating debt
        closed_expired_count = 0
        with db() as conn:
            old_rows = conn.execute(
                """
                select * from v6_activity_instances
                where user_id = ? and instance_date < ? and schedule_state != 'closed'
                """,
                (user_id, day_str),
            ).fetchall()
            for old in old_rows:
                ttl = old["ttl_policy"]
                if ttl in {"close_daily_without_debt", "casual_article_to_archive"}:
                    conn.execute(
                        "update v6_activity_instances set schedule_state = 'closed', updated_at = ? where instance_id = ?",
                        (now, old["instance_id"]),
                    )
                    closed_expired_count += 1

            conn.execute(
                "update v6_context_mode_state set last_catchup_at = ?, last_active_heartbeat_at = ?, updated_at = ? where user_id = ?",
                (now, now, now, user_id),
            )

        return {
            "success": True,
            "user_id": user_id,
            "wake_time": wake_time,
            "server_sleep_window": f"{context['server_sleep_start']}–{context['server_sleep_end']}",
            "recovered_relevant_count": len(surfaced_items),
            "recovered_items": surfaced_items,
            "closed_previous_day_without_debt_count": closed_expired_count,
            "duplicate_alerts_sent": 0,
            "artificial_failures_created": 0,
        }

    # =========================================================================
    # SLICE 1C: Hebrew Voice Reporting, Stable Numbering, Aliases & Mandatory Pre-Save Confirmation
    # =========================================================================

    def add_voice_phrase(
        self,
        *,
        user_id: str = "moshe",
        phrase: str,
        target_type: str,
        target_id: str,
        target_name: str,
        approved_by_user: bool = True,
    ) -> dict[str, Any]:
        phrase_id = resource_id("v6_phr")
        now = utc_now()
        with db() as conn:
            conn.execute(
                """
                insert into v6_voice_phrase_dictionary
                (phrase_id, user_id, phrase, target_type, target_id, target_name, approved_by_user, created_at)
                values (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    phrase_id,
                    user_id,
                    phrase.strip().lower(),
                    target_type,
                    target_id,
                    target_name,
                    1 if approved_by_user else 0,
                    now,
                ),
            )
        return {
            "phrase_id": phrase_id,
            "phrase": phrase.strip(),
            "target_id": target_id,
            "target_name": target_name,
        }

    def list_voice_phrases(self, user_id: str = "moshe") -> list[dict[str, Any]]:
        with db() as conn:
            rows = conn.execute(
                "select * from v6_voice_phrase_dictionary where user_id = ? order by created_at desc",
                (user_id,),
            ).fetchall()
        return [
            {
                "phrase_id": r["phrase_id"],
                "phrase": r["phrase"],
                "target_type": r["target_type"],
                "target_id": r["target_id"],
                "target_name": r["target_name"],
                "approved_by_user": bool(r["approved_by_user"]),
            }
            for r in rows
        ]

    def interpret_voice_task_command(
        self,
        *,
        user_id: str = "moshe",
        transcript: str,
        target_date: str | None = None,
        source_device: str = "web_mic",
    ) -> dict[str, Any]:
        """
        Section 3 & Section 19 POC Table:
        - Deterministic recognition by task name, stable daily voice number ('ביצעתי משימה 3' / 'משימה שלוש'), or alias.
        - Supports voice undo command ('בטל דיווח אחרון' / 'ביטול').
        - When ambiguous (multiple candidate tasks match), returns `status="ambiguous_requires_choice"` with candidate buttons.
        - In POC, every state-changing voice command requires explicit confirmation before saving (`status="pending_confirmation"`).
        """
        day_str = target_date or date.today().isoformat()
        clean = transcript.strip()
        lowered = clean.lower()

        with db() as conn:
            rows = conn.execute(
                "select * from v6_activity_instances where user_id = ? and instance_date = ? order by daily_voice_number asc",
                (user_id, day_str),
            ).fetchall()
        instances = [self._instance_row(r) for r in rows]

        # 1. Check for voice undo command
        if any(w in lowered for w in ("בטל דיווח", "בטל פעולה", "ביטול דיווח", "undo")):
            with db() as conn:
                last_evt = conn.execute(
                    "select * from v6_execution_events where user_id = ? order by received_at desc limit 1",
                    (user_id,),
                ).fetchone()
            if last_evt:
                undone = self.undo_last_instance_report(last_evt["entity_id"], user_id=user_id, source=f"voice_undo:{source_device}")
                return {
                    "success": True,
                    "status": "undone",
                    "intent": "undo_last_report",
                    "undone_result": undone,
                    "message_he": "הדיווח האחרון בוטל בהצלחה בפקודה קולית.",
                }

        # 2. Determine proposed outcome
        proposed_outcome = "completed"
        if any(w in lowered for w in ("חלקית", "חלקי", "partial")):
            proposed_outcome = "partial"
        elif any(w in lowered for w in ("דחה", "נדחה", "מאוחר יותר", "defer")):
            proposed_outcome = "deferred"
        elif any(w in lowered for w in ("לא ביצעתי", "לא בוצע", "not done")):
            proposed_outcome = "not_done"

        # 3. Check stable daily voice number ('משימה 3', 'משימה שלוש', etc.)
        hebrew_num_map = {
            "אחת": 1,
            "אחד": 1,
            "שתיים": 2,
            "שניים": 2,
            "שלוש": 3,
            "שלושה": 3,
            "ארבע": 4,
            "ארבעה": 4,
            "חמש": 5,
            "חמישה": 5,
            "שש": 6,
            "שבע": 7,
            "שמונה": 8,
            "תשע": 9,
            "עשר": 10,
        }
        matched_by_number: list[dict[str, Any]] = []
        digit_match = re.search(r"משימה\s*(\d+)", lowered)
        target_num = int(digit_match.group(1)) if digit_match else None
        if target_num is None:
            for word, num in hebrew_num_map.items():
                if f"משימה {word}" in lowered or f"מספר {word}" in lowered:
                    target_num = num
                    break
        if target_num is not None:
            for inst in instances:
                if inst["daily_voice_number"] == target_num:
                    matched_by_number.append(inst)

        # 4. If not matched by number, match by exact/substring name, aliases, or local dictionary
        candidates: list[dict[str, Any]] = list(matched_by_number)
        if not candidates:
            dict_phrases = self.list_voice_phrases(user_id=user_id)
            stripped_cmd = re.sub(
                r"^(סיימתי את|סיימתי|ביצעתי את|ביצעתי|השלמתי את|השלמתי|דווח על)\s*",
                "",
                lowered,
            ).strip()

            for inst in instances:
                inst_name_low = inst["name"].lower()
                inst_aliases_low = [a.lower() for a in inst["aliases"]]
                if (
                    (stripped_cmd and stripped_cmd in inst_name_low)
                    or inst_name_low in lowered
                    or any(a in lowered or (stripped_cmd and stripped_cmd in a) for a in inst_aliases_low)
                ):
                    candidates.append(inst)
                    continue
                for dp in dict_phrases:
                    if dp["target_id"] == inst["template_id"] and dp["phrase"] in lowered:
                        candidates.append(inst)
                        break

        command_id = resource_id("v6_vcmd")
        now = utc_now()

        if len(candidates) == 1:
            chosen = candidates[0]
            status = "pending_confirmation"
            matched_id = chosen["instance_id"]
            msg_he = (
                f"זוהתה משימה #{chosen['daily_voice_number']} ('{chosen['name']}') לסימון כ-'{proposed_outcome}'. "
                "ב-POC נדרש אישור מפורש לפני שמירה – לחץ 'אשר שמירה קולית' או 'בטל'."
            )
        elif len(candidates) > 1:
            status = "ambiguous_requires_choice"
            matched_id = None
            names_str = ", ".join(f"#{c['daily_voice_number']} {c['name']}" for c in candidates)
            msg_he = f"זיהוי קולי עמום – נמצאו מספר משימות תואמות ({names_str}). אנא בחר את המשימה הרצויה לאישור או בטל."
        else:
            status = "no_match_requires_clarification"
            matched_id = None
            msg_he = "לא נמצאה משימה תואמת לפקודה הקולית. ניתן לבחור מתוך רשימת משימות היום או ללמד כינוי חדש."

        with db() as conn:
            conn.execute(
                """
                insert into v6_pending_voice_commands
                (command_id, user_id, raw_transcript, detected_intent, status,
                 matched_instance_id, candidate_instances_json, proposed_outcome,
                 source_device, created_at, confirmed_at)
                values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    command_id,
                    user_id,
                    clean,
                    "report_task_execution",
                    status,
                    matched_id,
                    json_dump(candidates),
                    proposed_outcome,
                    source_device,
                    now,
                    None,
                ),
            )

        return {
            "success": True,
            "command_id": command_id,
            "raw_transcript": clean,
            "status": status,
            "requires_explicit_confirmation": True,
            "proposed_outcome": proposed_outcome,
            "matched_instance": candidates[0] if len(candidates) == 1 else None,
            "candidates": candidates,
            "message_he": msg_he,
        }

    def confirm_voice_task_command(
        self,
        command_id: str,
        *,
        user_id: str = "moshe",
        selected_instance_id: str | None = None,
        learn_phrase_on_confirm: bool = False,
    ) -> dict[str, Any]:
        """
        Section 3 & Section 26:
        Confirms a pending or disambiguated voice command, executes the state change,
        and optionally learns the user's phrase into the local dictionary.
        """
        with db() as conn:
            row = conn.execute(
                "select * from v6_pending_voice_commands where command_id = ? and user_id = ?",
                (command_id, user_id),
            ).fetchone()
        if not row:
            return {"success": False, "error": "voice_command_not_found"}

        target_instance_id = selected_instance_id or row["matched_instance_id"]
        if not target_instance_id:
            return {"success": False, "error": "must_select_candidate_instance"}

        now = utc_now()
        with db() as conn:
            conn.execute(
                "update v6_pending_voice_commands set status = 'confirmed', matched_instance_id = ?, confirmed_at = ? where command_id = ?",
                (target_instance_id, now, command_id),
            )

        exec_res = self.report_instance_execution(
            target_instance_id,
            user_id=user_id,
            outcome=row["proposed_outcome"],
            source=f"voice_confirmed:{row['source_device']}",
            action_idempotency_key=f"vconfirm_{command_id}",
        )

        inst = exec_res.get("instance")
        if learn_phrase_on_confirm and inst:
            self.add_voice_phrase(
                user_id=user_id,
                phrase=row["raw_transcript"],
                target_type="template",
                target_id=inst["template_id"],
                target_name=inst["name"],
                approved_by_user=True,
            )

        return {
            "success": True,
            "command_id": command_id,
            "status": "confirmed_and_saved",
            "visual_confirmation_he": f"אושר ונשמר: משימה #{inst['daily_voice_number']} '{inst['name']}' סומנה כ-'{row['proposed_outcome']}'. (אפשרות ביטול מהיר זמינה)",
            "execution_result": exec_res,
        }

    # =========================================================================
    # SLICE 1D: Multimedia (Replacing Text Completely) & Scheduled Messages / TTS Form
    # =========================================================================

    def register_media_asset(self, payload: dict[str, Any]) -> dict[str, Any]:
        """
        Section 4:
        Server-side validation of actual media_type, MIME type, size limit, and permissions.
        Supports video, infographic, image, prepared audio (full alternative to TTS), question, or link.
        Media can replace text completely!
        """
        user_id = str(payload.get("user_id") or "moshe")
        media_type = str(payload.get("media_type") or "infographic").lower()
        mime_type = str(payload.get("mime_type") or "image/png").lower()
        size_bytes = int(payload.get("size_bytes", 1024))

        allowed_mimes = ALLOWED_MEDIA_MIME_PREFIXES.get(media_type)
        if not allowed_mimes or mime_type not in allowed_mimes:
            raise ValueError(f"Invalid or unsupported mime_type '{mime_type}' for media_type '{media_type}'")
        if size_bytes <= 0 or size_bytes > self.MAX_MEDIA_SIZE_BYTES:
            raise ValueError(f"Media file size {size_bytes} exceeds limit {self.MAX_MEDIA_SIZE_BYTES}")

        media_id = str(payload.get("media_id") or resource_id("v6_media"))
        content_version_id = str(payload.get("content_version_id") or f"mver_{media_id}_v1")
        now = utc_now()

        with db() as conn:
            conn.execute(
                """
                insert into v6_media_assets
                (media_id, user_id, title, media_type, mime_type, file_path_or_url,
                 size_bytes, duration_seconds, alt_text_or_transcript, language,
                 content_version_id, offline_cached, ttl_days, created_at)
                values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    media_id,
                    user_id,
                    str(payload.get("title") or f"{media_type}_{media_id[-4:]}"),
                    media_type,
                    mime_type,
                    str(payload["file_path_or_url"]),
                    size_bytes,
                    payload.get("duration_seconds"),
                    payload.get("alt_text_or_transcript"),
                    str(payload.get("language") or "he"),
                    content_version_id,
                    1 if bool(payload.get("offline_cached", True)) else 0,
                    payload.get("ttl_days", 30),
                    now,
                ),
            )
            row = conn.execute("select * from v6_media_assets where media_id = ?", (media_id,)).fetchone()
        return {"success": True, "media": self._media_row(row)}

    def list_media_assets(self, user_id: str = "moshe") -> list[dict[str, Any]]:
        with db() as conn:
            rows = conn.execute(
                "select * from v6_media_assets where user_id = ? order by created_at desc",
                (user_id,),
            ).fetchall()
        return [self._media_row(r) for r in rows]

    def create_scheduled_message(self, payload: dict[str, Any]) -> dict[str, Any]:
        """
        Section 5:
        Dedicated Scheduled Messages & TTS Reader form:
        - Supports typed/dictated text, attached media (which can completely replace text!),
          start_date, one or multiple schedule times, daily/weekly/monthly recurrence,
          display_mode (`text`, `tts`, `media`, `combined`), preview, pause/resume/edit/delete.
        - Respects Global Mute & Quiet Mode (manual playback by default; no auto-TTS when muted).
        """
        user_id = str(payload.get("user_id") or "moshe")
        text_content = payload.get("text_content")
        media_id = payload.get("media_id")
        media_blocks = list(payload.get("media_blocks") or [])
        if not text_content and not media_id and not media_blocks:
            raise ValueError("Scheduled message must have text_content or media_id/media_blocks")

        message_id = str(payload.get("message_id") or resource_id("v6_msg"))
        now = utc_now()
        schedule_times = list(payload.get("schedule_times") or ["08:00"])

        with db() as conn:
            conn.execute(
                """
                insert into v6_scheduled_messages
                (message_id, user_id, name, text_content, media_id, media_blocks_json,
                 start_date, schedule_times_json, recurrence, display_mode,
                 require_response, auto_tts_allowed, tts_speed, tts_voice,
                 importance, status, last_triggered_at, created_at, updated_at)
                values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    message_id,
                    user_id,
                    str(payload.get("name") or "הודעה מתוזמנת"),
                    text_content,
                    media_id,
                    json_dump(media_blocks),
                    str(payload.get("start_date") or date.today().isoformat()),
                    json_dump(schedule_times),
                    str(payload.get("recurrence") or "daily"),
                    str(payload.get("display_mode") or ("media" if (media_id or media_blocks) and not text_content else "tts")),
                    1 if bool(payload.get("require_response", False)) else 0,
                    1 if bool(payload.get("auto_tts_allowed", False)) else 0,
                    float(payload.get("tts_speed", 1.0)),
                    str(payload.get("tts_voice") or "he-IL-Standard"),
                    int(payload.get("importance", 6)),
                    str(payload.get("status") or "active"),
                    None,
                    now,
                    now,
                ),
            )
            row = conn.execute("select * from v6_scheduled_messages where message_id = ?", (message_id,)).fetchone()
        return {"success": True, "scheduled_message": self._scheduled_message_row(row)}

    def list_scheduled_messages(self, user_id: str = "moshe") -> list[dict[str, Any]]:
        with db() as conn:
            rows = conn.execute(
                "select * from v6_scheduled_messages where user_id = ? order by created_at desc",
                (user_id,),
            ).fetchall()
        return [self._scheduled_message_row(r) for r in rows]

    def preview_or_trigger_scheduled_message(self, message_id: str, *, user_id: str = "moshe") -> dict[str, Any]:
        with db() as conn:
            row = conn.execute(
                "select * from v6_scheduled_messages where message_id = ? and user_id = ?",
                (message_id, user_id),
            ).fetchone()
        if not row:
            return {"success": False, "error": "message_not_found"}
        msg = self._scheduled_message_row(row)
        context = self.get_context_mode(user_id=user_id)
        tts_suppressed_by_mute = bool(context["global_mute_tts"] or context["active_mode"] in {"quiet_meeting", "shabbat"})
        return {
            "success": True,
            "scheduled_message": msg,
            "tts_suppressed_by_mute_or_quiet_mode": tts_suppressed_by_mute,
            "manual_play_available": True,
            "auto_tts_will_play": bool(msg["auto_tts_allowed"] and not tts_suppressed_by_mute),
            "delivery_instructions_he": (
                "מצב שקט / השתקת הקראות פעיל: ההודעה מוצגת חזותית בלבד (ללא הקראת TTS אוטומטית)."
                if tts_suppressed_by_mute
                else "הודעה מוכנה להצגה ולהאזנה בעברית (תצוגה מקדימה / השמעה ידנית זמינה)."
            ),
        }

    # =========================================================================
    # SLICE 1E: Quick Inbox ('Idea' Button) & Progressive Onboarding Owned by Compass
    # =========================================================================

    def capture_inbox_item(self, payload: dict[str, Any]) -> dict[str, Any]:
        """
        Section 14:
        Fast capture of an Idea, Task, Rule, Question, or Reminder.
        - 'כפתור רעיון' (`item_kind="idea"`) saves immediately without mandatory form or immediate conversion into a task!
        - Suggests association to an existing goal or rule when relevant without forcing association.
        """
        user_id = str(payload.get("user_id") or "moshe")
        raw_text = str(payload["raw_text"]).strip()
        item_kind = str(payload.get("item_kind") or "auto").lower()

        if item_kind == "auto":
            if any(w in raw_text for w in ("רעיון:", "אולי כדאי", "מחשבה:")):
                item_kind = "idea"
            elif any(w in raw_text for w in ("כלל:", "חוק:", "בכל יום ב-")):
                item_kind = "rule_proposal"
            else:
                item_kind = "task_proposal"

        suggested_goal = None
        if any(w in raw_text.lower() for w in ("מתח", "משקולות", "ריצה", "כושר", "גופני")):
            suggested_goal = "physical"
        elif any(w in raw_text.lower() for w in ("סקרנות", "נשימה", "רגש", "תגובה", "מנטלי")):
            suggested_goal = "mental"
        elif any(w in raw_text.lower() for w in ("ai", "סוכן", "מודל", "קוד")):
            suggested_goal = "ai_professional"

        item_id = resource_id("v6_inb")
        now = utc_now()
        status = "saved_in_idea_bank" if item_kind == "idea" else "pending_user_confirmation"

        with db() as conn:
            conn.execute(
                """
                insert into v6_inbox_items
                (item_id, user_id, item_kind, raw_text, source, suggested_classification,
                 suggested_goal_id, suggested_rule_id, status, created_at, updated_at)
                values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    item_id,
                    user_id,
                    item_kind,
                    raw_text,
                    str(payload.get("source") or "quick_inbox"),
                    item_kind,
                    suggested_goal,
                    payload.get("suggested_rule_id"),
                    status,
                    now,
                    now,
                ),
            )
            row = conn.execute("select * from v6_inbox_items where item_id = ?", (item_id,)).fetchone()
        return {
            "success": True,
            "inbox_item": self._inbox_row(row),
            "converted_to_task_automatically": False,
        }

    def list_inbox_items(self, user_id: str = "moshe") -> list[dict[str, Any]]:
        with db() as conn:
            rows = conn.execute(
                "select * from v6_inbox_items where user_id = ? order by created_at desc",
                (user_id,),
            ).fetchall()
        return [self._inbox_row(r) for r in rows]

    def ensure_seed_onboarding_questions(self, user_id: str = "moshe") -> None:
        now = utc_now()
        with db() as conn:
            for q in SEED_ONBOARDING_QUESTIONS:
                qid = f"{q['code']}_{user_id}"
                conn.execute(
                    """
                    insert or ignore into v6_onboarding_questions
                    (question_id, user_id, category, question_he, importance,
                     is_blocking_infra, status, answer_text, answer_fact_or_inference,
                     topic_muted, asked_count, last_asked_at, answered_at, updated_at)
                    values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        qid,
                        user_id,
                        q["category"],
                        q["question_he"],
                        q["importance"],
                        q["is_blocking_infra"],
                        "open",
                        None,
                        None,
                        0,
                        0,
                        None,
                        None,
                        now,
                    ),
                )

    def get_next_onboarding_question(self, user_id: str = "moshe") -> dict[str, Any]:
        """
        Section 13:
        Compass manages the Progressive Onboarding question bank:
        - Never repeats an already-answered question or a muted topic.
        - Prioritizes blocking infrastructure questions first, then highest importance.
        """
        self.ensure_seed_onboarding_questions(user_id)
        with db() as conn:
            row = conn.execute(
                """
                select * from v6_onboarding_questions
                where user_id = ? and status = 'open' and topic_muted = 0
                order by is_blocking_infra desc, importance desc, asked_count asc
                limit 1
                """,
                (user_id,),
            ).fetchone()
            all_rows = conn.execute(
                "select * from v6_onboarding_questions where user_id = ? order by is_blocking_infra desc, importance desc",
                (user_id,),
            ).fetchall()

        answered_count = sum(1 for r in all_rows if r["status"] == "answered")
        return {
            "success": True,
            "user_id": user_id,
            "next_question": self._onboarding_row(row) if row else None,
            "answered_count": answered_count,
            "total_questions": len(all_rows),
            "questions": [self._onboarding_row(r) for r in all_rows],
        }

    def answer_or_skip_onboarding_question(
        self,
        question_id: str,
        *,
        user_id: str = "moshe",
        action: str = "answer",
        answer_text: str | None = None,
        fact_or_inference: str = "explicit_fact",
        mute_topic: bool = False,
    ) -> dict[str, Any]:
        """
        Section 13:
        Supports answering (`explicit_fact` vs. `inference`), skipping, deferring, editing, or muting the topic.
        """
        self.ensure_seed_onboarding_questions(user_id)
        now = utc_now()
        status_map = {
            "answer": "answered",
            "skip": "skipped",
            "defer": "open",
            "mute_topic": "muted",
        }
        new_status = status_map.get(action, "answered")
        with db() as conn:
            row = conn.execute(
                "select * from v6_onboarding_questions where question_id = ? and user_id = ?",
                (question_id, user_id),
            ).fetchone()
            if not row:
                return {"success": False, "error": "question_not_found"}

            if mute_topic or action == "mute_topic":
                conn.execute(
                    "update v6_onboarding_questions set topic_muted = 1, status = 'muted', updated_at = ? where user_id = ? and category = ?",
                    (now, user_id, row["category"]),
                )
            else:
                conn.execute(
                    """
                    update v6_onboarding_questions
                    set status = ?,
                        answer_text = coalesce(?, answer_text),
                        answer_fact_or_inference = ?,
                        asked_count = asked_count + 1,
                        last_asked_at = ?,
                        answered_at = case when ? = 'answered' then ? else answered_at end,
                        updated_at = ?
                    where question_id = ? and user_id = ?
                    """,
                    (
                        new_status,
                        answer_text,
                        fact_or_inference,
                        now,
                        new_status,
                        now,
                        now,
                        question_id,
                        user_id,
                    ),
                )
            updated = conn.execute(
                "select * from v6_onboarding_questions where question_id = ?",
                (question_id,),
            ).fetchone()
        return {"success": True, "question": self._onboarding_row(updated)}

    # =========================================================================
    # Row Serializers
    # =========================================================================

    def _template_row(self, row: Any) -> dict[str, Any]:
        return {
            "template_id": row["template_id"],
            "user_id": row["user_id"],
            "name": row["name"],
            "aliases": json_load(row["aliases_json"], []),
            "description": row["description"],
            "open_time": row["open_time"],
            "preferred_time": row["preferred_time"],
            "window_end_time": row["window_end_time"],
            "check_time": row["check_time"],
            "frequency": row["frequency"],
            "content_blocks": json_load(row["content_blocks_json"], []),
            "media_only": bool(row["media_only"]),
            "completion_condition": row["completion_condition"],
            "evidence_type": row["evidence_type"],
            "estimated_minutes": int(row["estimated_minutes"]),
            "minimum_viable_version": row["minimum_viable_version"],
            "importance": int(row["importance"]),
            "impact": int(row["impact"]),
            "difficulty": int(row["difficulty"]),
            "energy_requirement": int(row["energy_requirement"]),
            "exception_action": row["exception_action"],
            "ttl_policy": row["ttl_policy"],
            "goal_ids": json_load(row["goal_ids_json"], []),
            "rule_id": row["rule_id"],
            "is_system_inquiry": bool(row["is_system_inquiry"]),
            "max_inquiry_repeats": int(row["max_inquiry_repeats"]),
            "inquiry_repeats_count": int(row["inquiry_repeats_count"]),
            "status": row["status"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }

    def _instance_row(self, row: Any) -> dict[str, Any]:
        return {
            "instance_id": row["instance_id"],
            "template_id": row["template_id"],
            "user_id": row["user_id"],
            "instance_date": row["instance_date"],
            "daily_voice_number": int(row["daily_voice_number"]),
            "name": row["name"],
            "aliases": json_load(row["aliases_json"], []),
            "open_time": row["open_time"],
            "preferred_time": row["preferred_time"],
            "window_end_time": row["window_end_time"],
            "check_time": row["check_time"],
            "schedule_state": row["schedule_state"],
            "execution_outcome": row["execution_outcome"],
            "partial_value": row["partial_value"],
            "partial_unit": row["partial_unit"],
            "partial_target": row["partial_target"],
            "partial_note": row["partial_note"],
            "used_minimum_version": bool(row["used_minimum_version"]),
            "alternative_performed": row["alternative_performed"],
            "deferred_until": row["deferred_until"],
            "defer_count": int(row["defer_count"]),
            "content_blocks": json_load(row["content_blocks_json"], []),
            "content_version_id": row["content_version_id"],
            "media_only": bool(row["media_only"]),
            "ttl_policy": row["ttl_policy"],
            "reported_execution_at": row["reported_execution_at"],
            "received_at": row["received_at"],
            "report_source": row["report_source"],
            "entity_version": int(row["entity_version"]),
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }

    def _media_row(self, row: Any) -> dict[str, Any]:
        return {
            "media_id": row["media_id"],
            "user_id": row["user_id"],
            "title": row["title"],
            "media_type": row["media_type"],
            "mime_type": row["mime_type"],
            "file_path_or_url": row["file_path_or_url"],
            "size_bytes": int(row["size_bytes"]),
            "duration_seconds": row["duration_seconds"],
            "alt_text_or_transcript": row["alt_text_or_transcript"],
            "language": row["language"],
            "content_version_id": row["content_version_id"],
            "offline_cached": bool(row["offline_cached"]),
            "ttl_days": row["ttl_days"],
            "created_at": row["created_at"],
        }

    def _scheduled_message_row(self, row: Any) -> dict[str, Any]:
        return {
            "message_id": row["message_id"],
            "user_id": row["user_id"],
            "name": row["name"],
            "text_content": row["text_content"],
            "media_id": row["media_id"],
            "media_blocks": json_load(row["media_blocks_json"], []),
            "start_date": row["start_date"],
            "schedule_times": json_load(row["schedule_times_json"], []),
            "recurrence": row["recurrence"],
            "display_mode": row["display_mode"],
            "require_response": bool(row["require_response"]),
            "auto_tts_allowed": bool(row["auto_tts_allowed"]),
            "tts_speed": float(row["tts_speed"]),
            "tts_voice": row["tts_voice"],
            "importance": int(row["importance"]),
            "status": row["status"],
            "last_triggered_at": row["last_triggered_at"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }

    def _context_mode_row(self, row: Any) -> dict[str, Any]:
        return {
            "user_id": row["user_id"],
            "active_mode": row["active_mode"],
            "global_mute_tts": bool(row["global_mute_tts"]),
            "quiet_hours_start": row["quiet_hours_start"],
            "quiet_hours_end": row["quiet_hours_end"],
            "max_concurrent_prompts": int(row["max_concurrent_prompts"]),
            "active_prompts_count": int(row["active_prompts_count"]),
            "timezone": row["timezone"],
            "week_starts_on": row["week_starts_on"],
            "server_sleep_start": row["server_sleep_start"],
            "server_sleep_end": row["server_sleep_end"],
            "last_active_heartbeat_at": row["last_active_heartbeat_at"],
            "last_catchup_at": row["last_catchup_at"],
            "updated_at": row["updated_at"],
        }

    def _inbox_row(self, row: Any) -> dict[str, Any]:
        return {
            "item_id": row["item_id"],
            "user_id": row["user_id"],
            "item_kind": row["item_kind"],
            "raw_text": row["raw_text"],
            "source": row["source"],
            "suggested_classification": row["suggested_classification"],
            "suggested_goal_id": row["suggested_goal_id"],
            "suggested_rule_id": row["suggested_rule_id"],
            "status": row["status"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }

    def _onboarding_row(self, row: Any) -> dict[str, Any]:
        return {
            "question_id": row["question_id"],
            "user_id": row["user_id"],
            "category": row["category"],
            "question_he": row["question_he"],
            "importance": int(row["importance"]),
            "is_blocking_infra": bool(row["is_blocking_infra"]),
            "status": row["status"],
            "answer_text": row["answer_text"],
            "answer_fact_or_inference": row["answer_fact_or_inference"],
            "topic_muted": bool(row["topic_muted"]),
            "asked_count": int(row["asked_count"]),
            "last_asked_at": row["last_asked_at"],
            "answered_at": row["answered_at"],
            "updated_at": row["updated_at"],
        }
