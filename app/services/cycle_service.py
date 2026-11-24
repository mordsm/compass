from __future__ import annotations

import re
from datetime import date, datetime, timezone
from typing import Any
from uuid import uuid4

from app.database import db, json_dump, json_load, resource_id, utc_now
from app.repository import CompassRepository
from app.schemas.daily_plan import SaveDailyPlanRequest
from app.routers.daily_plan import save_daily_plan
from app.services.frogs_service import FrogsService
from app.services.growth_service import GrowthChallengesAndPlayService
from app.services.mental_skills import MentalSkillsService
from app.services.routines_service import RoutinesAndExecutionService
from app.services.rules_engine import RulesEngineAdapter
from app.services.task_commander import TaskCommanderAdapter


class ProactiveCycleService:
    """
    Phase 6 Full Integration Orchestrator (Sections 13, 16, 17, 18, 19 of specification):
    1. Morning Cycle: energy & available time -> daily frog (`FROG-002`) -> mental & physical routines ->
       AI professional progress (`GROWTH-001`) -> active challenge -> TaskCommander operational tasks ->
       deterministic daily plan (`PLAN-001/002`).
    2. Intraday Cycle: Executor mode next-action, 6-step prep protocol (`MENTAL-001`), anti-spam reminder throttling.
    3. Evening Cycle: completed vs. open tasks summary, 4-frog pool check (`FROG-001`), wins & difficulties capture,
       next-day preparation.
    4. Weekly Cycle: consistency metrics, neglected core domains (`GROWTH-002`), adaptive challenge review
       (`CHALLENGE-001/002`), weekly Silent Wins check (`MENTAL-003`), next week adjustments.
    5. Monthly Cycle: multi-month mental & growth longitudinal assessment (`ASSESS-001/002`), stagnation detection,
       policy & goal update proposals requiring explicit approval (`CONTROL-001`).
    6. Voice & Text Quick-Capture (`AI-001/002`): deterministic command parser first (0 LLM tokens),
       separate STT/TTS vs. LLM cost logging, and full offline-LLM resilience (Acceptance Criterion #16).
    """

    def run_morning_cycle(
        self,
        *,
        user_id: str = "moshe",
        target_date: date | None = None,
        energy_level: int = 3,
        available_minutes: int = 180,
        outcomes: list[str] | None = None,
        extra_tasks: list[dict[str, Any]] | None = None,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        plan_date = target_date or date.today()
        repo = CompassRepository()
        frogs_svc = FrogsService()
        routines_svc = RoutinesAndExecutionService()
        growth_svc = GrowthChallengesAndPlayService()
        tc = TaskCommanderAdapter()

        # 1. Select Daily Frog (FROG-002)
        frog_selection = frogs_svc.select_daily_frog(
            user_id=user_id,
            target_date=plan_date,
            energy_level=energy_level,
            available_minutes=available_minutes,
            sync_to_task_commander=True,
        )

        # 2. Check Core Growth Domains & Cognitive Coverage via AI (GROWTH-001)
        domains_info = growth_svc.list_domains(user_id=user_id)
        cognitive_covered_by_ai = domains_info["cognitive_covered_by_ai"]

        # 3. Gather Active Routines (Mental, Physical, AI)
        active_routines = routines_svc.list_routines(user_id=user_id, status="active")["routines"]
        scheduled_tasks: list[dict[str, Any]] = []

        if frog_selection.get("selected") and frog_selection.get("selected_frog"):
            f = frog_selection["selected_frog"]
            scheduled_tasks.append(
                {
                    "title": f"🐸 צפרדע יומית: {f['name']}",
                    "frog_id": f["frog_id"],
                    "is_frog": True,
                    "category": "frog",
                    "domain": f["domain"],
                    "slot": frog_selection["recommended_slot"],
                    "minutes": f["estimated_minutes"],
                    "resistance_level": f["resistance_level"],
                }
            )

        for r in active_routines[:3]:
            use_min_viable = energy_level <= 2 or available_minutes <= 60
            full_text = r.get("name") or " -> ".join(r.get("action_sequence") or [])
            scheduled_tasks.append(
                {
                    "title": f"🔄 הרגל ({r['domain']}): {r['minimum_viable_version'] if use_min_viable else full_text}",
                    "routine_id": r["routine_id"],
                    "category": "routine",
                    "domain": r["domain"],
                    "slot": r.get("trigger_time_or_event") or "morning",
                    "minutes": r.get("minimum_minutes", 5) if use_min_viable else r.get("estimated_minutes", 15),
                    "version_used": "minimum_viable" if use_min_viable else "full",
                }
            )

        # Ensure Core Domains (Mental, Physical, AI) are represented in the morning plan
        existing_domains = {str(t.get("domain") or "").lower() for t in scheduled_tasks}
        if "mental" not in existing_domains:
            scheduled_tasks.append(
                {
                    "title": "🧘 אימון מנטלי פרואקטיבי קצר (מודעות לתחושות גוף וסקרנות)",
                    "category": "mental_training",
                    "domain": "mental",
                    "slot": "morning",
                    "minutes": 5,
                }
            )
        if "physical" not in existing_domains:
            scheduled_tasks.append(
                {
                    "title": "💪 פעילות גופנית יומית (מתח / כוח / תנועה בהתאם לאנרגיה)",
                    "category": "physical_training",
                    "domain": "physical",
                    "slot": "morning" if energy_level >= 3 else "afternoon",
                    "minutes": 10 if energy_level <= 2 else 20,
                }
            )
        if "ai_professional" not in existing_domains and "ai" not in existing_domains:
            scheduled_tasks.append(
                {
                    "title": "🤖 העמקה מקצועית ב-AI (מכסה גם גירוי קוגניטיבי)",
                    "category": "ai_learning",
                    "domain": "ai_professional",
                    "slot": "morning",
                    "minutes": 15 if energy_level <= 2 else 30,
                }
            )

        # 4. Active Adaptive Challenge
        active_challenges = growth_svc.list_challenges(user_id=user_id, status="active")["challenges"]
        selected_challenge = active_challenges[0] if active_challenges else None
        if selected_challenge:
            scheduled_tasks.append(
                {
                    "title": f"🎯 אתגר פעיל (רמה {selected_challenge['difficulty_level']}): {selected_challenge['title']}",
                    "challenge_id": selected_challenge["challenge_id"],
                    "category": "challenge",
                    "domain": selected_challenge["domain_slug"],
                    "slot": "afternoon",
                    "minutes": 15,
                }
            )

        # 5. Operational Tasks from TaskCommander
        tc_today = tc.today(user_id=user_id).get("items", [])
        for extra in extra_tasks or []:
            scheduled_tasks.append(extra)

        normalized_outcomes = [
            o if isinstance(o, dict) else {"title": str(o)}
            for o in (outcomes or ["ביצוע הצפרדע היומית מתוך בחירה", "שמירה על רצף תחומי ליבה (מנטלי, פיזי, AI)"])
        ]
        is_over = sum(int(t.get("minutes", 15)) for t in scheduled_tasks) > available_minutes
        normalized_risks = [{"risk": "עומס יתר", "severity": "high"} if is_over else {"risk": "ללא", "severity": "low"}]

        plan_request = SaveDailyPlanRequest(
            user_id=user_id,
            date=plan_date,
            energy_level=energy_level,
            available_minutes=available_minutes,
            outcomes=normalized_outcomes,
            scheduled_tasks=scheduled_tasks,
            deferred_items=[],
            risks=normalized_risks,
            status="approved",
            idempotency_key=idempotency_key,
        )
        plan_result = save_daily_plan(plan_request)

        telegram_text = (
            f"🌅 *תוכנית בוקר – {plan_date.isoformat()}*\n"
            f"⚡ אנרגיה: {energy_level}/5 | ⏱ זמן זמין: {available_minutes} דק׳\n"
            f"🐸 צפרדע יומית: {frog_selection['selected_frog']['name'] if frog_selection.get('selected_frog') else 'לא נבחרה'}\n"
            f"📋 משימות מתוזמנות: {len(scheduled_tasks)} | סטטוס תוכנית: `{plan_result['status']}`"
        )

        repo.log_ai_usage(
            {
                "user_id": user_id,
                "usage_type": "deterministic_bypass",
                "purpose": "cycles.morning",
                "reason": "Deterministic morning cycle orchestration (0 LLM tokens)",
            }
        )
        return {
            "success": True,
            "cycle": "morning",
            "user_id": user_id,
            "date": plan_date.isoformat(),
            "energy_level": energy_level,
            "available_minutes": available_minutes,
            "daily_frog": frog_selection,
            "cognitive_covered_by_ai": cognitive_covered_by_ai,
            "selected_challenge": selected_challenge,
            "task_commander_today_count": len(tc_today),
            "daily_plan": plan_result,
            "scheduled_tasks": scheduled_tasks,
            "telegram_summary_he": telegram_text,
        }

    def run_intraday_cycle(
        self,
        *,
        user_id: str = "moshe",
        target_date: date | None = None,
        energy_level: int = 3,
        available_minutes: int = 60,
        recent_unanswered_reminders: int = 0,
    ) -> dict[str, Any]:
        routines_svc = RoutinesAndExecutionService()
        next_action_info = routines_svc.get_executor_next_action(
            user_id=user_id,
            energy_level=energy_level,
            available_minutes=available_minutes,
        )

        # Section 17: Do not spam the user with reminders when previous reminders went unanswered
        reminder_throttled = recent_unanswered_reminders >= 2
        next_act = next_action_info.get("next_action")
        telegram_text = (
            "⏸ תזכורות הושהו אוטומטית כדי למנוע הצפה. כשתהיה פנוי, בקש את הפעולה הבאה."
            if reminder_throttled
            else (
                f"▶️ *הפעולה הבאה כעת ({next_action_info.get('role')}):*\n"
                f"{next_act['title'] if next_act else 'אין פעולה ממתינה כרגע.'}\n"
                f"💡 {next_act.get('instruction_he', '') if next_act else ''}"
            )
        )

        return {
            "success": True,
            "cycle": "intraday",
            "user_id": user_id,
            "reminder_throttled": reminder_throttled,
            "next_action_bundle": next_action_info,
            "telegram_summary_he": telegram_text,
        }

    def run_evening_cycle(
        self,
        *,
        user_id: str = "moshe",
        target_date: date | None = None,
        wins_today: list[str] | None = None,
        difficulties_today: list[str] | None = None,
        notes_for_tomorrow: str = "",
    ) -> dict[str, Any]:
        day = target_date or date.today()
        repo = CompassRepository()
        frogs_svc = FrogsService()
        tc = TaskCommanderAdapter()

        # 1. Check frog pool (FROG-001: minimum 4 active frogs without inventing frogs)
        frog_pool_check = frogs_svc.evening_pool_check(user_id=user_id)

        # 2. TaskCommander completed vs. open summary
        tc_status = tc.status(user_id=user_id)

        active_frogs_count = frog_pool_check["active_frogs_count"]
        min_req = frog_pool_check["minimum_required"]
        prompt_he = frog_pool_check.get("user_prompt_he") or ""

        # 3. Save evening reflection as conversation summary for tomorrow's context
        summary_text = (
            f"סיכום ערב {day.isoformat()}: הושלמו {tc_status.get('done_instances', 0)} משימות. "
            f"צפרדעים פעילות במאגר: {active_frogs_count}/{min_req}. "
            f"{notes_for_tomorrow}".strip()
        )
        summary_saved = repo.finalize_conversation(
            {
                "user_id": user_id,
                "conversation_id": f"evening_{day.isoformat()}",
                "summary": summary_text,
                "decisions": wins_today or [],
                "tasks": [],
                "open_questions": difficulties_today or [],
            }
        )

        telegram_text = (
            f"🌙 *סיכום ערב – {day.isoformat()}*\n"
            f"✅ משימות שהושלמו: {tc_status.get('done_instances', 0)} | פתוחות: {tc_status.get('pending_instances', 0)}\n"
            f"🐸 מאגר צפרדעים: {active_frogs_count}/{min_req} "
            f"({'נדרשת השלמת צפרדעים מהמשתמש' if frog_pool_check['replenishment_needed'] else 'מאגר תקין'})\n"
            f"📝 {prompt_he or 'המאגר מוכן למחר בבוקר.'}"
        )

        repo.log_ai_usage(
            {
                "user_id": user_id,
                "usage_type": "deterministic_bypass",
                "purpose": "cycles.evening",
                "reason": "Deterministic evening cycle & FROG-001 pool check (0 LLM tokens)",
            }
        )
        return {
            "success": True,
            "cycle": "evening",
            "user_id": user_id,
            "date": day.isoformat(),
            "frog_pool_check": frog_pool_check,
            "task_commander_summary": {
                "done_instances": tc_status.get("done_instances", 0),
                "pending_instances": tc_status.get("pending_instances", 0),
                "overdue_count": len(tc_status.get("overdue", [])),
            },
            "wins_today": wins_today or [],
            "difficulties_today": difficulties_today or [],
            "saved_summary_id": summary_saved["resource_id"],
            "telegram_summary_he": telegram_text,
        }

    def run_weekly_cycle(
        self,
        *,
        user_id: str = "moshe",
        silent_wins: list[dict[str, Any]] | None = None,
        notes: str = "",
    ) -> dict[str, Any]:
        repo = CompassRepository()
        growth_svc = GrowthChallengesAndPlayService()
        mental_svc = MentalSkillsService()

        # 1. Weekly consistency & task metrics
        weekly_progress = repo.get_weekly_progress(user_id=user_id)

        # 2. Neglected core domains check (GROWTH-002)
        neglected_check = growth_svc.check_neglected_domains(user_id=user_id, neglect_threshold_days=7)

        # 3. Weekly Silent Wins check (MENTAL-003)
        silent_wins_check = mental_svc.weekly_silent_wins_check(
            user_id=user_id,
            silent_wins=silent_wins,
            notes=notes,
        )

        # 4. Active challenges overview
        challenges = growth_svc.list_challenges(user_id=user_id, status="active")

        telegram_text = (
            f"📅 *סיכום שבועי – Compass*\n"
            f"📈 שיעור השלמת משימות: {weekly_progress['metrics']['task_completion_rate_pct']}%\n"
            f"🌱 תחומי ליבה שהוזנחו: {neglected_check['neglected_core_count']}\n"
            f"🤫 ניצחונות שקטים שתועדו השבוע: {silent_wins_check['silent_wins_recorded_count']}\n"
            f"🎯 אתגרים פעילים: {challenges['count']}"
        )

        repo.log_ai_usage(
            {
                "user_id": user_id,
                "usage_type": "deterministic_bypass",
                "purpose": "cycles.weekly",
                "reason": "Deterministic weekly review cycle (0 LLM tokens)",
            }
        )
        return {
            "success": True,
            "cycle": "weekly",
            "user_id": user_id,
            "weekly_progress": weekly_progress,
            "neglected_domains_check": neglected_check,
            "silent_wins_check": silent_wins_check,
            "active_challenges": challenges,
            "telegram_summary_he": telegram_text,
        }

    def run_monthly_cycle(
        self,
        *,
        user_id: str = "moshe",
        minimum_events_required: int = 5,
        proposed_policy_changes: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        repo = CompassRepository()
        growth_svc = GrowthChallengesAndPlayService()
        mental_svc = MentalSkillsService()

        # 1. Longitudinal mental progress assessment (ASSESS-001, ASSESS-002)
        mental_assessment = mental_svc.generate_monthly_mental_assessment(
            user_id=user_id,
            minimum_events_required=minimum_events_required,
        )

        # 2. Growth domains & stagnation review
        domains = growth_svc.list_domains(user_id=user_id)
        challenges = growth_svc.list_challenges(user_id=user_id, status="all")
        stagnant_challenges = [c for c in challenges["challenges"] if c["consecutive_stalls"] >= 3]

        # 3. If monthly cycle proposes material policy or goal changes, require explicit user approval (CONTROL-001)
        approval_request = None
        if proposed_policy_changes:
            event = {
                "event_id": f"evt_monthly_pol_{uuid4().hex[:10]}",
                "event_type": "policy.change_requested",
                "event_version": "1.0",
                "source": "compass.monthly_cycle",
                "user_id": user_id,
                "occurred_at": datetime.now(timezone.utc).isoformat(),
                "idempotency_key": f"monthly_pol_{uuid4().hex[:10]}",
                "payload": {"is_material_change": True, "proposed_patch": proposed_policy_changes},
                "metadata": {"dry_run": False, "requested_actions": []},
            }
            eval_res = RulesEngineAdapter().evaluate_event(event, actor=user_id)
            rule_result = eval_res.get("result", {})
            if eval_res.get("connected") and rule_result:
                repo.save_rule_evaluation(event, rule_result)
            approval_request = repo.create_approval_request(
                {
                    "user_id": user_id,
                    "title": "אישור עדכון מדיניות ומטרות חודשי (CONTROL-001)",
                    "description": "המלצת סיכום חודשי לעדכון גבולות אוטונומיה או יעדים דורשת אישור משתמש מפורש.",
                    "requested_by": "compass.monthly_cycle",
                    "action_type": "monthly_policy.update",
                    "risk_level": "high",
                    "proposed_action": proposed_policy_changes,
                    "rule_result": rule_result,
                }
            )

        telegram_text = (
            f"🗓 *הערכת התקדמות רב-חודשית – Compass*\n"
            f"🧠 סטטוס מגמה מנטלית: `{mental_assessment['trend_status']}` (רמת ביטחון: `{mental_assessment['conclusion_confidence']}`)\n"
            f"📊 אירועים מנטליים שנבדקו: {mental_assessment['data_quantity']['total_events']} "
            f"(ניצחונות שקטים: {mental_assessment['data_quantity']['silent_wins_count']})\n"
            f"🔄 אתגרים הדורשים רענון/החלפה: {len(stagnant_challenges)}\n"
            f"ℹ️ {mental_assessment['non_diagnostic_disclaimer']}"
        )

        repo.log_ai_usage(
            {
                "user_id": user_id,
                "usage_type": "deterministic_bypass",
                "purpose": "cycles.monthly",
                "reason": "Deterministic monthly longitudinal assessment (0 LLM tokens)",
            }
        )
        return {
            "success": True,
            "cycle": "monthly",
            "user_id": user_id,
            "mental_assessment": mental_assessment,
            "growth_domains": domains,
            "stagnant_challenges": stagnant_challenges,
            "pending_approval_request": approval_request,
            "telegram_summary_he": telegram_text,
        }

    # --- Section 17 & Rules AI-001, AI-002: Voice & Text Quick-Capture ---

    def process_quick_capture(
        self,
        *,
        user_id: str = "moshe",
        text: str,
        channel: str = "voice",
        speech_seconds: int = 0,
        tts_seconds: int = 0,
        llm_available: bool = True,
    ) -> dict[str, Any]:
        """
        Rule Engine First quick capture for Voice (STT/TTS) and Telegram:
        - Logs STT/TTS usage separately from LLM usage (`AI-002`).
        - Attempts deterministic structured command parsing FIRST (`AI-001`, 0 LLM tokens).
        - Works seamlessly even when `llm_available=False` (Acceptance Criterion #16).
        - Only records an LLM fallback when input is unstructured free-text AND `llm_available=True`.
        """
        repo = CompassRepository()
        rules_adapter = RulesEngineAdapter()
        clean_text = text.strip()

        # 1. Separate STT / TTS cost logging (Rule AI-002)
        speech_logs = []
        if channel == "voice" and speech_seconds > 0:
            stt_cost = round((speech_seconds / 60.0) * 0.006, 5)
            speech_logs.append(
                repo.log_ai_usage(
                    {
                        "user_id": user_id,
                        "usage_type": "stt",
                        "provider": "speech_to_text",
                        "model": "whisper-stt",
                        "purpose": "voice.quick_capture.stt",
                        "reason": "Voice input transcription (counted separately from LLM per AI-002)",
                        "tokens_or_seconds": speech_seconds,
                        "estimated_cost_usd": stt_cost,
                    }
                )
            )
        if channel == "voice" and tts_seconds > 0:
            tts_cost = round((tts_seconds / 60.0) * 0.009, 5)
            speech_logs.append(
                repo.log_ai_usage(
                    {
                        "user_id": user_id,
                        "usage_type": "tts",
                        "provider": "text_to_speech",
                        "model": "hebrew-tts",
                        "purpose": "voice.quick_capture.tts",
                        "reason": "Short voice confirmation response (counted separately from LLM per AI-002)",
                        "tokens_or_seconds": tts_seconds,
                        "estimated_cost_usd": tts_cost,
                    }
                )
            )

        # 2. Deterministic Structured Command Classification
        parsed = self._parse_deterministic_command(clean_text)
        is_structured_command = parsed["is_structured"]

        # Evaluate AI-001 via rules_engine
        ai_evt = {
            "event_id": f"evt_ai_{uuid4().hex[:10]}",
            "event_type": "input.received",
            "event_version": "1.0",
            "source": f"compass.{channel}",
            "user_id": user_id,
            "occurred_at": datetime.now(timezone.utc).isoformat(),
            "idempotency_key": f"ai_in_{uuid4().hex[:10]}",
            "payload": {
                "is_structured_command": is_structured_command,
                "channel": channel,
                "intent": parsed["intent"],
            },
            "metadata": {"dry_run": False, "requested_actions": []},
        }
        eval_res = rules_adapter.evaluate_event(ai_evt, actor=user_id)
        rule_result = eval_res.get("result", {})
        if eval_res.get("connected") and rule_result:
            repo.save_rule_evaluation(ai_evt, rule_result)

        # 3. Execute deterministically without LLM whenever structured OR when LLM is offline
        if is_structured_command or not llm_available:
            repo.log_ai_usage(
                {
                    "user_id": user_id,
                    "usage_type": "deterministic_bypass",
                    "purpose": f"quick_capture.{parsed['intent']}",
                    "reason": "Handled deterministically by Rule Engine First parser (0 LLM tokens)",
                }
            )
            action_result = self._execute_parsed_intent(user_id=user_id, parsed=parsed, raw_text=clean_text)
            return {
                "success": True,
                "channel": channel,
                "handled_by": "deterministic_parser",
                "llm_used": False,
                "llm_available": llm_available,
                "intent": parsed["intent"],
                "action_result": action_result,
                "voice_short_reply_he": action_result["short_reply_he"],
                "speech_logs_recorded": len(speech_logs),
                "rule_evaluation": rule_result,
            }

        # 4. Unstructured free-text with LLM available: log explicit LLM usage reason
        repo.log_ai_usage(
            {
                "user_id": user_id,
                "usage_type": "llm",
                "provider": "openai_compatible",
                "model": "gpt-4o-mini",
                "purpose": "quick_capture.free_text_analysis",
                "reason": "Unstructured free-text reflection could not be matched by deterministic command grammar",
                "tokens_or_seconds": max(40, len(clean_text) * 2),
                "estimated_cost_usd": 0.0004,
            }
        )
        fallback_result = self._execute_parsed_intent(
            user_id=user_id,
            parsed={"is_structured": False, "intent": "mental_event_capture", "params": {"is_silent_win": False}},
            raw_text=clean_text,
        )
        return {
            "success": True,
            "channel": channel,
            "handled_by": "llm_fallback",
            "llm_used": True,
            "llm_available": llm_available,
            "intent": "mental_event_capture",
            "action_result": fallback_result,
            "voice_short_reply_he": fallback_result["short_reply_he"],
            "speech_logs_recorded": len(speech_logs),
            "rule_evaluation": rule_result,
        }

    def _parse_deterministic_command(self, text: str) -> dict[str, Any]:
        lowered = text.lower()

        # 1. Next action / מה הפעולה הבאה
        if any(p in lowered for p in ("הפעולה הבאה", "מה עכשיו", "next action", "מה לעשות עכשיו")):
            return {"is_structured": True, "intent": "get_next_action", "params": {}}

        # 2. Frog execution reporting
        if "צפרדע" in lowered or "frog" in lowered:
            if any(w in lowered for w in ("בוצע חלקית", "חלקית", "partially")):
                return {"is_structured": True, "intent": "report_frog", "params": {"outcome": "partial"}}
            if any(w in lowered for w in ("לא בוצע", "נדחה", "דחה", "deferred", "not done")):
                return {"is_structured": True, "intent": "report_frog", "params": {"outcome": "deferred"}}
            if any(w in lowered for w in ("בוצע", "הושלמה", "סיימתי", "אכלתי", "done")):
                return {"is_structured": True, "intent": "report_frog", "params": {"outcome": "completed"}}
            if any(w in lowered for w in ("הוסף צפרדע", "צפרדע חדשה", "add frog")):
                name = re.sub(r"^(הוסף צפרדע|צפרדע חדשה|add frog)\s*:?\s*", "", text, flags=re.IGNORECASE).strip()
                return {"is_structured": True, "intent": "create_frog", "params": {"name": name or text}}

        # 3. Silent Win capture
        if any(w in lowered for w in ("ניצחון שקט", "עבר בשקט", "בלי להתפרץ", "silent win", "עצרתי לפני")):
            return {"is_structured": True, "intent": "record_silent_win", "params": {"is_silent_win": True}}

        # 4. Pre-action preparation protocol
        if any(w in lowered for w in ("פרוטוקול הכנה", "הפחתת התנגדות", "נשימה לפני", "prep protocol")):
            return {"is_structured": True, "intent": "get_prep_protocol", "params": {}}

        # 5. Routine reporting
        if any(w in lowered for w in ("הרגל בוצע", "סיימתי הרגל", "routine done", "גרסה מינימלית")):
            use_min = "מינימלית" in lowered
            return {"is_structured": True, "intent": "report_routine", "params": {"outcome": "minimum_completed" if use_min else "completed", "used_minimum_version": use_min}}

        # 6. Mental event capture with explicit keywords
        if any(w in lowered for w in ("אירוע מנטלי:", "תיעוד אירוע:", "טריגר:")):
            return {"is_structured": True, "intent": "mental_event_capture", "params": {"is_silent_win": False}}

        return {"is_structured": False, "intent": "unstructured_note", "params": {}}

    def _execute_parsed_intent(self, *, user_id: str, parsed: dict[str, Any], raw_text: str) -> dict[str, Any]:
        intent = parsed["intent"]
        params = parsed.get("params", {})

        if intent == "get_next_action":
            bundle = RoutinesAndExecutionService().get_executor_next_action(user_id=user_id)
            nxt = bundle.get("next_action")
            title = nxt["title"] if nxt else "אין משימה ממתינה כרגע"
            return {
                "intent": intent,
                "next_action": nxt,
                "short_reply_he": f"הפעולה הבאה שלך: {title}.",
            }

        if intent == "create_frog":
            created = FrogsService().create_frog(
                {
                    "user_id": user_id,
                    "name": params.get("name") or raw_text,
                    "frog_type": "one_time",
                    "importance": 8,
                    "resistance_level": 7,
                }
            )
            return {
                "intent": intent,
                "frog": created["frog"],
                "short_reply_he": f"הצפרדע '{created['frog']['name']}' נוספה למאגר בהצלחה.",
            }

        if intent == "report_frog":
            frogs = FrogsService().list_frogs(user_id=user_id, status="active")["frogs"]
            if not frogs:
                return {"intent": intent, "short_reply_he": "לא נמצאה צפרדע פעילה לדיווח."}
            target_frog = frogs[0]
            rep = FrogsService().report_frog_execution(
                target_frog["frog_id"],
                user_id=user_id,
                outcome=params.get("outcome", "completed"),
                notes=raw_text,
            )
            return {
                "intent": intent,
                "report": rep,
                "short_reply_he": f"דווח ביצוע לצפרדע '{target_frog['name']}' ({params.get('outcome', 'completed')}).",
            }

        if intent in {"record_silent_win", "mental_event_capture"}:
            is_sw = bool(params.get("is_silent_win", intent == "record_silent_win"))
            rec = MentalSkillsService().record_mental_event(
                {
                    "user_id": user_id,
                    "short_description": raw_text,
                    "trigger_text": "voice_or_quick_capture",
                    "actual_response": raw_text,
                    "is_silent_win": is_sw,
                }
            )
            return {
                "intent": intent,
                "event": rec["event"],
                "short_reply_he": (
                    "ניצחון שקט תועד בהצלחה! כל הכבוד על העצירה והבחירה המודעת."
                    if is_sw
                    else "האירוע המנטלי תועד לקראת עיבוד והערכה תקופתית."
                ),
            }

        if intent == "get_prep_protocol":
            proto = RoutinesAndExecutionService().get_or_create_prep_protocol(user_id=user_id)
            return {
                "intent": intent,
                "protocol": proto,
                "short_reply_he": f"פרוטוקול הכנה: עצור, זהו תחושה בגוף, ונשום ברוגע {proto['breathing_seconds']} שניות לפני הצעד הראשון.",
            }

        if intent == "report_routine":
            routines = RoutinesAndExecutionService().list_routines(user_id=user_id, status="active")["routines"]
            if not routines:
                return {"intent": intent, "short_reply_he": "לא נמצא הרגל פעיל לדיווח."}
            r = routines[0]
            rep = RoutinesAndExecutionService().report_routine_execution(
                r["routine_id"],
                user_id=user_id,
                outcome=params.get("outcome", "completed"),
                used_minimum_version=bool(params.get("used_minimum_version", False)),
                notes=raw_text,
            )
            return {
                "intent": intent,
                "report": rep,
                "short_reply_he": f"דווח ביצוע להרגל '{r['name']}'.",
            }

        # Default deterministic note capture (when LLM is offline and command is unstructured)
        saved = CompassRepository().save_conversation_event(
            {
                "user_id": user_id,
                "event_type": "quick_capture_note",
                "content": raw_text,
                "importance": "medium",
                "structured_payload": {"raw_text": raw_text},
            }
        )
        return {
            "intent": "quick_capture_note",
            "resource_id": saved["resource_id"],
            "short_reply_he": "ההערה נשמרה ביומן המערכת ללא שימוש במודל שפה.",
        }
