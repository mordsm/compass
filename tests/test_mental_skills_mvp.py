from __future__ import annotations

import os
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path


class MentalSkillsMvpTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)
        os.environ["COMPASS_DATABASE_URL"] = ""
        os.environ["COMPASS_DATABASE_PATH"] = str(Path(self.tmpdir.name) / "compass.db")
        os.environ["COMPASS_ACTIONS_API_KEY"] = "test-token"

        from app.config import get_settings

        get_settings.cache_clear()

    def test_context_seeds_mvp_skills_and_recommends_pause(self):
        from app.database import init_db
        from app.services.mental_skills import MentalSkillsService

        init_db()
        service = MentalSkillsService()

        context = service.user_context("moshe")
        skills = service.list_skills("moshe")

        self.assertEqual(context["recommended_skill_id"], "PAUSE")
        self.assertEqual(len(skills["skills"]), 3)
        self.assertEqual({skill["skill_id"] for skill in skills["skills"]}, {"PAUSE", "FRUSTRATION_TOLERANCE", "AROUSAL_REGULATION"})
        self.assertEqual(context["difficulty"], 1)

    def test_start_session_is_idempotent(self):
        from app.database import init_db
        from app.services.mental_skills import MentalSkillsService

        init_db()
        service = MentalSkillsService()
        payload = {
            "idempotency_key": "start-pause-1",
            "user_id": "moshe",
            "skill_id": "PAUSE",
            "mode": "TRAINING_MODE",
            "difficulty": 1,
        }

        first = service.start_session(payload)
        second = service.start_session(payload)

        self.assertEqual(first["session_id"], second["session_id"])
        self.assertFalse(first["already_existed"])
        self.assertTrue(second["already_existed"])
        self.assertEqual(first["exercise_id"], "pause_wait_three_seconds")

    def test_user_stop_event_marks_session_stopped(self):
        from app.database import init_db
        from app.services.mental_skills import MentalSkillsService

        init_db()
        service = MentalSkillsService()
        session = service.start_session(
            {
                "idempotency_key": "start-stop-1",
                "user_id": "moshe",
                "skill_id": "PAUSE",
                "mode": "TRAINING_MODE",
                "difficulty": 1,
            }
        )

        event = service.record_event(
            session["session_id"],
            {
                "idempotency_key": "event-stop-1",
                "event_type": "user_stop",
                "occurred_at": datetime(2026, 9, 7, 10, 0, tzinfo=timezone.utc).isoformat(),
                "payload": {"reason": "user asked to stop"},
            },
        )
        stored = service.skill_history("moshe", "PAUSE")["history"][0]

        self.assertEqual(event["safety_state"], "stopped")
        self.assertEqual(stored["status"], "stopped")
        self.assertEqual(stored["safety_state"], "stopped")

    def test_complete_session_updates_progress_and_is_idempotent(self):
        from app.database import init_db
        from app.services.mental_skills import MentalSkillsService

        init_db()
        service = MentalSkillsService()
        session = service.start_session(
            {
                "idempotency_key": "start-complete-1",
                "user_id": "moshe",
                "skill_id": "PAUSE",
                "mode": "TRAINING_MODE",
                "difficulty": 1,
            }
        )
        payload = {
            "idempotency_key": "complete-pause-1",
            "summary": "Practiced waiting before responding.",
            "user_noticed_change": True,
            "safety_state": "ok",
        }

        first = service.complete_session(session["session_id"], payload)
        second = service.complete_session(session["session_id"], payload)
        progress = service.progress("moshe")
        pause = next(skill for skill in progress["skills"] if skill["skill_id"] == "PAUSE")

        self.assertEqual(first, second)
        self.assertEqual(first["status"], "completed")
        self.assertEqual(first["summary"], "Practiced waiting before responding.")
        self.assertEqual(pause["sessions_count"], 1)
        self.assertEqual(pause["trend"], "collecting_evidence")

    def test_msp_router_is_available_through_fastapi_with_auth(self):
        from app.main import create_app

        app = create_app()
        paths = set(app.openapi()["paths"])

        self.assertIn("/api/msp/user/context", paths)
        self.assertIn("/api/msp/sessions/start", paths)
        self.assertIn("/api/msp/progress", paths)


if __name__ == "__main__":
    unittest.main()
