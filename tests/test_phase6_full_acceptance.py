from __future__ import annotations

import os
import tempfile
import unittest
from datetime import date, timedelta
from unittest.mock import patch

from app.config import get_settings
from app.database import init_db
from app.repository import CompassRepository
from app.routers.control_center import (
    CancelDecisionRequest,
    PolicyUpdateRequest,
    RuleRollbackRequest,
    RuleUpdateRequest,
    cancel_decision_before_execution,
    explain_rule_decision,
    get_control_center_overview,
    rollback_catalog_rule_version,
    update_catalog_rule,
    update_user_autonomy_policy,
)
from app.routers.cycles import (
    EveningCycleRequest,
    IntradayCycleRequest,
    MonthlyCycleRequest,
    MorningCycleRequest,
    QuickCaptureRequest,
    WeeklyCycleRequest,
    process_quick_capture,
    run_evening_cycle,
    run_intraday_cycle,
    run_monthly_cycle,
    run_morning_cycle,
    run_weekly_cycle,
)
from app.services.frogs_service import FrogsService
from app.services.growth_service import GrowthChallengesAndPlayService
from app.services.mental_skills import MentalSkillsService
from app.services.routines_service import RoutinesAndExecutionService


class Phase6FullAcceptanceCriteriaTest(unittest.TestCase):
    """
    End-to-End Verification of all 22 Acceptance Criteria (Section 19 of specification).
    """

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.temp_dir.name, "compass_phase6_e2e.db")
        self.env = patch.dict(
            os.environ,
            {
                "COMPASS_DATABASE_URL": "",
                "COMPASS_DATABASE_PATH": self.db_path,
                "COMPASS_ACTIONS_API_KEY": "test-key",
                "COMPASS_AUTOSTART_LOCAL_AGENTS": "false",
            },
        )
        self.env.start()
        get_settings.cache_clear()
        init_db()

    def tearDown(self) -> None:
        self.env.stop()
        get_settings.cache_clear()
        self.temp_dir.cleanup()

    def test_all_22_acceptance_criteria_end_to_end(self) -> None:
        frogs_svc = FrogsService()
        routines_svc = RoutinesAndExecutionService()
        growth_svc = GrowthChallengesAndPlayService()
        mental_svc = MentalSkillsService()
        repo = CompassRepository()

        # --- Criteria 1, 2, 3, 4: Frogs pool < 4 prompt, One-time vs. Ongoing, Approval before removing Ongoing, Morning Frog selection ---
        f1 = frogs_svc.create_frog(
            {
                "user_id": "moshe",
                "name": "תיאום בדיקה שנתית",
                "frog_type": "one_time",
                "domain": "physical",
                "importance": 8,
                "resistance_level": 7,
                "urgency": 8,
                "estimated_minutes": 15,
            }
        )["frog"]
        f2 = frogs_svc.create_frog(
            {
                "user_id": "moshe",
                "name": "אימון מתח ומשקולות",
                "frog_type": "ongoing",
                "domain": "physical",
                "importance": 10,
                "resistance_level": 8,
                "urgency": 7,
                "estimated_minutes": 20,
            }
        )["frog"]

        # Criterion 1: Pool has 2 frogs (< 4) -> Evening cycle requests completion without inventing frogs
        evening_res = run_evening_cycle(
            EveningCycleRequest(user_id="moshe", wins_today=["התקדמות בפרויקט"], notes_for_tomorrow="להתחיל מוקדם")
        )
        self.assertTrue(evening_res["frog_pool_check"]["replenishment_needed"])
        self.assertEqual(evening_res["frog_pool_check"]["missing_count"], 2)
        self.assertEqual(evening_res["frog_pool_check"]["active_frogs_count"], 2)  # No frogs invented!

        # Criterion 4: Morning cycle selects daily frog according to energy & available time
        morning_res = run_morning_cycle(
            MorningCycleRequest(user_id="moshe", energy_level=4, available_minutes=180)
        )
        self.assertTrue(morning_res["daily_frog"]["selected"])
        self.assertEqual(morning_res["daily_plan"]["status"], "active")

        # Criterion 2: One-time frog closes on completion; ongoing frog remains active on completion
        r_one_time = frogs_svc.report_frog_execution(f1["frog_id"], user_id="moshe", outcome="completed")
        self.assertEqual(r_one_time["frog"]["status"], "completed")

        r_ongoing = frogs_svc.report_frog_execution(f2["frog_id"], user_id="moshe", outcome="completed")
        self.assertEqual(r_ongoing["frog"]["status"], "active")

        # Criterion 3: Ongoing frog is never removed without explicit user approval
        rem_blocked = frogs_svc.request_remove_frog(f2["frog_id"], user_id="moshe", approval_confirmed=False)
        self.assertEqual(rem_blocked["status"], "approval_required")
        self.assertEqual(frogs_svc.get_frog(f2["frog_id"])["status"], "active")

        # --- Criterion 5: Pre-action resistance reduction protocol offered before high-resistance action ---
        intraday_res = run_intraday_cycle(
            IntradayCycleRequest(user_id="moshe", energy_level=3, available_minutes=90)
        )
        bundle = intraday_res["next_action_bundle"]
        self.assertIsNotNone(bundle["preparation_protocol"])
        self.assertEqual(len(bundle["preparation_protocol"]["steps"]), 6)

        # --- Criterion 6 & 8: Minimum viable routine when time/energy is short, and penalty-free skip ---
        routine = routines_svc.create_routine(
            {
                "user_id": "moshe",
                "name": "תרגול מנטלי וגופני יומי",
                "domain": "mental",
                "action_sequence": ["20 דקות תרגול מלא"],
                "minimum_viable_version": "2 דקות נשימה ומודעות לגוף",
                "trigger_time_or_event": "08:00",
            }
        )["routine"]

        low_energy_rep = routines_svc.report_routine_execution(
            routine["routine_id"],
            user_id="moshe",
            outcome="minimum_completed",
            used_minimum_version=True,
            energy_level=2,
            resistance_level=8,
        )
        self.assertTrue(low_energy_rep["used_minimum_version"])

        # Criterion 8: Skipping a day does not reset flexible streak or penalize
        streak_before = low_energy_rep["routine"]["flexible_streak_count"]
        skip_rep = routines_svc.report_routine_execution(
            routine["routine_id"],
            user_id="moshe",
            outcome="skipped",
        )
        self.assertFalse(skip_rep["penalty_applied"])
        self.assertEqual(skip_rep["routine"]["flexible_streak_count"], streak_before)

        # --- Criterion 7: Physical load is never increased automatically when pain/limitation is reported ---
        chal = growth_svc.create_challenge(
            {
                "user_id": "moshe",
                "domain_slug": "physical",
                "challenge_type": "physical",
                "title": "אתגר מתח הדרגתי",
                "difficulty_level": 3,
                "max_approved_difficulty": 5,
            }
        )["challenge"]
        chal_eval = growth_svc.evaluate_and_adapt_challenge(
            chal["challenge_id"],
            user_id="moshe",
            outcome="completed",
            pain_or_limitation=True,
            requested_difficulty_delta=1,
        )
        self.assertTrue(chal_eval["blocked_automatic_increase"])
        self.assertEqual(chal_eval["applied_difficulty"], 3)

        # --- Criterion 9: Neglected core domain triggers a tailored intervention proposal ---
        old_ts = (date.today() - timedelta(days=10)).isoformat()
        growth_svc.record_domain_activity("moshe", "mental", occurred_at=old_ts)
        weekly_res = run_weekly_cycle(
            WeeklyCycleRequest(
                user_id="moshe",
                silent_wins=[{"short_description": "שיחה מתוחה שעברה בשקט ובסקרנות", "trigger_text": "ביקורת"}],
            )
        )
        self.assertGreaterEqual(weekly_res["neglected_domains_check"]["neglected_core_count"], 1)
        self.assertEqual(weekly_res["silent_wins_check"]["silent_wins_recorded_count"], 1)

        # --- Criteria 10, 11, 12: Mental events < threshold blocks trend, partial fields not treated as 0, full transparency when >= 5 ---
        # Currently only 1 silent win event exists (< 5) -> Criterion 10
        monthly_early = run_monthly_cycle(MonthlyCycleRequest(user_id="moshe", minimum_events_required=5))
        self.assertFalse(monthly_early["mental_assessment"]["sufficient_data"])
        self.assertEqual(monthly_early["mental_assessment"]["trend_status"], "insufficient_data")

        # Criterion 12: Partial mental event without numeric 0-10 scores keeps None (not 0)
        partial_evt = mental_svc.record_mental_event(
            {
                "user_id": "moshe",
                "short_description": "אירוע קצר בדיווח חלקי",
                "trigger_text": "עיכוב בפגישה",
                "actual_response": "נשימה קצרה והמשך עבודה",
            }
        )["event"]
        self.assertIsNone(partial_evt["initial_emotion_intensity"])
        self.assertIsNone(partial_evt["defensive_or_attack_urge"])

        # Add 4 more events with improving scores to reach 6 total events (>= 5) -> Criterion 11
        sample_events = [
            {"initial_emotion_intensity": 8, "defensive_or_attack_urge": 8, "curiosity_ability": 3, "choice_ability": 3, "recovery_duration_minutes": 40},
            {"initial_emotion_intensity": 7, "defensive_or_attack_urge": 7, "curiosity_ability": 4, "choice_ability": 4, "recovery_duration_minutes": 30},
            {"initial_emotion_intensity": 5, "defensive_or_attack_urge": 4, "curiosity_ability": 7, "choice_ability": 7, "recovery_duration_minutes": 15},
            {"initial_emotion_intensity": 4, "defensive_or_attack_urge": 3, "curiosity_ability": 8, "choice_ability": 8, "recovery_duration_minutes": 10},
        ]
        for idx, se in enumerate(sample_events):
            mental_svc.record_mental_event(
                {
                    "user_id": "moshe",
                    "short_description": f"אירוע מעקב {idx}",
                    "trigger_text": "ביקורת",
                    "actual_response": "עצירה ובחירה",
                    **se,
                }
            )

        monthly_full = run_monthly_cycle(
            MonthlyCycleRequest(
                user_id="moshe",
                minimum_events_required=5,
                proposed_policy_changes={"max_daily_minutes": 210},
            )
        )
        ma = monthly_full["mental_assessment"]
        self.assertTrue(ma["sufficient_data"])
        self.assertIn("data_quantity", ma)
        self.assertIn("data_quality", ma)
        self.assertIn("comparison_limitations", ma)
        self.assertIn("conclusion_confidence", ma)
        self.assertIsNotNone(monthly_full["pending_approval_request"])

        # --- Criterion 13 & 14: Mental privacy isolation & Playful points separated from Assessment ---
        sanitized = mental_svc.sanitize_payload_for_target_service(
            target_service="task_commander",
            payload={"title": "משימה", "trigger_text": "סודי", "initial_emotion_intensity": 8},
        )
        self.assertNotIn("trigger_text", sanitized)
        self.assertNotIn("initial_emotion_intensity", sanitized)
        self.assertEqual(sanitized["title"], "משימה")

        playful = growth_svc.get_playful_state(user_id="moshe")
        self.assertFalse(playful["is_diagnostic_or_assessment_metric"])
        self.assertEqual(playful["penalties_count"], 0)

        # --- Criterion 15 & 16: Deterministic actions run with 0 LLM calls and continue working when LLM is unavailable ---
        qc_offline = process_quick_capture(
            QuickCaptureRequest(
                user_id="moshe",
                text="ניצחון שקט: עצרתי לפני תגובה אוטומטית בשיחה",
                channel="voice",
                speech_seconds=6,
                tts_seconds=4,
                llm_available=False,
            )
        )
        self.assertTrue(qc_offline["success"])
        self.assertFalse(qc_offline["llm_used"])
        self.assertEqual(qc_offline["handled_by"], "deterministic_parser")
        self.assertEqual(qc_offline["speech_logs_recorded"], 2)

        ai_summary = repo.get_ai_usage_summary("moshe")
        self.assertEqual(ai_summary["llm_call_count"], 0)
        self.assertGreater(ai_summary["speech_stt_tts_call_count"], 0)
        self.assertGreater(ai_summary["deterministic_bypass_count"], 0)

        # --- Criterion 17: When rules_engine is unavailable, Compass marks status and does not run local shadow rules ---
        with patch("app.services.rules_engine.RulesEngineAdapter.evaluate_event", return_value={"connected": False, "warning": "offline"}), patch(
            "app.services.rules_engine.RulesEngineAdapter.evaluate", return_value={"connected": False, "warning": "offline"}
        ):
            offline_plan = run_morning_cycle(
                MorningCycleRequest(user_id="moshe", date=date.today() + timedelta(days=1))
            )
            self.assertEqual(offline_plan["daily_plan"]["status"], "rules_engine_unavailable")

        # --- Criteria 18, 19, 20, 21, 22: Control Center transparency, explainability, cancel decision, rule rollback, Planner/Executor ---
        overview = get_control_center_overview(user_id="moshe")
        self.assertGreaterEqual(overview["rules_summary"]["total_rules"], 20)
        rule_ids = {r["rule_id"] for r in overview["rules_catalog"]}
        for expected_id in ("FROG-001", "FROG-002", "FROG-003", "FROG-004", "HABIT-001", "MENTAL-001", "MENTAL-002", "MENTAL-003", "ASSESS-001", "ASSESS-002", "GROWTH-001", "GROWTH-002", "CHALLENGE-001", "CHALLENGE-002", "PLAN-001", "PLAN-002", "AI-001", "AI-002", "CONTROL-001", "CONTROL-002"):
            self.assertIn(expected_id, rule_ids)
        self.assertGreater(len(overview["recent_decisions"]), 0)

        # Criterion 19: Every decision has a full deterministic explanation
        decision_id = overview["recent_decisions"][0]["decision_id"]
        explained = explain_rule_decision(decision_id)
        self.assertTrue(explained["success"])
        self.assertIn("הכלל המוביל שהופעל", explained["readable_explanation_he"])

        # Criterion 20: User can cancel a decision before execution or require approval
        cancelled = cancel_decision_before_execution(
            decision_id, CancelDecisionRequest(user_id="moshe", reason="בדיקת ביטול החלטה")
        )
        self.assertEqual(cancelled["decision"]["final_decision"], "cancelled")

        pol_approval = update_user_autonomy_policy(
            PolicyUpdateRequest(user_id="moshe", max_challenge_difficulty=8, approval_confirmed=False)
        )
        self.assertEqual(pol_approval["status"], "approval_required")

        # Criterion 21: Rule change saves a new version and supports full rollback
        upd_rule = update_catalog_rule(
            "FROG-001",
            RuleUpdateRequest(user_id="moshe", priority=98, change_note="בדיקת עדכון גרסה"),
        )
        self.assertGreaterEqual(upd_rule["rule"]["version"], 2)
        rb_rule = rollback_catalog_rule_version(
            "FROG-001",
            RuleRollbackRequest(user_id="moshe", target_version=1),
        )
        self.assertEqual(rb_rule["rule"]["priority"], 100)

        # Criterion 22: Executor mode cannot change policy or create routines without switching to Planner mode
        update_user_autonomy_policy(
            PolicyUpdateRequest(user_id="moshe", active_role="executor", approval_confirmed=True)
        )
        blocked_routine = routines_svc.create_routine(
            {
                "user_id": "moshe",
                "name": "הרגל שנחסם במצב מבצע",
                "domain": "physical",
            }
        )
        self.assertFalse(blocked_routine["success"])
        self.assertEqual(blocked_routine["status"], "planner_role_required")


if __name__ == "__main__":
    unittest.main()
