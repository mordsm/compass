from __future__ import annotations

import os
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

RULES_ENGINE_ROOT = Path(__file__).resolve().parents[2] / "rules_engine"
if str(RULES_ENGINE_ROOT) not in sys.path:
    sys.path.insert(0, str(RULES_ENGINE_ROOT))

from compass_rules import evaluate_structured_event  # noqa: E402


class RulesGatewayTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)
        os.environ["COMPASS_DATABASE_URL"] = ""
        os.environ["COMPASS_DATABASE_PATH"] = str(Path(self.tmpdir.name) / "compass.db")
        os.environ["COMPASS_ACTIONS_API_KEY"] = "test-token"

        from app.config import get_settings

        get_settings.cache_clear()

    def test_structured_event_is_evaluated_stored_audited_and_idempotent(self):
        from app.database import db
        from app.database import init_db
        from app.routers.rules import evaluate_structured_rules_event
        from app.schemas.rules import StructuredRulesEventRequest
        from app.services.rules_engine import RulesEngineAdapter

        original = RulesEngineAdapter.evaluate_event

        def local_evaluate_event(_self, event, actor=None, dry_run=False):
            result = evaluate_structured_event(event, dry_run=dry_run)
            return {"connected": True, "result": result.model_dump(mode="json")}

        RulesEngineAdapter.evaluate_event = local_evaluate_event
        self.addCleanup(setattr, RulesEngineAdapter, "evaluate_event", original)

        payload = {
            "event_id": "evt_assessment_104",
            "event_type": "assessment_finding_created",
            "event_version": "1.0",
            "source": "personal_Assessment",
            "user_id": "moshe",
            "occurred_at": datetime(2026, 8, 6, 10, 0, tzinfo=timezone.utc).isoformat(),
            "payload": {
                "domain": "fitness",
                "finding_type": "aerobic_fitness_gap",
                "severity": "medium",
                "confidence": 0.87,
                "current_state": "low",
                "recommended_capability": "fitness_planning",
            },
            "idempotency_key": "rules-eval-evt-104",
            "dry_run": True,
        }

        init_db()
        first_body = evaluate_structured_rules_event(StructuredRulesEventRequest.model_validate(payload))
        second_body = evaluate_structured_rules_event(StructuredRulesEventRequest.model_validate(payload))

        self.assertEqual(first_body, second_body)
        self.assertEqual(first_body["final_decision"], "require_approval")
        self.assertTrue(any(route["component"] == "self_manage" for route in first_body["routes"]))
        self.assertTrue(first_body["blocked_actions"])

        with db() as conn:
            evaluations = conn.execute("select count(*) as count from rule_evaluations").fetchone()["count"]
            audits = conn.execute("select count(*) as count from audit_log where action = 'rules.evaluate'").fetchone()["count"]
            idempotency = conn.execute("select count(*) as count from idempotency_keys").fetchone()["count"]

        self.assertEqual(evaluations, 1)
        self.assertEqual(audits, 1)
        self.assertEqual(idempotency, 1)

    def test_assessment_workflow_creates_approval_and_self_manage_route(self):
        from app.database import db, init_db
        from app.routers.rules import run_assessment_finding_rules_workflow
        from app.schemas.rules import AssessmentFindingWorkflowRequest
        from app.services.self_management import SelfManagementAdapter

        original_today = SelfManagementAdapter.get_today
        original_reminder = SelfManagementAdapter.get_hourly_reminder
        original_domains = SelfManagementAdapter.list_domains
        SelfManagementAdapter.list_domains = lambda _self: {"connected": True, "result": []}
        SelfManagementAdapter.get_today = lambda _self: {"connected": True, "result": {"items": []}}
        SelfManagementAdapter.get_hourly_reminder = lambda _self: {"connected": True, "result": {"enabled": True}}
        self.addCleanup(setattr, SelfManagementAdapter, "list_domains", original_domains)
        self.addCleanup(setattr, SelfManagementAdapter, "get_today", original_today)
        self.addCleanup(setattr, SelfManagementAdapter, "get_hourly_reminder", original_reminder)

        init_db()
        request = AssessmentFindingWorkflowRequest(
            user_id="moshe",
            event_id="evt_assessment_105",
            occurred_at=datetime(2026, 8, 6, 10, 0, tzinfo=timezone.utc),
            idempotency_key="workflow-assessment-105",
            domain="fitness",
            finding_type="aerobic_fitness_gap",
            severity="medium",
            confidence=0.87,
            current_state="low",
            evidence=["low endurance score"],
            recommended_capability="fitness_planning",
            dry_run=False,
        )

        result = run_assessment_finding_rules_workflow(request)

        self.assertEqual(result["status"], "approval_required")
        self.assertIsNotNone(result["approval_request_id"])
        self.assertEqual(result["self_manage_route"]["component"], "self_manage")
        self.assertEqual(result["rules_result"]["final_decision"], "require_approval")
        self.assertTrue(result["rules_result"]["blocked_actions"])

        with db() as conn:
            approvals = conn.execute("select count(*) as count from approval_requests").fetchone()["count"]
            evaluations = conn.execute("select count(*) as count from rule_evaluations").fetchone()["count"]

        self.assertEqual(approvals, 1)
        self.assertEqual(evaluations, 1)

    def test_assessment_workflow_does_not_execute_self_manage_without_approval(self):
        from app.database import init_db
        from app.routers.rules import run_assessment_finding_rules_workflow
        from app.schemas.rules import AssessmentFindingWorkflowRequest
        from app.services.self_management import SelfManagementAdapter

        generate_calls = []
        original_today = SelfManagementAdapter.get_today
        original_reminder = SelfManagementAdapter.get_hourly_reminder
        original_generate = SelfManagementAdapter.generate_today
        original_domains = SelfManagementAdapter.list_domains
        original_exercises = SelfManagementAdapter.list_cardio_candidates
        SelfManagementAdapter.list_domains = lambda _self: {
            "connected": True,
            "result": [
                {"kind": "physical", "slug": "cardio"},
                {"kind": "physical", "slug": "strength"},
                {"kind": "physical", "slug": "qigong"},
            ],
        }
        SelfManagementAdapter.list_cardio_candidates = lambda _self: {
            "connected": True,
            "result": [
                {
                    "kind": "physical",
                    "domain": {"slug": "cardio"},
                    "is_active": True,
                    "measurement": "RPE 1-5",
                }
            ],
        }
        SelfManagementAdapter.get_today = lambda _self: {"connected": True, "result": {"items": []}}
        SelfManagementAdapter.get_hourly_reminder = lambda _self: {"connected": True, "result": {"enabled": True}}
        SelfManagementAdapter.generate_today = lambda _self, **kwargs: generate_calls.append(kwargs)
        self.addCleanup(setattr, SelfManagementAdapter, "list_domains", original_domains)
        self.addCleanup(setattr, SelfManagementAdapter, "list_cardio_candidates", original_exercises)
        self.addCleanup(setattr, SelfManagementAdapter, "get_today", original_today)
        self.addCleanup(setattr, SelfManagementAdapter, "get_hourly_reminder", original_reminder)
        self.addCleanup(setattr, SelfManagementAdapter, "generate_today", original_generate)

        init_db()
        request = AssessmentFindingWorkflowRequest(
            user_id="moshe",
            event_id="evt_assessment_106",
            occurred_at=datetime(2026, 8, 6, 10, 0, tzinfo=timezone.utc),
            idempotency_key="workflow-assessment-106",
            domain="fitness",
            finding_type="aerobic_fitness_gap",
            severity="medium",
            confidence=0.87,
            current_state="low",
            evidence=["low endurance score"],
            recommended_capability="fitness_planning",
            dry_run=False,
            execute_self_manage=True,
        )

        result = run_assessment_finding_rules_workflow(request)

        self.assertEqual(result["status"], "approval_required")
        self.assertEqual(result["executed_actions"], [])
        self.assertEqual(generate_calls, [])
        self.assertIn("cognitive", result["self_manage_profile"]["excluded_kinds"])
        self.assertIn("strength", result["self_manage_profile"]["excluded_domains"])
        self.assertIn("qigong", result["self_manage_profile"]["excluded_domains"])
        self.assertTrue(any("requires approval" in warning for warning in result["warnings"]))

    def test_assessment_workflow_executes_cardio_self_manage_after_approval(self):
        from app.database import db, init_db
        from app.routers.rules import run_assessment_finding_rules_workflow
        from app.schemas.rules import AssessmentFindingWorkflowRequest
        from app.services.self_management import SelfManagementAdapter

        generate_calls = []
        original_today = SelfManagementAdapter.get_today
        original_reminder = SelfManagementAdapter.get_hourly_reminder
        original_generate = SelfManagementAdapter.generate_today
        original_domains = SelfManagementAdapter.list_domains
        original_open = SelfManagementAdapter.open_ui
        original_exercises = SelfManagementAdapter.list_cardio_candidates
        SelfManagementAdapter.list_domains = lambda _self: {
            "connected": True,
            "result": [
                {"kind": "physical", "slug": "cardio"},
                {"kind": "physical", "slug": "strength"},
                {"kind": "physical", "slug": "qigong"},
            ],
        }
        SelfManagementAdapter.list_cardio_candidates = lambda _self: {
            "connected": True,
            "result": [
                {
                    "kind": "physical",
                    "domain": {"slug": "cardio"},
                    "is_active": True,
                    "measurement": "RPE 1-5",
                }
            ],
        }
        SelfManagementAdapter.get_today = lambda _self: {"connected": True, "result": {"items": []}}
        SelfManagementAdapter.get_hourly_reminder = lambda _self: {"connected": True, "result": {"enabled": True}}

        def generate_today(_self, profile=None, overwrite=True):
            generate_calls.append({"profile": profile, "overwrite": overwrite})
            return {
                "connected": True,
                "result": {
                    "plan_id": 77,
                    "plan_date": "2026-08-06",
                    "items": [
                        {
                            "kind": "physical",
                            "domain": {"slug": "cardio", "label": "Cardio"},
                            "plan_item_id": 123,
                            "exercise": {
                                "id": 10,
                                "slug": "brisk_walk",
                                "label": "Brisk walk",
                                "minutes_default": 20,
                                "how_to": ["walk"],
                                "measurement": "RPE 1-10",
                            },
                        }
                    ]
                },
            }

        SelfManagementAdapter.generate_today = generate_today
        SelfManagementAdapter.open_ui = lambda _self, plan_item_id=None: {
            "opened": True,
            "url": f"http://127.0.0.1:8001/static/session.html?plan_item_id={plan_item_id}",
            "open_method": "test.open_ui",
            "urls": {
                "today": "http://127.0.0.1:8001/static/index.html",
                "session": f"http://127.0.0.1:8001/static/session.html?plan_item_id={plan_item_id}",
            },
        }
        self.addCleanup(setattr, SelfManagementAdapter, "list_domains", original_domains)
        self.addCleanup(setattr, SelfManagementAdapter, "list_cardio_candidates", original_exercises)
        self.addCleanup(setattr, SelfManagementAdapter, "get_today", original_today)
        self.addCleanup(setattr, SelfManagementAdapter, "get_hourly_reminder", original_reminder)
        self.addCleanup(setattr, SelfManagementAdapter, "generate_today", original_generate)
        self.addCleanup(setattr, SelfManagementAdapter, "open_ui", original_open)

        init_db()
        request = AssessmentFindingWorkflowRequest(
            user_id="moshe",
            event_id="evt_assessment_107",
            occurred_at=datetime(2026, 8, 6, 10, 0, tzinfo=timezone.utc),
            idempotency_key="workflow-assessment-107",
            domain="fitness",
            finding_type="aerobic_fitness_gap",
            severity="medium",
            confidence=0.87,
            current_state="low",
            evidence=["low endurance score"],
            recommended_capability="fitness_planning",
            dry_run=False,
            execute_self_manage=True,
            approval_confirmed=True,
            open_ui=True,
        )

        result = run_assessment_finding_rules_workflow(request)

        self.assertEqual(result["status"], "self_manage_executed")
        self.assertEqual(len(generate_calls), 1)
        self.assertEqual(generate_calls[0]["profile"]["excluded_kinds"], ["cognitive", "mental"])
        self.assertIn("strength", generate_calls[0]["profile"]["excluded_domains"])
        self.assertIn("qigong", generate_calls[0]["profile"]["excluded_domains"])
        self.assertEqual(generate_calls[0]["profile"]["required_measurement_terms"], ["rpe"])
        self.assertTrue(result["executed_actions"])
        self.assertEqual(result["executed_actions"][0]["purpose"], "create_aerobic_cardio_plan")
        self.assertEqual(result["self_manage_plan"]["plan_id"], 77)
        self.assertEqual(result["self_manage_plan"]["selected_plan_item_id"], 123)
        self.assertEqual(result["self_manage_plan"]["selected_exercise"]["label"], "Brisk walk")
        self.assertEqual(result["self_manage_plan"]["session_url"], "http://127.0.0.1:8001/static/session.html?plan_item_id=123")
        self.assertEqual(result["ui_url"], "http://127.0.0.1:8001/static/session.html?plan_item_id=123")
        self.assertTrue(result["ui_opened"])
        self.assertEqual(result["ui_open_method"], "test.open_ui")

        with db() as conn:
            approvals = conn.execute("select count(*) as count from approval_requests").fetchone()["count"]

        self.assertEqual(approvals, 0)

    def test_assessment_workflow_executes_mental_self_manage_after_approval(self):
        from app.database import init_db
        from app.routers.rules import run_assessment_finding_rules_workflow
        from app.schemas.rules import AssessmentFindingWorkflowRequest
        from app.services.self_management import SelfManagementAdapter

        generate_calls = []
        original_today = SelfManagementAdapter.get_today
        original_reminder = SelfManagementAdapter.get_hourly_reminder
        original_generate = SelfManagementAdapter.generate_today
        original_domains = SelfManagementAdapter.list_domains
        original_open = SelfManagementAdapter.open_ui
        original_exercises = SelfManagementAdapter.list_exercises
        SelfManagementAdapter.list_domains = lambda _self: {"connected": True, "result": []}
        SelfManagementAdapter.list_exercises = lambda _self: {
            "connected": True,
            "result": [
                {
                    "kind": "mental",
                    "domain": {"slug": "stress_regulation"},
                    "is_active": True,
                    "measurement": "before/after stress",
                }
            ],
        }
        SelfManagementAdapter.get_today = lambda _self: {"connected": True, "result": {"items": []}}
        SelfManagementAdapter.get_hourly_reminder = lambda _self: {"connected": True, "result": {"enabled": True}}

        def generate_today(_self, profile=None, overwrite=True):
            generate_calls.append({"profile": profile, "overwrite": overwrite})
            return {
                "connected": True,
                "result": {
                    "plan_id": 88,
                    "plan_date": "2026-08-11",
                    "items": [
                        {
                            "kind": "mental",
                            "domain": {"slug": "stress_regulation", "label": "Stress Regulation"},
                            "plan_item_id": 456,
                            "exercise": {
                                "id": 21,
                                "slug": "if_then_plan",
                                "label": "If-Then plan",
                                "minutes_default": 6,
                                "how_to": ["choose trigger", "choose response"],
                                "measurement": "before/after stress",
                            },
                        }
                    ],
                },
            }

        SelfManagementAdapter.generate_today = generate_today
        SelfManagementAdapter.open_ui = lambda _self, plan_item_id=None: {
            "opened": True,
            "url": f"http://127.0.0.1:8001/static/session.html?plan_item_id={plan_item_id}",
            "open_method": "test.open_ui",
            "urls": {
                "today": "http://127.0.0.1:8001/static/index.html",
                "session": f"http://127.0.0.1:8001/static/session.html?plan_item_id={plan_item_id}",
            },
        }
        self.addCleanup(setattr, SelfManagementAdapter, "list_domains", original_domains)
        self.addCleanup(setattr, SelfManagementAdapter, "list_exercises", original_exercises)
        self.addCleanup(setattr, SelfManagementAdapter, "get_today", original_today)
        self.addCleanup(setattr, SelfManagementAdapter, "get_hourly_reminder", original_reminder)
        self.addCleanup(setattr, SelfManagementAdapter, "generate_today", original_generate)
        self.addCleanup(setattr, SelfManagementAdapter, "open_ui", original_open)

        init_db()
        request = AssessmentFindingWorkflowRequest(
            user_id="moshe",
            event_id="evt_assessment_mental_101",
            occurred_at=datetime(2026, 8, 11, 10, 0, tzinfo=timezone.utc),
            idempotency_key="workflow-assessment-mental-101",
            domain="mental",
            finding_type="self_regulation_gap",
            severity="medium",
            confidence=0.86,
            current_state="strained",
            evidence=["low sense of control under load"],
            recommended_capability="mental_training",
            dry_run=False,
            execute_self_manage=True,
            approval_confirmed=True,
            open_ui=True,
        )

        result = run_assessment_finding_rules_workflow(request)

        self.assertEqual(result["status"], "self_manage_executed")
        self.assertEqual(generate_calls[0]["profile"]["excluded_kinds"], ["cognitive", "physical"])
        self.assertEqual(result["executed_actions"][0]["purpose"], "create_mental_self_manage_plan")
        self.assertEqual(result["self_manage_plan"]["selected_plan_item_id"], 456)
        self.assertEqual(result["self_manage_plan"]["selected_exercise"]["slug"], "if_then_plan")
        self.assertEqual(result["ui_url"], "http://127.0.0.1:8001/static/session.html?plan_item_id=456")
        self.assertTrue(result["ui_opened"])

    def test_assessment_workflow_reports_missing_cardio_content(self):
        from app.database import init_db
        from app.routers.rules import run_assessment_finding_rules_workflow
        from app.schemas.rules import AssessmentFindingWorkflowRequest
        from app.services.self_management import SelfManagementAdapter

        generate_calls = []
        original_today = SelfManagementAdapter.get_today
        original_reminder = SelfManagementAdapter.get_hourly_reminder
        original_generate = SelfManagementAdapter.generate_today
        original_domains = SelfManagementAdapter.list_domains
        original_exercises = SelfManagementAdapter.list_cardio_candidates
        SelfManagementAdapter.list_domains = lambda _self: {
            "connected": True,
            "result": [{"kind": "physical", "slug": "cardio"}],
        }
        SelfManagementAdapter.list_cardio_candidates = lambda _self: {
            "connected": True,
            "result": [
                {
                    "kind": "physical",
                    "domain": {"slug": "cardio"},
                    "is_active": True,
                    "measurement": "Stability 1-5",
                }
            ],
        }
        SelfManagementAdapter.get_today = lambda _self: {"connected": True, "result": {"items": []}}
        SelfManagementAdapter.get_hourly_reminder = lambda _self: {"connected": True, "result": {"enabled": True}}
        SelfManagementAdapter.generate_today = lambda _self, **kwargs: generate_calls.append(kwargs)
        self.addCleanup(setattr, SelfManagementAdapter, "list_domains", original_domains)
        self.addCleanup(setattr, SelfManagementAdapter, "list_cardio_candidates", original_exercises)
        self.addCleanup(setattr, SelfManagementAdapter, "get_today", original_today)
        self.addCleanup(setattr, SelfManagementAdapter, "get_hourly_reminder", original_reminder)
        self.addCleanup(setattr, SelfManagementAdapter, "generate_today", original_generate)

        init_db()
        request = AssessmentFindingWorkflowRequest(
            user_id="moshe",
            event_id="evt_assessment_108",
            occurred_at=datetime(2026, 8, 6, 10, 0, tzinfo=timezone.utc),
            idempotency_key="workflow-assessment-108",
            domain="fitness",
            finding_type="aerobic_fitness_gap",
            severity="medium",
            confidence=0.87,
            current_state="low",
            evidence=["low endurance score"],
            recommended_capability="fitness_planning",
            dry_run=False,
            execute_self_manage=True,
            approval_confirmed=True,
        )

        result = run_assessment_finding_rules_workflow(request)

        self.assertEqual(result["status"], "self_manage_content_needed")
        self.assertEqual(result["executed_actions"], [])
        self.assertEqual(generate_calls, [])
        self.assertTrue(result["self_manage_plan"]["content_needed"])
        self.assertEqual(result["self_manage_plan"]["missing_capability"], "aerobic_cardio_exercise")
        self.assertIn("suggested_search_query", result["self_manage_plan"])


if __name__ == "__main__":
    unittest.main()
