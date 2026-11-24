from __future__ import annotations

import os
import tempfile
import unittest
from datetime import date, datetime, timezone
from pathlib import Path


class Phase1ControlCenterAndTaskCommanderTests(unittest.TestCase):
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

    def test_20_initial_rules_exist_in_catalog(self) -> None:
        from app.routers.control_center import list_rules_catalog

        res = list_rules_catalog()
        self.assertTrue(res["success"])
        rule_ids = {r["rule_id"] for r in res["rules"]}
        expected_20 = {
            "FROG-001",
            "FROG-002",
            "FROG-003",
            "FROG-004",
            "HABIT-001",
            "MENTAL-001",
            "MENTAL-002",
            "MENTAL-003",
            "ASSESS-001",
            "ASSESS-002",
            "GROWTH-001",
            "GROWTH-002",
            "CHALLENGE-001",
            "CHALLENGE-002",
            "PLAN-001",
            "PLAN-002",
            "AI-001",
            "AI-002",
            "CONTROL-001",
            "CONTROL-002",
        }
        self.assertTrue(expected_20.issubset(rule_ids))

    def test_disabled_rule_does_not_fire_and_can_rollback_version(self) -> None:
        """Covers Acceptance Criteria #12 (disabled rule not triggered) and #20 (rollback to prior version)."""
        from app.routers.control_center import (
            RuleRollbackRequest,
            RuleUpdateRequest,
            get_catalog_rule_versions,
            rollback_catalog_rule_version,
            update_catalog_rule,
        )
        from app.routers.rules import StructuredRulesEventRequest, evaluate_structured_rules_event

        # 1. Disable FROG-001 -> creates version 2
        upd = update_catalog_rule(
            "FROG-001",
            RuleUpdateRequest(user_id="moshe", enabled=False, change_note="Disable evening frog check temporarily"),
        )
        self.assertEqual(upd["rule"]["version"], 2)
        self.assertFalse(upd["rule"]["enabled"])

        # 2. Evaluate evening_review.frogs_check -> FROG-001 must NOT match while disabled
        eval_res = evaluate_structured_rules_event(
            StructuredRulesEventRequest(
                event_id="evt_frog_disabled",
                event_type="evening_review.frogs_check",
                source="test",
                user_id="moshe",
                occurred_at=datetime.now(timezone.utc),
                idempotency_key="idem_frog_disabled",
                payload={"active_frogs_count": 2},
            )
        )
        matched_ids = [r["rule_id"] for r in eval_res["matched_rules"]]
        self.assertNotIn("FROG-001", matched_ids)

        # 3. Rollback FROG-001 to version 1 -> creates version 3 with enabled=True
        rb = rollback_catalog_rule_version("FROG-001", RuleRollbackRequest(user_id="moshe", target_version=1))
        self.assertEqual(rb["rule"]["version"], 3)
        self.assertTrue(rb["rule"]["enabled"])

        versions = get_catalog_rule_versions("FROG-001")
        self.assertEqual(len(versions["versions"]), 3)

        # 4. Re-evaluate -> FROG-001 fires again
        eval_res2 = evaluate_structured_rules_event(
            StructuredRulesEventRequest(
                event_id="evt_frog_reenabled",
                event_type="evening_review.frogs_check",
                source="test",
                user_id="moshe",
                occurred_at=datetime.now(timezone.utc),
                idempotency_key="idem_frog_reenabled",
                payload={"active_frogs_count": 2},
            )
        )
        matched_ids2 = [r["rule_id"] for r in eval_res2["matched_rules"]]
        self.assertIn("FROG-001", matched_ids2)

    def test_conflicting_rules_and_decision_explanation(self) -> None:
        """Covers Acceptance Criteria #13 (rule conflict resolution documented) and #14 (actual rule & data explained)."""
        from app.routers.control_center import explain_rule_decision
        from app.routers.rules import StructuredRulesEventRequest, evaluate_structured_rules_event

        # daily_plan.evaluate with low energy (PLAN-001: allow) AND overloaded minutes (PLAN-002: require_approval)
        res = evaluate_structured_rules_event(
            StructuredRulesEventRequest(
                event_id="evt_conflict_1",
                event_type="daily_plan.evaluate",
                source="test",
                user_id="moshe",
                occurred_at=datetime.now(timezone.utc),
                idempotency_key="idem_conflict_1",
                payload={
                    "energy_level": 2,
                    "available_minutes": 60,
                    "planned_minutes": 120,
                    "is_overloaded": True,
                    "core_domains_scheduled_count": 1,
                },
            )
        )
        self.assertEqual(res["final_decision"], "require_approval")
        self.assertTrue(len(res["conflicts_resolved"]) >= 1)
        self.assertTrue(len(res["alternatives_considered"]) >= 2)

        explanation = explain_rule_decision(res["evaluation_id"])
        self.assertTrue(explanation["success"])
        self.assertEqual(explanation["relevant_data"]["planned_minutes"], 120)
        self.assertIn("PLAN-002", explanation["readable_explanation_he"])
        self.assertTrue(len(explanation["conflicts_resolved"]) >= 1)

    def test_daily_plan_requires_approval_when_overloaded_and_adapts_to_low_energy(self) -> None:
        """Covers Acceptance Criteria #5 (low energy adapts plan), #6 (insufficient time blocks impossible activation), #18 (idempotency), #19 (pending_approval before approval)."""
        from app.routers.daily_plan import save_daily_plan
        from app.schemas.daily_plan import SaveDailyPlanRequest

        req = SaveDailyPlanRequest(
            idempotency_key="plan_overload_1",
            user_id="moshe",
            date=date(2026, 11, 24),
            energy_level=2,
            available_minutes=45,
            outcomes=[{"title": "Deep AI study"}],
            scheduled_tasks=[
                {"title": "AI Architecture Study", "minutes": 60, "domain": "ai"},
                {"title": "Pull-up Practice", "minutes": 30, "domain": "physical"},
            ],
        )
        res = save_daily_plan(req)
        self.assertEqual(res["status"], "pending_approval")
        self.assertIn("approval_request_id", res)

        # Idempotent duplicate call does not create duplicate record
        dup = save_daily_plan(req)
        self.assertTrue(dup["already_existed"])
        self.assertEqual(dup["resource_id"], res["resource_id"])

    def test_material_policy_change_requires_approval(self) -> None:
        """Covers Acceptance Criterion #22 (CONTROL-001: material policy change requires approval)."""
        from app.routers.control_center import PolicyUpdateRequest, update_user_autonomy_policy

        # Non-material role switch (Planner -> Executor) succeeds directly
        role_res = update_user_autonomy_policy(PolicyUpdateRequest(user_id="moshe", active_role="executor"))
        self.assertEqual(role_res["status"], "updated")
        self.assertEqual(role_res["policy"]["active_role"], "executor")

        # Material change to max_challenge_difficulty without approval_confirmed -> requires approval
        pol_res = update_user_autonomy_policy(
            PolicyUpdateRequest(user_id="moshe", max_challenge_difficulty=9, approval_confirmed=False)
        )
        self.assertEqual(pol_res["status"], "approval_required")
        self.assertIn("approval_request_id", pol_res)
        # Unapproved change must NOT have modified max_challenge_difficulty
        self.assertEqual(pol_res["policy"]["max_challenge_difficulty"], 5)

        # Material change with approval_confirmed=True -> updates policy
        approved_res = update_user_autonomy_policy(
            PolicyUpdateRequest(user_id="moshe", max_challenge_difficulty=7, approval_confirmed=True)
        )
        self.assertEqual(approved_res["status"], "updated")
        self.assertEqual(approved_res["policy"]["max_challenge_difficulty"], 7)

    def test_native_task_commander_under_compass(self) -> None:
        """Verifies TaskCommander running natively inside Compass (create, recurring instances, today, mark_done, snooze, skip)."""
        from app.routers.task_commander import (
            CreateOperationalTaskRequest,
            SnoozeInstanceRequest,
            create_task,
            generate_instances,
            get_status,
            get_today,
            mark_instance_done,
            skip_instance,
            snooze_instance,
        )

        today_str = date.today().isoformat()
        created = create_task(
            CreateOperationalTaskRequest(
                user_id="moshe",
                title="Morning Mobility & Pull-up Prep",
                priority="high",
                recurrence_rule="DAILY@08:30",
                occurrence_date=today_str,
                estimated_minutes=15,
            )
        )
        self.assertTrue(created["connected"])
        instance_id = created["instance_id"]

        today_list = get_today(user_id="moshe")
        self.assertEqual(today_list["count"], 1)
        self.assertEqual(today_list["items"][0]["instance_id"], instance_id)

        # Mark today's instance done -> disappears from today's pending list and generates tomorrow's instance
        done_res = mark_instance_done(instance_id)
        self.assertTrue(done_res["success"])

        today_after = get_today(user_id="moshe")
        self.assertEqual(today_after["count"], 0)

        # Create a second task and test snooze & skip
        created2 = create_task(
            CreateOperationalTaskRequest(
                user_id="moshe",
                title="Review AI Research Notes",
                occurrence_date=today_str,
            )
        )
        inst2 = created2["instance_id"]
        snoozed = snooze_instance(inst2, SnoozeInstanceRequest(minutes=60))
        self.assertTrue(snoozed["success"])

        skipped = skip_instance(inst2)
        self.assertEqual(skipped["status"], "skipped")

        st = get_status(user_id="moshe")
        self.assertEqual(st["done_instances"], 1)
        self.assertEqual(st["skipped_instances"], 1)
        gen = generate_instances(days=2, user_id="moshe")
        self.assertTrue(gen["connected"])


if __name__ == "__main__":
    unittest.main()
