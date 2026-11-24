from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path


class Phase4GrowthChallengesAndPlayTests(unittest.TestCase):
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

    def test_domain_hierarchy_ai_cognitive_coverage_and_neglected_core_domain_intervention(self) -> None:
        """Covers Section 4, Rules GROWTH-001/002 & Acceptance Criterion #9 (neglected core domain triggers intervention proposal)."""
        from app.routers.growth import (
            RecordDomainActivityRequest,
            UpsertDomainRequest,
            check_neglected_domains,
            list_growth_domains,
            record_domain_activity,
            upsert_growth_domain,
        )

        doms = list_growth_domains(user_id="moshe")
        self.assertEqual(len(doms["core_domains"]), 3)
        self.assertEqual(len(doms["enrichment_domains"]), 4)
        # Enrichment weight must be strictly less than Core weight (4 vs 10)
        self.assertTrue(all(d["tier_weight"] == 10 for d in doms["core_domains"]))
        self.assertTrue(all(d["tier_weight"] < 10 for d in doms["enrichment_domains"]))

        # Importance vs intervention_level distinction
        upd = upsert_growth_domain(
            UpsertDomainRequest(
                user_id="moshe",
                slug="cooking",
                tier="enrichment",
                importance=8,
                intervention_level="low",
            )
        )
        self.assertEqual(upd["domain"]["importance"], 8)
        self.assertEqual(upd["domain"]["intervention_level"], "low")
        self.assertLess(upd["domain"]["tier_weight"], 10)

        # Record 3 AI learning sessions -> cognitive development is covered by AI learning!
        for _ in range(3):
            record_domain_activity(RecordDomainActivityRequest(user_id="moshe", slug="ai_professional"))

        after_ai = list_growth_domains(user_id="moshe")
        self.assertTrue(after_ai["cognitive_covered_by_ai"])

        # Check neglected domains: mental and physical have no recent activity -> generates core intervention proposals (Acceptance Criterion #9)
        neglect = check_neglected_domains(user_id="moshe", neglect_threshold_days=7)
        self.assertEqual(neglect["neglected_core_count"], 2)
        neglected_core_slugs = {item["domain_slug"] for item in neglect["intervention_proposals"]}
        self.assertEqual(neglected_core_slugs, {"mental", "physical"})

    def test_adaptive_challenges_pain_blocks_load_increase_and_stagnation_detection(self) -> None:
        """Covers Section 8, Rules CHALLENGE-001/002 & Acceptance Criterion #7 (pain/limitation blocks automatic physical load increase)."""
        from app.routers.growth import (
            CreateChallengeRequest,
            EvaluateChallengeRequest,
            create_challenge,
            evaluate_challenge,
            get_playful_state,
        )

        chal = create_challenge(
            CreateChallengeRequest(
                user_id="moshe",
                domain_slug="physical",
                challenge_type="physical",
                title="אתגר מתח הדרגתי",
                goal="ביצוע 8 חזרות מתח נקיות",
                difficulty_level=3,
                max_approved_difficulty=4,
            )
        )["challenge"]

        # 1. Acceptance Criterion #7: User reports pain or limitation while requesting/qualifying for difficulty increase -> BLOCKED!
        res_pain = evaluate_challenge(
            chal["challenge_id"],
            EvaluateChallengeRequest(
                user_id="moshe",
                outcome="completed",
                pain_or_limitation=True,
                perceived_effort=3,
                requested_difficulty_delta=1,
                notes="כאב קל בכתף ימין",
            ),
        )
        self.assertTrue(res_pain["blocked_automatic_increase"])
        self.assertEqual(res_pain["applied_difficulty"], 3)
        self.assertEqual(res_pain["recommended_adjustment"], "temporary_pause")

        # 2. Normal progress (3 consecutive completions with low effort and no pain) -> increases difficulty from 3 to 4
        for _ in range(2):
            res_prog = evaluate_challenge(
                chal["challenge_id"],
                EvaluateChallengeRequest(
                    user_id="moshe",
                    outcome="completed",
                    pain_or_limitation=False,
                    perceived_effort=3,
                    resistance_level=6,
                ),
            )
        self.assertEqual(res_prog["recommended_adjustment"], "increase_difficulty")
        self.assertEqual(res_prog["applied_difficulty"], 4)

        # 3. Attempting to increase beyond max_approved_difficulty (4 -> 5) is blocked by CHALLENGE-002!
        res_cap = evaluate_challenge(
            chal["challenge_id"],
            EvaluateChallengeRequest(
                user_id="moshe",
                outcome="completed",
                pain_or_limitation=False,
                perceived_effort=2,
                requested_difficulty_delta=1,
            ),
        )
        self.assertTrue(res_cap["blocked_automatic_increase"])
        self.assertEqual(res_cap["applied_difficulty"], 4)

        # 4. 3 consecutive stalls -> detects stagnation and lowers difficulty
        for _ in range(3):
            res_stall = evaluate_challenge(
                chal["challenge_id"],
                EvaluateChallengeRequest(
                    user_id="moshe",
                    outcome="stalled",
                    pain_or_limitation=False,
                    perceived_effort=7,
                    resistance_level=5,
                ),
            )
        self.assertTrue(res_stall["stagnation_detected"])
        self.assertEqual(res_stall["applied_difficulty"], 3)

        # 5. Section 9: Playful points awarded for starting actions & overcoming resistance, strictly separated from Assessment
        play = get_playful_state(user_id="moshe")["playful_state"]
        self.assertGreater(play["action_start_points"], 0)
        self.assertGreater(play["resistance_mastery_points"], 0)
        self.assertEqual(play["penalties_count"], 0)
        self.assertFalse(play["is_diagnostic_or_assessment_metric"])


if __name__ == "__main__":
    unittest.main()
