from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path


class WeeklyProgressTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)
        os.environ["COMPASS_DATABASE_URL"] = ""
        os.environ["COMPASS_DATABASE_PATH"] = str(Path(self.tmpdir.name) / "compass.db")
        os.environ["COMPASS_ACTIONS_API_KEY"] = "test-token"

        from app.config import get_settings

        get_settings.cache_clear()

    def test_weekly_progress_is_derived_from_existing_operational_data(self) -> None:
        from app.database import db, init_db, json_dump
        from app.repository import CompassRepository

        init_db()
        with db() as conn:
            conn.execute(
                """
                insert into tasks
                (id, user_id, title, description, status, due_date, priority, source,
                 metadata_json, created_at, updated_at)
                values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "task_done",
                    "moshe",
                    "Done this week",
                    "",
                    "completed",
                    "2026-11-03",
                    "high",
                    "test",
                    "{}",
                    "2026-11-02T08:00:00+00:00",
                    "2026-11-03T09:00:00+00:00",
                ),
            )
            conn.execute(
                """
                insert into tasks
                (id, user_id, title, description, status, due_date, priority, source,
                 metadata_json, created_at, updated_at)
                values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "task_open",
                    "moshe",
                    "Open and overdue",
                    "",
                    "active",
                    "2026-11-02",
                    "medium",
                    "test",
                    "{}",
                    "2026-11-02T08:00:00+00:00",
                    "2026-11-04T09:00:00+00:00",
                ),
            )
            for plan_id, plan_date, outcomes in (
                ("plan_1", "2026-11-02", ["A", "B"]),
                ("plan_2", "2026-11-03", ["C"]),
            ):
                conn.execute(
                    """
                    insert into daily_plans
                    (id, user_id, plan_date, status, energy_level, available_minutes,
                     outcomes_json, scheduled_tasks_json, deferred_items_json, risks_json,
                     raw_payload_json, created_at, updated_at)
                    values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        plan_id,
                        "moshe",
                        plan_date,
                        "approved",
                        3,
                        60,
                        json_dump(outcomes),
                        "[]",
                        "[]",
                        "[]",
                        "{}",
                        f"{plan_date}T06:00:00+00:00",
                        f"{plan_date}T06:00:00+00:00",
                    ),
                )
            conn.execute(
                """
                insert into approval_requests
                (id, user_id, title, description, requested_by, action_type, status,
                 risk_level, proposed_action_json, rule_result_json, created_at, updated_at)
                values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "approval_1",
                    "moshe",
                    "Review",
                    "",
                    "test",
                    "write",
                    "pending",
                    "medium",
                    "{}",
                    "{}",
                    "2026-11-03T10:00:00+00:00",
                    "2026-11-03T10:00:00+00:00",
                ),
            )
            conn.execute(
                """
                insert into msp_training_sessions
                (session_id, user_id, skill_id, exercise_id, mode, difficulty, status,
                 started_at, completed_at, summary, safety_state, idempotency_key)
                values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "session_1",
                    "moshe",
                    "focus",
                    "exercise_1",
                    "guided",
                    2,
                    "completed",
                    "2026-11-03T12:00:00+00:00",
                    "2026-11-03T12:10:00+00:00",
                    "ok",
                    "safe",
                    "session-1",
                ),
            )

        report = CompassRepository().get_weekly_progress("moshe", "2026-11-02")

        self.assertEqual(report["period"], {"start": "2026-11-02", "end": "2026-11-08"})
        self.assertEqual(report["metrics"]["tasks_completed"], 1)
        self.assertEqual(report["metrics"]["tasks_touched"], 2)
        self.assertEqual(report["metrics"]["task_completion_rate_pct"], 50.0)
        self.assertEqual(report["metrics"]["planned_days"], 2)
        self.assertEqual(report["metrics"]["planning_coverage_pct"], 28.6)
        self.assertEqual(report["metrics"]["outcomes_planned"], 3)
        self.assertEqual(report["metrics"]["overdue_open_tasks"], 1)
        self.assertEqual(report["metrics"]["pending_approvals"], 1)
        self.assertEqual(report["metrics"]["training_sessions_completed"], 1)
        self.assertEqual(report["definitions"]["task_completion_rate_pct"], "משימות שהושלמו מתוך משימות שעודכנו בשבוע")

    def test_weekly_progress_route_exposes_the_report(self) -> None:
        from app.database import init_db
        from app.routers.progress import get_weekly_progress

        init_db()
        report = get_weekly_progress(user_id="moshe", week_start="2026-11-02")

        self.assertEqual(report["user_id"], "moshe")
        self.assertEqual(report["period"]["start"], "2026-11-02")
        self.assertIn("task_completion_rate_pct", report["metrics"])


if __name__ == "__main__":
    unittest.main()
