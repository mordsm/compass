from __future__ import annotations

import os
import tempfile
import unittest
from datetime import date
from pathlib import Path


class Phase2EatThatFrogTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)
        os.environ["COMPASS_DATABASE_URL"] = ""
        os.environ["COMPASS_DATABASE_PATH"] = str(Path(self.tmpdir.name) / "compass.db")
        os.environ["COMPASS_ACTIONS_API_KEY"] = "test-token"
        os.environ["COMPASS_AUTOSTART_LOCAL_AGENTS"] = "false"

        from app.config import get_settings
        from app.database import init_db

        get_settings.cache_clear()
        init_db()

    def test_evening_check_with_two_frogs_requests_replenishment_without_inventing(self) -> None:
        """Covers Acceptance Criterion #1: Only 2 frogs -> requests replenishment and never invents frogs."""
        from app.routers.frogs import CreateFrogRequest, create_frog, list_frogs, run_evening_frog_pool_check

        create_frog(
            CreateFrogRequest(
                user_id="moshe",
                name="שיחה מורכבת עם ספק",
                frog_type="one_time",
                importance=8,
                resistance_level=8,
            )
        )
        create_frog(
            CreateFrogRequest(
                user_id="moshe",
                name="תרגול מתח ומשקולות",
                domain="physical",
                frog_type="ongoing",
                importance=9,
                resistance_level=7,
            )
        )

        check = run_evening_frog_pool_check(user_id="moshe")
        self.assertTrue(check["success"])
        self.assertEqual(check["active_frogs_count"], 2)
        self.assertTrue(check["replenishment_needed"])
        self.assertEqual(check["missing_count"], 2)
        self.assertEqual(check["invented_frogs"], [])

        # Confirm pool still has exactly 2 frogs (none invented)
        pool = list_frogs(user_id="moshe", status="active")
        self.assertEqual(pool["active_count"], 2)

    def test_one_time_frog_closes_on_completion_while_ongoing_frog_remains_active(self) -> None:
        """Covers Acceptance Criteria #2 (one-time closes) and #3 (ongoing stays in pool) and #4 (ongoing removal requires approval)."""
        from app.routers.frogs import (
            CreateFrogRequest,
            RemoveFrogRequest,
            ReportFrogExecutionRequest,
            create_frog,
            list_frogs,
            report_frog_execution,
            request_remove_frog,
        )

        f_one = create_frog(
            CreateFrogRequest(
                user_id="moshe",
                name="הגשת מסמך רשמי",
                frog_type="one_time",
                importance=8,
                resistance_level=7,
            )
        )["frog"]
        f_ongoing = create_frog(
            CreateFrogRequest(
                user_id="moshe",
                name="אימון מתח בוקר",
                domain="physical",
                frog_type="ongoing",
                importance=9,
                resistance_level=8,
            )
        )["frog"]

        # 1. Complete one-time frog -> closes automatically (FROG-003)
        rep1 = report_frog_execution(
            f_one["frog_id"],
            ReportFrogExecutionRequest(user_id="moshe", outcome="completed"),
        )
        self.assertEqual(rep1["frog"]["status"], "completed")
        self.assertEqual(rep1["frog"]["completions_count"], 1)

        # 2. Complete ongoing frog -> remains active in pool!
        rep2 = report_frog_execution(
            f_ongoing["frog_id"],
            ReportFrogExecutionRequest(user_id="moshe", outcome="completed"),
        )
        self.assertEqual(rep2["frog"]["status"], "active")
        self.assertEqual(rep2["frog"]["completions_count"], 1)

        active_pool = list_frogs(user_id="moshe", status="active")
        active_ids = [f["frog_id"] for f in active_pool["frogs"]]
        self.assertNotIn(f_one["frog_id"], active_ids)
        self.assertIn(f_ongoing["frog_id"], active_ids)

        # 3. Request removal of ongoing frog without confirmation -> requires approval (FROG-004)
        rm_unconfirmed = request_remove_frog(
            f_ongoing["frog_id"],
            RemoveFrogRequest(user_id="moshe", reason="הפך להרגל טבעי", approval_confirmed=False),
        )
        self.assertEqual(rm_unconfirmed["status"], "approval_required")
        self.assertIn("approval_request_id", rm_unconfirmed)
        # Still active before approval!
        self.assertEqual(rm_unconfirmed["frog"]["status"], "active")

        # 4. Confirm removal of ongoing frog -> graduates from pool
        rm_confirmed = request_remove_frog(
            f_ongoing["frog_id"],
            RemoveFrogRequest(user_id="moshe", reason="הפך להרגל טבעי", approval_confirmed=True),
        )
        self.assertEqual(rm_confirmed["status"], "graduated")
        self.assertEqual(rm_confirmed["frog"]["status"], "graduated")

    def test_daily_frog_selection_respects_time_energy_and_safety_and_integrates_with_daily_plan(self) -> None:
        """Covers Section 5.4 (deterministic morning selection, safety/time filters, user override, and daily plan integration)."""
        from app.routers.daily_plan import save_daily_plan
        from app.routers.frogs import (
            CreateFrogRequest,
            DailyFrogSelectRequest,
            OverrideDailyFrogRequest,
            UpdateFrogScoresRequest,
            create_frog,
            override_daily_selection,
            select_daily_frog,
            update_frog_scores,
        )
        from app.schemas.daily_plan import SaveDailyPlanRequest

        # Frog A: physical, high difficulty, has safety constraint "shoulder_pain"
        f_phys = create_frog(
            CreateFrogRequest(
                user_id="moshe",
                name="אימון מתח עצים",
                domain="physical",
                frog_type="ongoing",
                importance=10,
                resistance_level=9,
                difficulty_level=8,
                urgency=7,
                estimated_minutes=30,
                safety_constraints=["shoulder_pain"],
            )
        )["frog"]

        # Frog B: AI core domain, fits time and has no safety conflict
        f_ai = create_frog(
            CreateFrogRequest(
                user_id="moshe",
                name="כתיבת מבחן הערכה לסוכן AI",
                domain="ai_professional",
                frog_type="one_time",
                importance=9,
                resistance_level=8,
                difficulty_level=6,
                urgency=8,
                estimated_minutes=25,
            )
        )["frog"]

        # User updates Frog B urgency score
        upd = update_frog_scores(f_ai["frog_id"], UpdateFrogScoresRequest(user_id="moshe", urgency=9))
        self.assertEqual(upd["frog"]["urgency"], 9)

        # When shoulder_pain is active, physical frog is skipped and AI frog is selected
        sel = select_daily_frog(
            DailyFrogSelectRequest(
                user_id="moshe",
                date=date(2026, 11, 24),
                energy_level=4,
                available_minutes=45,
                active_safety_constraints=["shoulder_pain"],
            )
        )
        self.assertTrue(sel["selected"])
        self.assertEqual(sel["selected_frog"]["frog_id"], f_ai["frog_id"])
        self.assertEqual(sel["recommended_slot"], "morning_early")
        self.assertEqual(len(sel["skipped_candidates"]), 1)
        self.assertEqual(sel["skipped_candidates"][0]["frog_id"], f_phys["frog_id"])

        # User can defer or replace daily selection
        ovr = override_daily_selection(
            OverrideDailyFrogRequest(
                user_id="moshe",
                plan_date="2026-11-24",
                action="defer",
                reason="דחייה לשעות הצהריים",
            )
        )
        self.assertEqual(ovr["status"], "deferred_by_user")

        # Saving a daily plan automatically embeds the selected daily frog
        plan_res = save_daily_plan(
            SaveDailyPlanRequest(
                idempotency_key="plan_with_frog_1",
                user_id="moshe",
                date=date(2026, 11, 25),
                energy_level=4,
                available_minutes=120,
                outcomes=[{"title": "התקדמות ב-AI"}],
                scheduled_tasks=[{"title": "סקירת קוד", "minutes": 30, "domain": "ai"}],
            )
        )
        self.assertEqual(plan_res["status"], "active")
        self.assertIsNotNone(plan_res["downstream"]["daily_frog"])
        self.assertTrue(plan_res["downstream"]["daily_frog"]["selected"])


if __name__ == "__main__":
    unittest.main()
