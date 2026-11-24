from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Any
from uuid import uuid4

from app.database import db, json_dump, json_load, resource_id, utc_now
from app.repository import CompassRepository
from app.services.rules_engine import RulesEngineAdapter

SEED_GROWTH_DOMAINS: list[dict[str, Any]] = [
    {
        "slug": "mental",
        "name": "התפתחות מנטלית",
        "tier": "core",
        "tier_weight": 10,
        "long_term_goal": "מעבר מתגובתיות לפרואקטיביות, סקרנות במקום התגוננות, גמישות מחשבתית וויסות רגשי המשפיעים לטובה על מערכות יחסים.",
        "importance": 10,
        "intervention_level": "high",
        "current_level": 4,
        "desired_level": 8,
        "progress_metrics": ["עוצמת תגובה ראשונית", "זמן התאוששות", "יכולת סקרנות ובחירה", "הצלחות שקטות"],
        "desired_frequency_per_week": 5,
        "constraints": ["ללא שיפוטיות או אבחון פסיכולוגי"],
    },
    {
        "slug": "physical",
        "name": "התפתחות פיזית",
        "tier": "core",
        "tier_weight": 10,
        "long_term_goal": "כוח פונקציונלי (מתח ומשקולות), סיבולת לב-ריאה, שיווי משקל וגמישות לאורך שנים.",
        "importance": 10,
        "intervention_level": "high",
        "current_level": 5,
        "desired_level": 8,
        "progress_metrics": ["אימונים שבועיים", "עקביות מתח/כוח", "התאוששות וללא כאב"],
        "desired_frequency_per_week": 5,
        "constraints": ["אין להעלות עומס אוטומטית בעת כאב או מגבלת בטיחות"],
    },
    {
        "slug": "ai_professional",
        "name": "התפתחות מקצועית בתחום AI",
        "tier": "core",
        "tier_weight": 10,
        "long_term_goal": "שליטה מעמיקה בארכיטקטורת סוכנים, מערכות מבוססות כללים ומחקר AI יישומי.",
        "importance": 10,
        "intervention_level": "medium",
        "current_level": 6,
        "desired_level": 9,
        "progress_metrics": ["שעות עומק ב-AI", "ניסויים ופרויקטים פעילים", "למידת מושגים חדשים"],
        "desired_frequency_per_week": 5,
        "constraints": ["מכסה גם התפתחות קוגניטיבית כאשר קיימת פעילות מספקת"],
    },
    {
        "slug": "cooking",
        "name": "בישול בריא ויצירתי",
        "tier": "enrichment",
        "tier_weight": 4,
        "long_term_goal": "שליטה בטכניקות בישול בריאות וטעימות בהנאה ובנינוחות.",
        "importance": 6,
        "intervention_level": "low",
        "current_level": 5,
        "desired_level": 8,
        "progress_metrics": ["מנות חדשות שנוסו", "הנאה מתהליך הבישול"],
        "desired_frequency_per_week": 2,
        "constraints": [],
    },
    {
        "slug": "gardening",
        "name": "גינון",
        "tier": "enrichment",
        "tier_weight": 4,
        "long_term_goal": "טיפוח גינה עירונית פורייה ומרגיעה.",
        "importance": 5,
        "intervention_level": "low",
        "current_level": 4,
        "desired_level": 7,
        "progress_metrics": ["טיפול שבועי בצמחים", "מעקב צמיחה עונתי"],
        "desired_frequency_per_week": 2,
        "constraints": [],
    },
    {
        "slug": "music",
        "name": "נגינה",
        "tier": "enrichment",
        "tier_weight": 4,
        "long_term_goal": "תרגול נגינה קבוע מתוך סקרנות והנאה.",
        "importance": 5,
        "intervention_level": "low",
        "current_level": 3,
        "desired_level": 6,
        "progress_metrics": ["דקות תרגול שבועיות", "יצירות בתהליך"],
        "desired_frequency_per_week": 2,
        "constraints": [],
    },
    {
        "slug": "drawing",
        "name": "ציור ורישום",
        "tier": "enrichment",
        "tier_weight": 4,
        "long_term_goal": "פיתוח התבוננות ומיומנות רישום חופשית.",
        "importance": 5,
        "intervention_level": "low",
        "current_level": 3,
        "desired_level": 6,
        "progress_metrics": ["תרגולי רישום שבועיים"],
        "desired_frequency_per_week": 2,
        "constraints": [],
    },
]


class GrowthChallengesAndPlayService:
    """
    Phase 4 Deterministic Engine (Sections 4, 8, 9 of specification):
    1. Long-Term Goals & Domain Hierarchy (Core vs. Enrichment, separating domain importance from system intervention level,
       cognitive coverage via AI learning, and neglect detection `GROWTH-001/002`).
    2. Adaptive Challenges Engine (`CHALLENGE-001/002`, detecting progress vs. stagnation vs. overload, and blocking
       automatic physical load increases on pain/limitation or above approved bounds).
    3. Non-Competitive Playfulness (`playful_engagement_state` strictly separated from real assessment metrics).
    """

    # --- 1. Growth Domains & Long-Term Goals (Section 4) ---

    def ensure_seed_domains(self, user_id: str = "moshe") -> None:
        now = utc_now()
        next_eval = (date.today() + timedelta(days=30)).isoformat()
        with db() as conn:
            for item in SEED_GROWTH_DOMAINS:
                domain_id = f"dom_{user_id}_{item['slug']}"
                conn.execute(
                    """
                    insert or ignore into growth_domains
                    (domain_id, user_id, slug, name, tier, tier_weight, long_term_goal,
                     importance, intervention_level, current_level, desired_level,
                     progress_metrics_json, last_activity_at, current_challenge_id,
                     desired_frequency_per_week, weekly_activity_count,
                     constraints_json, next_evaluation_date, updated_at)
                    values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        domain_id,
                        user_id,
                        item["slug"],
                        item["name"],
                        item["tier"],
                        item["tier_weight"],
                        item["long_term_goal"],
                        item["importance"],
                        item["intervention_level"],
                        item["current_level"],
                        item["desired_level"],
                        json_dump(item["progress_metrics"]),
                        None,
                        None,
                        item["desired_frequency_per_week"],
                        0,
                        json_dump(item["constraints"]),
                        next_eval,
                        now,
                    ),
                )

    def list_domains(self, user_id: str = "moshe", tier: str | None = None) -> dict[str, Any]:
        self.ensure_seed_domains(user_id)
        with db() as conn:
            if tier in {"core", "enrichment"}:
                rows = conn.execute(
                    "select * from growth_domains where user_id = ? and tier = ? order by tier_weight desc, importance desc",
                    (user_id, tier),
                ).fetchall()
            else:
                rows = conn.execute(
                    "select * from growth_domains where user_id = ? order by tier_weight desc, importance desc, slug asc",
                    (user_id,),
                ).fetchall()
        domains = [self._domain_row(r) for r in rows]
        ai_domain = next((d for d in domains if d["slug"] == "ai_professional"), None)
        cognitive_covered_by_ai = bool(ai_domain and ai_domain["weekly_activity_count"] >= 3)
        return {
            "success": True,
            "user_id": user_id,
            "core_domains": [d for d in domains if d["tier"] == "core"],
            "enrichment_domains": [d for d in domains if d["tier"] == "enrichment"],
            "cognitive_covered_by_ai": cognitive_covered_by_ai,
            "cognitive_policy_note": (
                "פעילות הלמידה והעיסוק ב-AI מספקת גירוי קוגניטיבי מלא השבוע – אין צורך באימונים קוגניטיביים נפרדים."
                if cognitive_covered_by_ai
                else "ניתן לשלב אימון קוגניטיבי קצר או העמקת למידה ב-AI."
            ),
            "domains": domains,
        }

    def upsert_domain(self, payload: dict[str, Any]) -> dict[str, Any]:
        user_id = str(payload.get("user_id") or "moshe")
        self.ensure_seed_domains(user_id)
        slug = str(payload["slug"]).strip().lower()
        tier = str(payload.get("tier") or ("core" if slug in {"mental", "physical", "ai_professional"} else "enrichment"))
        # Section 4: Enrichment domains must never receive equal weight to core domains
        tier_weight = 10 if tier == "core" else min(5, int(payload.get("tier_weight", 4)))
        now = utc_now()
        domain_id = f"dom_{user_id}_{slug}"
        next_eval = str(payload.get("next_evaluation_date") or (date.today() + timedelta(days=30)).isoformat())

        with db() as conn:
            existing = conn.execute(
                "select * from growth_domains where user_id = ? and slug = ?",
                (user_id, slug),
            ).fetchone()
            if existing:
                conn.execute(
                    """
                    update growth_domains
                    set name = ?, tier = ?, tier_weight = ?, long_term_goal = ?,
                        importance = ?, intervention_level = ?, current_level = ?,
                        desired_level = ?, progress_metrics_json = ?,
                        desired_frequency_per_week = ?, constraints_json = ?,
                        next_evaluation_date = ?, updated_at = ?
                    where user_id = ? and slug = ?
                    """,
                    (
                        str(payload.get("name", existing["name"])),
                        tier,
                        tier_weight,
                        str(payload.get("long_term_goal", existing["long_term_goal"])),
                        int(payload.get("importance", existing["importance"])),
                        str(payload.get("intervention_level", existing["intervention_level"])),
                        int(payload.get("current_level", existing["current_level"])),
                        int(payload.get("desired_level", existing["desired_level"])),
                        json_dump(payload.get("progress_metrics", json_load(existing["progress_metrics_json"], []))),
                        int(payload.get("desired_frequency_per_week", existing["desired_frequency_per_week"])),
                        json_dump(payload.get("constraints", json_load(existing["constraints_json"], []))),
                        next_eval,
                        now,
                        user_id,
                        slug,
                    ),
                )
            else:
                conn.execute(
                    """
                    insert into growth_domains
                    (domain_id, user_id, slug, name, tier, tier_weight, long_term_goal,
                     importance, intervention_level, current_level, desired_level,
                     progress_metrics_json, last_activity_at, current_challenge_id,
                     desired_frequency_per_week, weekly_activity_count,
                     constraints_json, next_evaluation_date, updated_at)
                    values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        domain_id,
                        user_id,
                        slug,
                        str(payload.get("name") or slug),
                        tier,
                        tier_weight,
                        str(payload.get("long_term_goal") or ""),
                        int(payload.get("importance", 6)),
                        str(payload.get("intervention_level") or ("high" if tier == "core" else "low")),
                        int(payload.get("current_level", 3)),
                        int(payload.get("desired_level", 7)),
                        json_dump(payload.get("progress_metrics") or []),
                        None,
                        None,
                        int(payload.get("desired_frequency_per_week", 2)),
                        0,
                        json_dump(payload.get("constraints") or []),
                        next_eval,
                        now,
                    ),
                )
            row = conn.execute(
                "select * from growth_domains where user_id = ? and slug = ?",
                (user_id, slug),
            ).fetchone()
        return {"success": True, "domain": self._domain_row(row)}

    def record_domain_activity(self, user_id: str, slug: str, occurred_at: str | None = None) -> dict[str, Any]:
        self.ensure_seed_domains(user_id)
        ts = occurred_at or utc_now()
        with db() as conn:
            conn.execute(
                """
                update growth_domains
                set last_activity_at = ?, weekly_activity_count = weekly_activity_count + 1, updated_at = ?
                where user_id = ? and slug = ?
                """,
                (ts, ts, user_id, slug),
            )
            row = conn.execute(
                "select * from growth_domains where user_id = ? and slug = ?",
                (user_id, slug),
            ).fetchone()
        return {"success": True, "domain": self._domain_row(row) if row else None}

    def check_neglected_domains(self, user_id: str = "moshe", neglect_threshold_days: int = 7) -> dict[str, Any]:
        """
        Section 4, Rule GROWTH-002 & Acceptance Criterion #9:
        Detects neglected core domains and creates tailored intervention proposals.
        """
        repo = CompassRepository()
        all_domains = self.list_domains(user_id=user_id)["domains"]
        today = date.today()
        neglected: list[dict[str, Any]] = []
        interventions: list[dict[str, Any]] = []

        for d in all_domains:
            if d["last_activity_at"]:
                last_dt = date.fromisoformat(str(d["last_activity_at"])[:10])
                days_since = (today - last_dt).days
            else:
                days_since = 14

            if days_since >= neglect_threshold_days:
                event = {
                    "event_id": f"evt_growth_{uuid4().hex[:10]}",
                    "event_type": "growth_domain.check",
                    "event_version": "1.0",
                    "source": "compass.growth",
                    "user_id": user_id,
                    "occurred_at": datetime.now(timezone.utc).isoformat(),
                    "idempotency_key": f"growth_chk_{d['slug']}_{uuid4().hex[:8]}",
                    "payload": {
                        "slug": d["slug"],
                        "name": d["name"],
                        "tier": d["tier"],
                        "days_since_last_activity": days_since,
                        "intervention_level": d["intervention_level"],
                    },
                    "metadata": {"dry_run": False, "requested_actions": []},
                }
                eval_res = RulesEngineAdapter().evaluate_event(event, actor=user_id)
                rule_result = eval_res.get("result", {})
                if eval_res.get("connected") and rule_result:
                    repo.save_rule_evaluation(event, rule_result)

                neglected.append({**d, "days_since_last_activity": days_since})
                if d["tier"] == "core":
                    interventions.append(
                        {
                            "domain_slug": d["slug"],
                            "domain_name": d["name"],
                            "tier": "core",
                            "days_since_last_activity": days_since,
                            "intervention_level": d["intervention_level"],
                            "proposed_intervention_he": (
                                f"תחום הליבה '{d['name']}' לא תורגל {days_since} ימים. "
                                "מוצע לשבץ מחר בבוקר פעולת כניסה קצרה (5–10 דקות) או צפרדע מותאמת בתחום זה."
                            ),
                            "rule_evaluation_id": rule_result.get("evaluation_id"),
                        }
                    )

        return {
            "success": True,
            "user_id": user_id,
            "neglected_domains_count": len(neglected),
            "neglected_core_count": len(interventions),
            "neglected_domains": neglected,
            "intervention_proposals": interventions,
        }

    # --- 2. Challenges & Adaptive Challenge Progression (Section 8) ---

    def create_challenge(self, payload: dict[str, Any]) -> dict[str, Any]:
        user_id = str(payload.get("user_id") or "moshe")
        self.ensure_seed_domains(user_id)
        policy = CompassRepository().get_user_autonomy_policy(user_id)
        now = utc_now()
        challenge_id = str(payload.get("challenge_id") or resource_id("chal"))
        duration_days = int(payload.get("duration_days", 14))
        review_date = str(payload.get("review_date") or (date.today() + timedelta(days=duration_days)).isoformat())
        max_approved = min(
            int(payload.get("max_approved_difficulty", policy["max_challenge_difficulty"])),
            int(policy["max_challenge_difficulty"]),
        )
        difficulty = min(int(payload.get("difficulty_level", 3)), max_approved)

        with db() as conn:
            conn.execute(
                """
                insert into challenges
                (challenge_id, user_id, domain_slug, challenge_type, title, goal,
                 current_level, difficulty_level, max_approved_difficulty, duration_days,
                 start_condition, success_condition, progress_metric, constraints_json,
                 stop_condition, review_date, consecutive_completions, consecutive_stalls,
                 status, created_at, updated_at)
                values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    challenge_id,
                    user_id,
                    str(payload.get("domain_slug") or "physical"),
                    str(payload.get("challenge_type") or "physical"),
                    str(payload["title"]).strip(),
                    str(payload.get("goal") or payload["title"]),
                    int(payload.get("current_level", 1)),
                    difficulty,
                    max_approved,
                    duration_days,
                    str(payload.get("start_condition") or "אנרגיה >= 3 וללא כאב"),
                    str(payload.get("success_condition") or "3 השלמות עקביות"),
                    str(payload.get("progress_metric") or "חזרות / דקות איכות"),
                    json_dump(payload.get("constraints") or ["ללא כאב חד או עומס יתר"]),
                    str(payload.get("stop_condition") or "כאב, סחרחורת או בקשת עצירה"),
                    review_date,
                    0,
                    0,
                    "active",
                    now,
                    now,
                ),
            )
            conn.execute(
                "update growth_domains set current_challenge_id = ?, updated_at = ? where user_id = ? and slug = ?",
                (challenge_id, now, user_id, str(payload.get("domain_slug") or "physical")),
            )
        return {"success": True, "challenge": self.get_challenge(challenge_id)}

    def get_challenge(self, challenge_id: str) -> dict[str, Any] | None:
        with db() as conn:
            row = conn.execute("select * from challenges where challenge_id = ?", (challenge_id,)).fetchone()
        return self._challenge_row(row) if row else None

    def list_challenges(self, user_id: str = "moshe", status: str = "active") -> dict[str, Any]:
        with db() as conn:
            if status and status != "all":
                rows = conn.execute(
                    "select * from challenges where user_id = ? and status = ? order by created_at desc",
                    (user_id, status),
                ).fetchall()
            else:
                rows = conn.execute(
                    "select * from challenges where user_id = ? order by created_at desc",
                    (user_id,),
                ).fetchall()
        items = [self._challenge_row(r) for r in rows]
        return {"success": True, "user_id": user_id, "count": len(items), "challenges": items}

    def evaluate_and_adapt_challenge(
        self,
        challenge_id: str,
        *,
        user_id: str = "moshe",
        outcome: str,
        pain_or_limitation: bool = False,
        perceived_effort: int = 5,
        resistance_level: int = 4,
        requested_difficulty_delta: int = 0,
        notes: str | None = None,
    ) -> dict[str, Any]:
        """
        Section 8, Rules CHALLENGE-001, CHALLENGE-002 & Acceptance Criterion #7:
        Evaluates progress, stagnation, too-easy state, abnormal resistance, or overload/pain.
        NEVER automatically increases physical load when pain/limitation is reported or above approved bounds.
        """
        chal = self.get_challenge(challenge_id)
        if not chal:
            return {"success": False, "error": "challenge_not_found"}

        repo = CompassRepository()
        policy = repo.get_user_autonomy_policy(user_id)
        max_cap = min(chal["max_approved_difficulty"], policy["max_challenge_difficulty"])
        current_diff = chal["difficulty_level"]
        proposed_diff = current_diff + requested_difficulty_delta

        consec_comp = chal["consecutive_completions"] + 1 if outcome == "completed" else 0
        consec_stall = chal["consecutive_stalls"] + 1 if outcome in {"stalled", "failed", "not_done"} else 0
        stagnation_detected = consec_stall >= 3

        # Check if increase was requested or triggered while pain_or_limitation is True or proposed > max_cap
        wants_increase = requested_difficulty_delta > 0 or (consec_comp >= 3 and perceived_effort <= 4)
        candidate_new_diff = current_diff + 1 if wants_increase and requested_difficulty_delta == 0 else proposed_diff
        exceeds_safety_or_bounds = bool(
            (pain_or_limitation and (wants_increase or candidate_new_diff > current_diff))
            or candidate_new_diff > max_cap
        )

        event = {
            "event_id": f"evt_chal_{uuid4().hex[:10]}",
            "event_type": "challenge.evaluate",
            "event_version": "1.0",
            "source": "compass.challenges",
            "user_id": user_id,
            "occurred_at": datetime.now(timezone.utc).isoformat(),
            "idempotency_key": f"chal_eval_{uuid4().hex[:10]}",
            "payload": {
                "challenge_id": challenge_id,
                "domain_slug": chal["domain_slug"],
                "challenge_type": chal["challenge_type"],
                "outcome": outcome,
                "pain_or_limitation": pain_or_limitation,
                "perceived_effort": perceived_effort,
                "resistance_level": resistance_level,
                "current_difficulty": current_diff,
                "proposed_difficulty": candidate_new_diff,
                "max_approved_difficulty": max_cap,
                "exceeds_safety_or_approved_bounds": exceeds_safety_or_bounds,
                "stagnation_detected": stagnation_detected,
            },
            "metadata": {"dry_run": False, "requested_actions": []},
        }
        eval_res = RulesEngineAdapter().evaluate_event(event, actor=user_id)
        rule_result = eval_res.get("result", {})
        if eval_res.get("connected") and rule_result:
            repo.save_rule_evaluation(event, rule_result)

        # Determine adaptive recommendation & applied difficulty strictly within safety and approved bounds
        if pain_or_limitation:
            recommended_adjustment = "temporary_pause" if chal["challenge_type"] == "physical" else "decrease_difficulty"
            applied_difficulty = current_diff  # Never increase; keep or lower
            if requested_difficulty_delta < 0:
                applied_difficulty = max(1, current_diff - 1)
            status_note = "דווח על כאב או מגבלה (CHALLENGE-002): העלאת עומס נחסמה לחלוטין והאתגר הועבר למצב התאוששות/עצירה בטוחה."
        elif exceeds_safety_or_bounds:
            recommended_adjustment = "keep_level"
            applied_difficulty = min(current_diff, max_cap)
            status_note = f"הקושי המבוקש ({candidate_new_diff}) חורג מתקרת הקושי המאושרת ({max_cap}) ולכן נחסם (CHALLENGE-002)."
        elif stagnation_detected:
            recommended_adjustment = "replace_challenge" if resistance_level >= 8 else "decrease_difficulty"
            applied_difficulty = max(1, current_diff - 1)
            status_note = "זוהתה דריכה במקום (3 ניסיונות ללא התקדמות): רמת הקושי הופחתה ומוצע לגוון או להחליף את האתגר."
        elif resistance_level >= 8 or perceived_effort >= 9:
            recommended_adjustment = "decrease_difficulty"
            applied_difficulty = max(1, current_diff - 1)
            status_note = "זוהה עומס או התנגדות חריגה: הקושי הופחת בדרגה אחת לשמירה על רציפות."
        elif wants_increase and candidate_new_diff <= max_cap:
            recommended_adjustment = "increase_difficulty"
            applied_difficulty = candidate_new_diff
            status_note = f"התקדמות עקבית! רמת הקושי הועלתה מ-{current_diff} ל-{applied_difficulty} (בגבולות המאושרים: עד {max_cap})."
        else:
            recommended_adjustment = "keep_level"
            applied_difficulty = current_diff
            status_note = "שמירה על רמת הקושי הנוכחית להמשך ביסוס השליטה."

        now = utc_now()
        log_id = resource_id("chal_log")
        with db() as conn:
            conn.execute(
                """
                insert into challenge_logs
                (log_id, challenge_id, user_id, outcome, pain_or_limitation,
                 perceived_effort, resistance_level, recommended_adjustment,
                 applied_difficulty, notes, occurred_at)
                values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    log_id,
                    challenge_id,
                    user_id,
                    outcome,
                    1 if pain_or_limitation else 0,
                    perceived_effort,
                    resistance_level,
                    recommended_adjustment,
                    applied_difficulty,
                    notes,
                    now,
                ),
            )
            conn.execute(
                """
                update challenges
                set difficulty_level = ?,
                    consecutive_completions = ?,
                    consecutive_stalls = ?,
                    updated_at = ?
                where challenge_id = ?
                """,
                (applied_difficulty, consec_comp, consec_stall, now, challenge_id),
            )

        if outcome == "completed":
            self.record_domain_activity(user_id, chal["domain_slug"], occurred_at=now)
            self.award_playful_points(
                user_id=user_id,
                started_action=True,
                overcame_resistance=(resistance_level >= 6),
                explored_new=False,
            )

        return {
            "success": True,
            "log_id": log_id,
            "challenge": self.get_challenge(challenge_id),
            "recommended_adjustment": recommended_adjustment,
            "previous_difficulty": current_diff,
            "applied_difficulty": applied_difficulty,
            "blocked_automatic_increase": bool(pain_or_limitation or exceeds_safety_or_bounds),
            "stagnation_detected": stagnation_detected,
            "status_note_he": status_note,
            "rule_evaluation": rule_result,
        }

    # --- 3. Non-Competitive Playfulness & Motivation (Section 9) ---

    def get_playful_state(self, user_id: str = "moshe") -> dict[str, Any]:
        now = utc_now()
        with db() as conn:
            row = conn.execute("select * from playful_engagement_state where user_id = ?", (user_id,)).fetchone()
            if not row:
                conn.execute(
                    """
                    insert into playful_engagement_state
                    (user_id, action_start_points, resistance_mastery_points,
                     exploration_points, stage_level, flexible_active_days,
                     unlocked_achievements_json, updated_at)
                    values (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (user_id, 0, 0, 0, 1, 0, "[]", now),
                )
                row = conn.execute("select * from playful_engagement_state where user_id = ?", (user_id,)).fetchone()
        return self._playful_row(row)

    def award_playful_points(
        self,
        *,
        user_id: str = "moshe",
        started_action: bool = True,
        overcame_resistance: bool = False,
        explored_new: bool = False,
    ) -> dict[str, Any]:
        state = self.get_playful_state(user_id)
        now = utc_now()
        start_pts = state["action_start_points"] + (10 if started_action else 0)
        res_pts = state["resistance_mastery_points"] + (15 if overcame_resistance else 0)
        exp_pts = state["exploration_points"] + (20 if explored_new else 0)
        total = start_pts + res_pts + exp_pts
        stage_level = max(1, 1 + (total // 50))
        active_days = state["flexible_active_days"] + (1 if started_action else 0)

        achievements = list(state["unlocked_achievements"])
        if start_pts >= 10 and "צעד ראשון מתוך בחירה" not in achievements:
            achievements.append("צעד ראשון מתוך בחירה")
        if res_pts >= 15 and "פירוק התנגדות מודע" not in achievements:
            achievements.append("פירוק התנגדות מודע")
        if exp_pts >= 20 and "חוקר סקרן" not in achievements:
            achievements.append("חוקר סקרן")

        with db() as conn:
            conn.execute(
                """
                update playful_engagement_state
                set action_start_points = ?, resistance_mastery_points = ?,
                    exploration_points = ?, stage_level = ?, flexible_active_days = ?,
                    unlocked_achievements_json = ?, updated_at = ?
                where user_id = ?
                """,
                (start_pts, res_pts, exp_pts, stage_level, active_days, json_dump(achievements), now, user_id),
            )
        return self.get_playful_state(user_id)

    def _domain_row(self, row: Any) -> dict[str, Any]:
        return {
            "domain_id": row["domain_id"],
            "user_id": row["user_id"],
            "slug": row["slug"],
            "name": row["name"],
            "tier": row["tier"],
            "tier_weight": int(row["tier_weight"]),
            "long_term_goal": row["long_term_goal"],
            "importance": int(row["importance"]),
            "intervention_level": row["intervention_level"],
            "current_level": int(row["current_level"]),
            "desired_level": int(row["desired_level"]),
            "progress_metrics": json_load(row["progress_metrics_json"], []),
            "last_activity_at": row["last_activity_at"],
            "current_challenge_id": row["current_challenge_id"],
            "desired_frequency_per_week": int(row["desired_frequency_per_week"]),
            "weekly_activity_count": int(row["weekly_activity_count"]),
            "constraints": json_load(row["constraints_json"], []),
            "next_evaluation_date": row["next_evaluation_date"],
            "updated_at": row["updated_at"],
        }

    def _challenge_row(self, row: Any) -> dict[str, Any]:
        return {
            "challenge_id": row["challenge_id"],
            "user_id": row["user_id"],
            "domain_slug": row["domain_slug"],
            "challenge_type": row["challenge_type"],
            "title": row["title"],
            "goal": row["goal"],
            "current_level": int(row["current_level"]),
            "difficulty_level": int(row["difficulty_level"]),
            "max_approved_difficulty": int(row["max_approved_difficulty"]),
            "duration_days": int(row["duration_days"]),
            "start_condition": row["start_condition"],
            "success_condition": row["success_condition"],
            "progress_metric": row["progress_metric"],
            "constraints": json_load(row["constraints_json"], []),
            "stop_condition": row["stop_condition"],
            "review_date": row["review_date"],
            "consecutive_completions": int(row["consecutive_completions"]),
            "consecutive_stalls": int(row["consecutive_stalls"]),
            "status": row["status"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }

    def _playful_row(self, row: Any) -> dict[str, Any]:
        total = int(row["action_start_points"]) + int(row["resistance_mastery_points"]) + int(row["exploration_points"])
        return {
            "user_id": row["user_id"],
            "action_start_points": int(row["action_start_points"]),
            "resistance_mastery_points": int(row["resistance_mastery_points"]),
            "exploration_points": int(row["exploration_points"]),
            "total_playful_points": total,
            "stage_level": int(row["stage_level"]),
            "flexible_active_days": int(row["flexible_active_days"]),
            "unlocked_achievements": json_load(row["unlocked_achievements_json"], []),
            "penalties_count": 0,
            "is_diagnostic_or_assessment_metric": False,
            "separation_notice": "ניקוד זה נועד להנעה ומשחקיות אישית בלבד ואינו משמש כמדד להערכת התקדמות ב-Assessment.",
            "updated_at": row["updated_at"],
        }
