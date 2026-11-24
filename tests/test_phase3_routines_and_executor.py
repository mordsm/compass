from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path


class Phase3RoutinesPrepAndExecutorTests(unittest.TestCase):
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

    def test_prep_protocol_6_steps_customization_and_periodic_sampling(self) -> None:
        """Covers Section 6 & Rule MENTAL-001: 6-step prep protocol, bounded pleasant starter, and periodic sampling."""
        from app.routers.routines import (
            LogPrepExecutionRequest,
            UpdatePrepProtocolRequest,
            get_prep_protocol,
            log_prep_execution,
            update_prep_protocol,
        )

        proto = get_prep_protocol(user_id="moshe")["protocol"]
        self.assertEqual(len(proto["steps"]), 6)
        self.assertEqual(proto["sampling_interval"], 3)

        # Customize breathing seconds and pleasant starter
        upd = update_prep_protocol(
            UpdatePrepProtocolRequest(
                user_id="moshe",
                breathing_seconds=60,
                pleasant_starter_action="שתיית כוס מים קרים",
                pleasant_starter_max_seconds=40,
                sampling_interval=2,
            )
        )["protocol"]
        self.assertEqual(upd["breathing_seconds"], 60)
        self.assertEqual(upd["sampling_interval"], 2)

        # Run 1 (sampled because 1 % 2 == 1)
        log1 = log_prep_execution(
            LogPrepExecutionRequest(
                user_id="moshe",
                target_type="frog",
                target_id="frog_1",
                tension_before=8,
                tension_after_prep=5,
                feeling_after_execution="הקלה וסיפוק",
                action_started=True,
                action_completed=True,
            )
        )
        self.assertTrue(log1["sampled_this_run"])
        self.assertEqual(log1["tension_delta"], -3)

        # Run 2 without optional tension fields -> not sampled, no full report required!
        log2 = log_prep_execution(
            LogPrepExecutionRequest(
                user_id="moshe",
                target_type="frog",
                target_id="frog_1",
                action_started=True,
                action_completed=True,
            )
        )
        self.assertFalse(log2["sampled_this_run"])

    def test_routine_minimum_viable_version_and_skip_without_penalty(self) -> None:
        """Covers Section 7, Rule HABIT-001 & Acceptance Criterion #8 (skip applies no penalty and preserves flexible streak)."""
        from app.routers.routines import (
            CreateRoutineRequest,
            ReportRoutineExecutionRequest,
            create_routine,
            report_routine_execution,
        )

        routine = create_routine(
            CreateRoutineRequest(
                user_id="moshe",
                name="שגרת תנועה וכוח בוקר",
                domain="physical",
                action_sequence=["חימום מפרקים 3 דק'", "3 סטים מתח", "מתיחות"],
                minimum_viable_version="סט אחד של תלייה על מתח + 5 נשימות",
                estimated_minutes=20,
                minimum_minutes=3,
            )
        )["routine"]
        self.assertEqual(routine["automation_kind"], "beneficial_habit_trigger")

        # 1. Complete full routine -> flexible_streak_count becomes 1
        rep1 = report_routine_execution(
            routine["routine_id"],
            ReportRoutineExecutionRequest(user_id="moshe", outcome="completed"),
        )
        self.assertEqual(rep1["routine"]["flexible_streak_count"], 1)

        # 2. High resistance -> complete minimum viable version (HABIT-001) -> flexible_streak_count becomes 2
        rep2 = report_routine_execution(
            routine["routine_id"],
            ReportRoutineExecutionRequest(
                user_id="moshe",
                outcome="minimum_completed",
                used_minimum_version=True,
                resistance_level=8,
                energy_level=2,
            ),
        )
        self.assertTrue(rep2["used_minimum_version"])
        self.assertEqual(rep2["routine"]["flexible_streak_count"], 2)

        # 3. Skip routine -> Acceptance Criterion #8: penalty_applied is False and flexible_streak_count stays 2!
        rep3 = report_routine_execution(
            routine["routine_id"],
            ReportRoutineExecutionRequest(user_id="moshe", outcome="skipped", notes="עומס חריג בבוקר"),
        )
        self.assertFalse(rep3["penalty_applied"])
        self.assertTrue(rep3["streak_preserved"])
        self.assertEqual(rep3["routine"]["flexible_streak_count"], 2)
        self.assertEqual(rep3["routine"]["skips_count"], 1)

    def test_planner_executor_separation_and_next_action_guidance(self) -> None:
        """Covers Section 10: Planner defines routines/policy; Executor cannot create routines and receives single next-action guidance."""
        from app.routers.control_center import PolicyUpdateRequest, update_user_autonomy_policy
        from app.routers.frogs import CreateFrogRequest, create_frog
        from app.routers.routines import CreateRoutineRequest, create_routine, get_executor_next_action

        # In Planner mode (default), create a routine and a challenging frog
        r = create_routine(
            CreateRoutineRequest(
                user_id="moshe",
                name="אימון גמישות ונשימה",
                domain="physical",
                minimum_viable_version="2 דקות נשימה סרעפתית ומתיחת גב",
                estimated_minutes=20,
                minimum_minutes=2,
            )
        )
        self.assertTrue(r["success"])

        create_frog(
            CreateFrogRequest(
                user_id="moshe",
                name="תרגיל מתח מלא",
                domain="physical",
                frog_type="ongoing",
                importance=9,
                resistance_level=8,
                estimated_minutes=15,
            )
        )

        # Switch to Executor mode
        update_user_autonomy_policy(PolicyUpdateRequest(user_id="moshe", active_role="executor"))

        # In Executor mode, attempting to create a new routine is blocked (Planner role required)
        blocked_create = create_routine(
            CreateRoutineRequest(
                user_id="moshe",
                name="שגרה חדשה שאסור ליצור במצב מבצע",
            )
        )
        self.assertFalse(blocked_create["success"])
        self.assertEqual(blocked_create["status"], "planner_role_required")

        # High energy (4) -> Executor next-action selects the daily frog and attaches the 6-step prep protocol (MENTAL-001)
        next_high = get_executor_next_action(
            user_id="moshe",
            energy_level=4,
            available_minutes=30,
            resistance_level=7,
        )
        self.assertEqual(next_high["action_source"], "frog")
        self.assertIsNotNone(next_high["preparation_protocol"])
        self.assertEqual(len(next_high["preparation_protocol"]["steps"]), 6)

        # Low energy (2) & high resistance (8) -> Executor next-action selects routine in minimum viable version (HABIT-001)
        next_low = get_executor_next_action(
            user_id="moshe",
            energy_level=2,
            available_minutes=10,
            resistance_level=8,
        )
        self.assertEqual(next_low["action_source"], "routine")
        self.assertTrue(next_low["next_action"]["used_minimum_viable_version"])
        self.assertEqual(next_low["next_action"]["minutes"], 2)


if __name__ == "__main__":
    unittest.main()
