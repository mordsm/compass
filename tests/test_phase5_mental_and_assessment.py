from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path


class Phase5ProactiveMentalAndAssessmentTests(unittest.TestCase):
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

    def test_4_training_modes_partial_event_reporting_and_insufficient_data_guardrail(self) -> None:
        """Covers Sections 11, 12, Rule ASSESS-002 & Acceptance Criterion #10 (few events -> no unfounded trend conclusion; missing values != 0)."""
        from app.routers.mental_skills import (
            RecordMentalEventRequest,
            get_monthly_mental_assessment,
            get_proactive_catalog,
            record_proactive_mental_event,
        )

        cat = get_proactive_catalog()
        mode_ids = {m["mode_id"] for m in cat["training_modes"]}
        self.assertEqual(
            mode_ids,
            {"baseline_calm", "pre_event_prep", "realtime_intervention", "post_event_processing"},
        )

        # Record 1 partial event where curiosity_ability and recovery_duration_minutes are omitted (None)
        ev1 = record_proactive_mental_event(
            RecordMentalEventRequest(
                user_id="moshe",
                event_type="interpersonal_friction",
                short_description="אי-הסכמה קצרה בשיחה",
                trigger_text="ביקורת לא צפויה",
                initial_emotion_intensity=8,
                defensive_or_attack_urge=7,
                curiosity_ability=None,
                choice_ability=4,
                actual_response="עצרתי ל-3 שניות לפני תשובה",
                recovery_duration_minutes=None,
                idempotency_key="mental_ev_1",
            )
        )
        self.assertIsNone(ev1["event"]["curiosity_ability"])
        self.assertIsNone(ev1["event"]["recovery_duration_minutes"])

        # Acceptance Criterion #10: With only 1 event (< 5 required), monthly assessment refuses to infer a trend
        assess_early = get_monthly_mental_assessment(user_id="moshe", minimum_events=5)
        self.assertFalse(assess_early["sufficient_data"])
        self.assertEqual(assess_early["trend_status"], "insufficient_data")
        self.assertIsNone(assess_early["trend"])
        self.assertEqual(assess_early["data_quantity"]["field_sample_sizes"]["curiosity_ability"], 0)

    def test_longitudinal_trend_with_silent_wins_and_limitations(self) -> None:
        """Covers Section 12, Rule MENTAL-003 & Acceptance Criterion #11 (comparable events over time show trend with limitations & confidence)."""
        from app.routers.mental_skills import (
            RecordMentalEventRequest,
            WeeklySilentWinsCheckRequest,
            get_monthly_mental_assessment,
            record_proactive_mental_event,
            run_weekly_silent_wins_check,
        )

        # Earlier 3 events: higher initial intensity (8, 7, 8), higher recovery time (25, 20, 20), lower curiosity (3, 4, 4)
        early_samples = [
            (8, 8, 3, 3, 25),
            (7, 7, 4, 4, 20),
            (8, 7, 4, 4, 20),
        ]
        for idx, (init_e, urge, cur, choice, rec) in enumerate(early_samples, start=1):
            record_proactive_mental_event(
                RecordMentalEventRequest(
                    user_id="moshe",
                    occurred_at=f"2026-10-0{idx}T10:00:00Z",
                    event_type="interpersonal_friction",
                    trigger_text="עיכוב או שינוי בלו''ז",
                    initial_emotion_intensity=init_e,
                    defensive_or_attack_urge=urge,
                    curiosity_ability=cur,
                    choice_ability=choice,
                    recovery_duration_minutes=rec,
                    actual_response="תגובה מהירה",
                )
            )

        # Recent 2 events + 1 weekly Silent Win: lower initial intensity (5, 4, 2), faster recovery (8, 5, 2), higher curiosity (7, 8, 9)
        recent_samples = [
            (5, 4, 7, 7, 8),
            (4, 3, 8, 8, 5),
        ]
        for idx, (init_e, urge, cur, choice, rec) in enumerate(recent_samples, start=1):
            record_proactive_mental_event(
                RecordMentalEventRequest(
                    user_id="moshe",
                    occurred_at=f"2026-11-1{idx}T10:00:00Z",
                    event_type="interpersonal_friction",
                    trigger_text="עיכוב או שינוי בלו''ז",
                    initial_emotion_intensity=init_e,
                    defensive_or_attack_urge=urge,
                    curiosity_ability=cur,
                    choice_ability=choice,
                    recovery_duration_minutes=rec,
                    actual_response="עצירה ושאלת סקרנות",
                )
            )

        sw_res = run_weekly_silent_wins_check(
            WeeklySilentWinsCheckRequest(
                user_id="moshe",
                silent_wins=[
                    {
                        "occurred_at": "2026-11-20T12:00:00Z",
                        "event_type": "interpersonal_friction",
                        "short_description": "שינוי פתאומי בתוכנית שעבר בשלווה מלאה",
                        "trigger_text": "עיכוב או שינוי בלו''ז",
                        "initial_emotion_intensity": 2,
                        "defensive_or_attack_urge": 1,
                        "curiosity_ability": 9,
                        "choice_ability": 9,
                        "recovery_duration_minutes": 1,
                        "actual_response": "חיוך והתאמה רגועה",
                    }
                ],
                notes="בדיקה שבועית",
            )
        )
        self.assertEqual(sw_res["silent_wins_recorded_count"], 1)

        report = get_monthly_mental_assessment(user_id="moshe", minimum_events=5)
        self.assertTrue(report["sufficient_data"])
        self.assertEqual(report["trend_status"], "trend_identified")
        self.assertEqual(report["trend"]["direction"], "improving")
        self.assertLess(
            report["trend"]["initial_emotion_intensity"]["recent_avg"],
            report["trend"]["initial_emotion_intensity"]["early_avg"],
        )
        self.assertGreater(
            report["trend"]["curiosity_ability"]["recent_avg"],
            report["trend"]["curiosity_ability"]["early_avg"],
        )
        self.assertEqual(report["trend"]["silent_wins_count"], 1)
        self.assertTrue(len(report["comparison_limitations"]) >= 2)
        self.assertIn("אינה כלי אבחון", report["non_diagnostic_disclaimer"])

    def test_mental_data_privacy_isolation_from_operational_services(self) -> None:
        """Covers Acceptance Criterion #21: Mental event data is never exposed to operational services that do not need it."""
        from app.services.mental_skills import MentalSkillsService

        svc = MentalSkillsService()
        raw_context = {
            "user_id": "moshe",
            "title": "משימה יומית",
            "mental_events": [{"trigger_text": "אישי מאוד", "initial_emotion_intensity": 9}],
            "defensive_or_attack_urge": 8,
            "silent_wins": ["אירוע פרטי"],
        }

        for forbidden_target in ("task_commander", "mail_manager", "economic_manager", "administrative"):
            sanitized = svc.sanitize_payload_for_target_service(forbidden_target, raw_context)
            self.assertNotIn("mental_events", sanitized)
            self.assertNotIn("defensive_or_attack_urge", sanitized)
            self.assertNotIn("silent_wins", sanitized)
            self.assertEqual(sanitized["title"], "משימה יומית")


if __name__ == "__main__":
    unittest.main()
