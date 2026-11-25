from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.database import db, json_dump, json_load, resource_id, utc_now


MVP_SKILLS: list[dict[str, Any]] = [
    {
        "skill_id": "PAUSE",
        "display_name": "Pause",
        "description": "Create space between stimulus and response.",
        "default_min_difficulty": 1,
        "default_max_difficulty": 2,
    },
    {
        "skill_id": "FRUSTRATION_TOLERANCE",
        "display_name": "Frustration tolerance",
        "description": "Stay stable when something does not work, is delayed, or goes wrong.",
        "default_min_difficulty": 1,
        "default_max_difficulty": 2,
    },
    {
        "skill_id": "AROUSAL_REGULATION",
        "display_name": "Arousal regulation",
        "description": "Notice and reduce physical or emotional activation.",
        "default_min_difficulty": 1,
        "default_max_difficulty": 2,
    },
]


MVP_EXERCISES: list[dict[str, Any]] = [
    {
        "exercise_id": "pause_wait_three_seconds",
        "skill_id": "PAUSE",
        "mode": "TRAINING_MODE",
        "challenge_type": "waiting",
        "min_difficulty": 1,
        "max_difficulty": 2,
        "micro_skill": "wait_three_seconds",
        "templates": {
            "baseline": "A message arrives that feels slightly unfair. What is your first impulse?",
            "retest": "A similar message arrives. Try a three-second pause before choosing your response.",
        },
        "safety_tags": ["low_intensity", "stop_available"],
    },
    {
        "exercise_id": "frustration_changed_instruction",
        "skill_id": "FRUSTRATION_TOLERANCE",
        "mode": "TRAINING_MODE",
        "challenge_type": "changed_instructions",
        "min_difficulty": 1,
        "max_difficulty": 2,
        "micro_skill": "reset_and_continue",
        "templates": {
            "baseline": "A small task changes after you already started. What happens first?",
            "retest": "The instruction changes again. Try one reset breath, then choose the next step.",
        },
        "safety_tags": ["low_intensity", "stop_available"],
    },
    {
        "exercise_id": "arousal_notice_exhale",
        "skill_id": "AROUSAL_REGULATION",
        "mode": "TRAINING_MODE",
        "challenge_type": "body_signal",
        "min_difficulty": 1,
        "max_difficulty": 2,
        "micro_skill": "slow_exhale_notice_change",
        "templates": {
            "baseline": "Pause and notice: what is happening in your body right now?",
            "retest": "After one slow exhale, what changed, even a little?",
        },
        "safety_tags": ["low_intensity", "stop_available"],
    },
]


class MentalSkillsService:
    def ensure_seed_data(self, user_id: str = "moshe") -> None:
        now = utc_now()
        with db() as conn:
            conn.execute(
                """
                insert or ignore into msp_users
                (user_id, display_name, timezone, coach_style, identity_method, created_at, updated_at)
                values (?, ?, ?, ?, ?, ?, ?)
                """,
                (user_id, user_id, "Asia/Jerusalem", "curious_playful", "single_user_mvp", now, now),
            )
            for skill in MVP_SKILLS:
                conn.execute(
                    """
                    insert or ignore into msp_skills
                    (skill_id, display_name, description, status, default_min_difficulty,
                     default_max_difficulty, created_at)
                    values (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        skill["skill_id"],
                        skill["display_name"],
                        skill["description"],
                        "active",
                        skill["default_min_difficulty"],
                        skill["default_max_difficulty"],
                        now,
                    ),
                )
                conn.execute(
                    """
                    insert or ignore into msp_user_skill_state
                    (user_id, skill_id, current_training_level, confidence, sessions_count,
                     recent_performance_json, trend, last_trained_at, preferred_exercises_json,
                     ineffective_exercises_json, known_triggers_json, effective_regulation_methods_json)
                    values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (user_id, skill["skill_id"], 1, 0.0, 0, "[]", "not_enough_data", None, "[]", "[]", "[]", "[]"),
                )
            for exercise in MVP_EXERCISES:
                conn.execute(
                    """
                    insert or ignore into msp_exercises
                    (exercise_id, skill_id, mode, challenge_type, min_difficulty, max_difficulty,
                     micro_skill, templates_json, safety_tags_json, status)
                    values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        exercise["exercise_id"],
                        exercise["skill_id"],
                        exercise["mode"],
                        exercise["challenge_type"],
                        exercise["min_difficulty"],
                        exercise["max_difficulty"],
                        exercise["micro_skill"],
                        json_dump(exercise["templates"]),
                        json_dump(exercise["safety_tags"]),
                        "active",
                    ),
                )

    def list_skills(self, user_id: str = "moshe") -> dict[str, Any]:
        self.ensure_seed_data(user_id)
        with db() as conn:
            rows = conn.execute("select * from msp_skills where status = 'active' order by skill_id").fetchall()
        return {"success": True, "skills": [self._skill_row(row) for row in rows]}

    def user_context(self, user_id: str) -> dict[str, Any]:
        self.ensure_seed_data(user_id)
        recommendation = self.recommendation(user_id)
        history = self.skill_history(user_id, recommendation["recommended_skill_id"], limit=3)
        return {
            "success": True,
            "user_id": user_id,
            "current_focus": recommendation["recommended_skill_id"],
            "recommended_skill_id": recommendation["recommended_skill_id"],
            "recommended_exercise_id": recommendation["recommended_exercise_id"],
            "difficulty": recommendation["difficulty"],
            "recent_summary": self._recent_summary(user_id),
            "skill_history": history["history"],
            "safety_notes": ["MVP uses only low-intensity drills.", "Stop immediately if the user asks to stop."],
        }

    def profile(self, user_id: str) -> dict[str, Any]:
        self.ensure_seed_data(user_id)
        with db() as conn:
            row = conn.execute("select * from msp_users where user_id = ?", (user_id,)).fetchone()
        return {
            "success": True,
            "user_id": row["user_id"],
            "display_name": row["display_name"],
            "timezone": row["timezone"],
            "coach_style": row["coach_style"],
            "identity_method": row["identity_method"],
        }

    def recommendation(self, user_id: str) -> dict[str, Any]:
        self.ensure_seed_data(user_id)
        with db() as conn:
            rows = conn.execute(
                """
                select * from msp_user_skill_state
                where user_id = ?
                order by sessions_count asc,
                         last_trained_at is not null asc,
                         last_trained_at asc,
                         case skill_id
                             when 'PAUSE' then 1
                             when 'FRUSTRATION_TOLERANCE' then 2
                             when 'AROUSAL_REGULATION' then 3
                             else 99
                         end asc
                """,
                (user_id,),
            ).fetchall()
            stopped = conn.execute(
                """
                select skill_id from msp_training_sessions
                where user_id = ? and safety_state in ('stopped', 'overload')
                order by started_at desc
                limit 1
                """,
                (user_id,),
            ).fetchone()
        chosen = next((row for row in rows if not stopped or row["skill_id"] != stopped["skill_id"]), rows[0])
        difficulty = min(2, max(1, int(chosen["current_training_level"])))
        exercise = self._exercise_for(chosen["skill_id"], difficulty)
        reason = "Fewest completed sessions; capped at low-intensity MVP difficulty."
        return {
            "success": True,
            "user_id": user_id,
            "recommended_skill_id": chosen["skill_id"],
            "recommended_exercise_id": exercise["exercise_id"] if exercise else None,
            "difficulty": difficulty,
            "reason": reason,
        }

    def start_session(self, payload: dict[str, Any]) -> dict[str, Any]:
        self.ensure_seed_data(payload["user_id"])
        existing = self._session_by_idempotency(payload["idempotency_key"])
        if existing:
            return existing
        exercise_id = payload.get("exercise_id") or self._exercise_for(payload["skill_id"], payload["difficulty"])["exercise_id"]
        session_id = resource_id("msp_session")
        now = utc_now()
        with db() as conn:
            conn.execute(
                """
                insert into msp_training_sessions
                (session_id, user_id, skill_id, exercise_id, mode, difficulty, status,
                 started_at, completed_at, summary, safety_state, idempotency_key)
                values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    session_id,
                    payload["user_id"],
                    payload["skill_id"],
                    exercise_id,
                    payload.get("mode", "TRAINING_MODE"),
                    payload.get("difficulty", 1),
                    "active",
                    now,
                    None,
                    "",
                    "ok",
                    payload["idempotency_key"],
                ),
            )
        return self._session(session_id) | {"already_existed": False}

    def record_event(self, session_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        existing = self._event_by_idempotency(payload["idempotency_key"])
        if existing:
            return existing
        session = self._session(session_id)
        if not session:
            return {"success": False, "error": "session_not_found"}
        safety_state = "stopped" if payload["event_type"] == "user_stop" else session["safety_state"]
        event_id = resource_id("msp_event")
        with db() as conn:
            conn.execute(
                """
                insert into msp_training_events
                (event_id, session_id, user_id, event_type, occurred_at, payload_json, idempotency_key)
                values (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event_id,
                    session_id,
                    session["user_id"],
                    payload["event_type"],
                    payload["occurred_at"],
                    json_dump(payload.get("payload", {})),
                    payload["idempotency_key"],
                ),
            )
            if safety_state != session["safety_state"]:
                conn.execute(
                    "update msp_training_sessions set safety_state = ?, status = ? where session_id = ?",
                    (safety_state, "stopped", session_id),
                )
        return {"success": True, "event_id": event_id, "session_id": session_id, "safety_state": safety_state, "already_existed": False}

    def complete_session(self, session_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        existing = self._idempotent_response(payload["idempotency_key"], "msp.complete_session")
        if existing:
            return existing
        session = self._session(session_id)
        if not session:
            return {"success": False, "error": "session_not_found"}
        now = utc_now()
        safety_state = payload.get("safety_state") or session["safety_state"]
        status = "completed" if safety_state == "ok" else "completed_with_safety_note"
        with db() as conn:
            conn.execute(
                """
                update msp_training_sessions
                set status = ?, completed_at = ?, summary = ?, safety_state = ?
                where session_id = ?
                """,
                (status, now, payload["summary"], safety_state, session_id),
            )
        self._update_skill_state(session["user_id"], session["skill_id"], session["difficulty"], safety_state, payload["user_noticed_change"], now)
        response = self._session(session_id) | {"success": True}
        self._remember_idempotent_response(payload["idempotency_key"], "msp.complete_session", response)
        return response

    def skill_history(self, user_id: str, skill_id: str, limit: int = 10) -> dict[str, Any]:
        self.ensure_seed_data(user_id)
        with db() as conn:
            state = conn.execute(
                "select * from msp_user_skill_state where user_id = ? and skill_id = ?",
                (user_id, skill_id),
            ).fetchone()
            sessions = conn.execute(
                """
                select * from msp_training_sessions
                where user_id = ? and skill_id = ?
                order by started_at desc
                limit ?
                """,
                (user_id, skill_id, limit),
            ).fetchall()
        return {
            "success": True,
            "user_id": user_id,
            "skill_id": skill_id,
            "state": self._state_row(state) if state else None,
            "history": [self._session_row(row) for row in sessions],
        }

    def progress(self, user_id: str) -> dict[str, Any]:
        self.ensure_seed_data(user_id)
        with db() as conn:
            rows = conn.execute("select * from msp_user_skill_state where user_id = ? order by skill_id", (user_id,)).fetchall()
        return {"success": True, "user_id": user_id, "skills": [self._state_row(row) for row in rows]}

    def patterns(self, user_id: str) -> dict[str, Any]:
        progress = self.progress(user_id)
        patterns = []
        for state in progress["skills"]:
            if state["sessions_count"]:
                patterns.append(
                    {
                        "skill_id": state["skill_id"],
                        "pattern": f"{state['sessions_count']} completed session(s); trend is {state['trend']}.",
                        "evidence_level": "early",
                    }
                )
        return {"success": True, "user_id": user_id, "patterns": patterns}

    def save_observation(self, payload: dict[str, Any]) -> dict[str, Any]:
        existing = self._idempotent_response(payload["idempotency_key"], "msp.save_observation")
        if existing:
            return existing
        observation_id = resource_id("msp_observation")
        occurred_at = payload.get("occurred_at") or datetime.now(timezone.utc).isoformat()
        with db() as conn:
            conn.execute(
                """
                insert into msp_observations
                (observation_id, user_id, skill_id, occurred_at, source, content, tags_json, idempotency_key)
                values (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    observation_id,
                    payload["user_id"],
                    payload.get("skill_id"),
                    occurred_at,
                    payload.get("source", "gpt"),
                    payload["content"],
                    json_dump(payload.get("tags", [])),
                    payload["idempotency_key"],
                ),
            )
        response = {"success": True, "observation_id": observation_id, "already_existed": False}
        self._remember_idempotent_response(payload["idempotency_key"], "msp.save_observation", response)
        return response

    def save_reflection(self, payload: dict[str, Any]) -> dict[str, Any]:
        existing = self._idempotent_response(payload["idempotency_key"], "msp.save_reflection")
        if existing:
            return existing
        reflection_id = resource_id("msp_reflection")
        with db() as conn:
            conn.execute(
                """
                insert into msp_reflections
                (reflection_id, user_id, session_id, skill_id, created_at, content, insight_tags_json, idempotency_key)
                values (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    reflection_id,
                    payload["user_id"],
                    payload.get("session_id"),
                    payload.get("skill_id"),
                    utc_now(),
                    payload["content"],
                    json_dump(payload.get("insight_tags", [])),
                    payload["idempotency_key"],
                ),
            )
        response = {"success": True, "reflection_id": reflection_id, "already_existed": False}
        self._remember_idempotent_response(payload["idempotency_key"], "msp.save_reflection", response)
        return response

    def _update_skill_state(self, user_id: str, skill_id: str, difficulty: int, safety_state: str, noticed_change: bool, now: str) -> None:
        with db() as conn:
            row = conn.execute(
                "select * from msp_user_skill_state where user_id = ? and skill_id = ?",
                (user_id, skill_id),
            ).fetchone()
            recent = json_load(row["recent_performance_json"], []) if row else []
            recent = ([{"safety_state": safety_state, "user_noticed_change": noticed_change, "difficulty": difficulty}] + recent)[:5]
            if safety_state in {"stopped", "overload"}:
                level = 1
                trend = "reduce_difficulty"
            elif noticed_change and row and row["sessions_count"] >= 2:
                level = min(2, difficulty + 1)
                trend = "early_positive_signal"
            else:
                level = min(2, difficulty)
                trend = "collecting_evidence"
            confidence = min(1.0, 0.2 + 0.1 * (int(row["sessions_count"]) + 1 if row else 1))
            conn.execute(
                """
                update msp_user_skill_state
                set current_training_level = ?, confidence = ?, sessions_count = sessions_count + 1,
                    recent_performance_json = ?, trend = ?, last_trained_at = ?
                where user_id = ? and skill_id = ?
                """,
                (level, confidence, json_dump(recent), trend, now, user_id, skill_id),
            )

    def _exercise_for(self, skill_id: str, difficulty: int) -> dict[str, Any] | None:
        with db() as conn:
            row = conn.execute(
                """
                select * from msp_exercises
                where skill_id = ? and min_difficulty <= ? and max_difficulty >= ? and status = 'active'
                order by exercise_id
                limit 1
                """,
                (skill_id, difficulty, difficulty),
            ).fetchone()
        return self._exercise_row(row) if row else None

    def _recent_summary(self, user_id: str) -> str:
        with db() as conn:
            row = conn.execute(
                """
                select summary from msp_training_sessions
                where user_id = ? and summary != ''
                order by completed_at desc
                limit 1
                """,
                (user_id,),
            ).fetchone()
        return row["summary"] if row else ""

    def _session(self, session_id: str) -> dict[str, Any] | None:
        with db() as conn:
            row = conn.execute("select * from msp_training_sessions where session_id = ?", (session_id,)).fetchone()
        return self._session_row(row) if row else None

    def _session_by_idempotency(self, key: str) -> dict[str, Any] | None:
        with db() as conn:
            row = conn.execute("select * from msp_training_sessions where idempotency_key = ?", (key,)).fetchone()
        return (self._session_row(row) | {"already_existed": True}) if row else None

    def _event_by_idempotency(self, key: str) -> dict[str, Any] | None:
        with db() as conn:
            row = conn.execute("select * from msp_training_events where idempotency_key = ?", (key,)).fetchone()
        if not row:
            return None
        return {
            "success": True,
            "event_id": row["event_id"],
            "session_id": row["session_id"],
            "safety_state": "stopped" if row["event_type"] == "user_stop" else "ok",
            "already_existed": True,
        }

    def _idempotent_response(self, key: str, endpoint: str) -> dict[str, Any] | None:
        with db() as conn:
            row = conn.execute(
                "select response_json from idempotency_keys where key = ? and endpoint = ?",
                (key, endpoint),
            ).fetchone()
        return json_load(row["response_json"], None) if row else None

    def _remember_idempotent_response(self, key: str, endpoint: str, response: dict[str, Any]) -> None:
        with db() as conn:
            conn.execute(
                """
                insert or ignore into idempotency_keys (key, endpoint, response_json, created_at)
                values (?, ?, ?, ?)
                """,
                (key, endpoint, json_dump(response), utc_now()),
            )

    def _skill_row(self, row: Any) -> dict[str, Any]:
        return {
            "skill_id": row["skill_id"],
            "display_name": row["display_name"],
            "description": row["description"],
            "status": row["status"],
            "default_min_difficulty": row["default_min_difficulty"],
            "default_max_difficulty": row["default_max_difficulty"],
        }

    def _exercise_row(self, row: Any) -> dict[str, Any]:
        return {
            "exercise_id": row["exercise_id"],
            "skill_id": row["skill_id"],
            "mode": row["mode"],
            "challenge_type": row["challenge_type"],
            "min_difficulty": row["min_difficulty"],
            "max_difficulty": row["max_difficulty"],
            "micro_skill": row["micro_skill"],
            "templates": json_load(row["templates_json"], {}),
            "safety_tags": json_load(row["safety_tags_json"], []),
            "status": row["status"],
        }

    def _state_row(self, row: Any) -> dict[str, Any]:
        return {
            "user_id": row["user_id"],
            "skill_id": row["skill_id"],
            "current_training_level": row["current_training_level"],
            "confidence": row["confidence"],
            "sessions_count": row["sessions_count"],
            "recent_performance": json_load(row["recent_performance_json"], []),
            "trend": row["trend"],
            "last_trained_at": row["last_trained_at"],
            "preferred_exercises": json_load(row["preferred_exercises_json"], []),
            "ineffective_exercises": json_load(row["ineffective_exercises_json"], []),
            "known_triggers": json_load(row["known_triggers_json"], []),
            "effective_regulation_methods": json_load(row["effective_regulation_methods_json"], []),
        }

    def _session_row(self, row: Any) -> dict[str, Any]:
        return {
            "success": True,
            "session_id": row["session_id"],
            "user_id": row["user_id"],
            "skill_id": row["skill_id"],
            "exercise_id": row["exercise_id"],
            "mode": row["mode"],
            "difficulty": row["difficulty"],
            "status": row["status"],
            "started_at": row["started_at"],
            "completed_at": row["completed_at"],
            "summary": row["summary"],
            "safety_state": row["safety_state"],
        }

    # --- Phase 5: Proactive Mental Training (4 Modes), Real-Life Events, Silent Wins & Monthly Assessment ---

    ALLOWED_MENTAL_CONSUMERS = {"compass", "personal_Assessment", "self_manage_recommendation_only"}
    FORBIDDEN_OPERATIONAL_SERVICES = {"task_commander", "mail_manager", "economic_manager", "administrative"}

    def get_proactive_training_catalog(self) -> dict[str, Any]:
        """Section 11: Four proactive mental training modes."""
        return {
            "success": True,
            "training_modes": [
                {
                    "mode_id": "baseline_calm",
                    "title": "א. אימון בסיס (בזמנים רגועים)",
                    "practices": [
                        {"id": "body_sensation_scan", "title": "מודעות לתחושות הגוף וזיהוי כיווצים"},
                        {"id": "thought_pattern_noticing", "title": "זיהוי דפוסי מחשבה אוטומטיים"},
                        {"id": "curiosity_shift_drill", "title": "אימון מעבר מהתגוננות לסקרנות"},
                        {"id": "cognitive_flexibility_3_views", "title": "גמישות מחשבתית – 3 פרשנויות חלופיות"},
                    ],
                },
                {
                    "mode_id": "pre_event_prep",
                    "title": "ב. הכנה לפני אירוע",
                    "practices": [
                        {"id": "pre_event_trigger_intent", "title": "זיהוי טריגר אפשרי, בחירת כוונה ותזכורת לדפוס התגובה הרצוי"},
                    ],
                },
                {
                    "mode_id": "realtime_intervention",
                    "title": "ג. התערבות בזמן אמת",
                    "practices": [
                        {"id": "realtime_pause_choice_space", "title": "זיהוי תגובה אוטומטית -> עצירה -> מרווח לבחירה -> מעבר לסקרנות"},
                    ],
                },
                {
                    "mode_id": "post_event_processing",
                    "title": "ד. עיבוד לאחר אירוע",
                    "practices": [
                        {"id": "post_event_quick_debrief", "title": "תיעוד קצר, זיהוי דפוס, הפקת לקח והתאמת תרגול"},
                    ],
                },
            ],
        }

    def record_mental_event(self, payload: dict[str, Any]) -> dict[str, Any]:
        """
        Section 12 & Rule MENTAL-002:
        Fast capture of real-life mental events and Silent Wins.
        Supports partial reporting: missing 0-10 scores remain None (NULL) and are NEVER treated as 0.
        """
        from uuid import uuid4
        from app.repository import CompassRepository
        from app.services.rules_engine import RulesEngineAdapter

        repo = CompassRepository()
        idem_key = payload.get("idempotency_key")
        if idem_key and (cached := self._idempotent_response(idem_key, "msp.record_mental_event")):
            return {**cached, "already_existed": True}

        user_id = str(payload.get("user_id") or "moshe")
        event_id = str(payload.get("event_id") or resource_id("mental_evt"))
        now = utc_now()
        occurred_at = str(payload.get("occurred_at") or now)
        is_silent_win = bool(payload.get("is_silent_win", False))
        event_type = str(payload.get("event_type") or ("silent_win" if is_silent_win else "interpersonal_friction"))
        training_stage = str(payload.get("training_stage") or "post_event_processing")

        # Keep missing values strictly as None (NULL in SQLite/Postgres), never defaulting to 0!
        init_intensity = payload.get("initial_emotion_intensity")
        def_urge = payload.get("defensive_or_attack_urge")
        curiosity = payload.get("curiosity_ability")
        choice = payload.get("choice_ability")
        recovery_min = payload.get("recovery_duration_minutes")

        # Deterministic pattern & tailored exercise recommendation
        if is_silent_win:
            identified_pattern = "silent_win_proactive_regulation"
            recommended_practice_id = "curiosity_shift_drill"
        elif def_urge is not None and int(def_urge) >= 7:
            identified_pattern = "high_defensive_reactivity"
            recommended_practice_id = "curiosity_shift_drill"
        elif init_intensity is not None and int(init_intensity) >= 7:
            identified_pattern = "high_initial_arousal"
            recommended_practice_id = "arousal_notice_exhale"
        else:
            identified_pattern = str(payload.get("identified_pattern") or "moderate_trigger_response")
            recommended_practice_id = "pause_wait_three_seconds"

        lesson = str(
            payload.get("lesson_learned")
            or (
                "אירוע שעבר בשקט יחסי לעומת העבר – עדות להפחתת עוצמת התגובה הראשונית."
                if is_silent_win
                else "זיהוי המרווח שבין הטריגר לתגובה מאפשר מעבר מהתגוננות לסקרנות."
            )
        )

        with db() as conn:
            conn.execute(
                """
                insert into msp_mental_events
                (event_id, user_id, occurred_at, event_type, training_stage,
                 short_description, trigger_text, initial_emotion_intensity,
                 defensive_or_attack_urge, curiosity_ability, choice_ability,
                 actual_response, recovery_duration_minutes, notes,
                 reporting_confidence, is_silent_win, identified_pattern,
                 lesson_learned, recommended_practice_id, idempotency_key, created_at)
                values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event_id,
                    user_id,
                    occurred_at,
                    event_type,
                    training_stage,
                    str(payload.get("short_description") or ""),
                    str(payload.get("trigger_text") or "unspecified_trigger"),
                    int(init_intensity) if init_intensity is not None else None,
                    int(def_urge) if def_urge is not None else None,
                    int(curiosity) if curiosity is not None else None,
                    int(choice) if choice is not None else None,
                    str(payload.get("actual_response") or ""),
                    int(recovery_min) if recovery_min is not None else None,
                    payload.get("notes"),
                    str(payload.get("reporting_confidence") or "high"),
                    1 if is_silent_win else 0,
                    identified_pattern,
                    lesson,
                    recommended_practice_id,
                    idem_key,
                    now,
                ),
            )

        rule_evt = {
            "event_id": f"evt_m2_{uuid4().hex[:10]}",
            "event_type": "mental_event.occurred",
            "event_version": "1.0",
            "source": "compass.mental_skills",
            "user_id": user_id,
            "occurred_at": datetime.now(timezone.utc).isoformat(),
            "idempotency_key": f"m2_{event_id}",
            "payload": {"event_id": event_id, "event_type": event_type, "is_silent_win": is_silent_win},
            "metadata": {"dry_run": False, "requested_actions": []},
        }
        eval_res = RulesEngineAdapter().evaluate_event(rule_evt, actor=user_id)
        if eval_res.get("connected") and eval_res.get("result"):
            repo.save_rule_evaluation(rule_evt, eval_res["result"])

        from app.services.growth_service import GrowthChallengesAndPlayService

        GrowthChallengesAndPlayService().record_domain_activity(user_id=user_id, slug="mental", occurred_at=now)

        saved = self.get_mental_event(event_id)
        res = {
            "success": True,
            "event": saved,
            "recommended_practice_id": recommended_practice_id,
            "already_existed": False,
        }
        if idem_key:
            self._remember_idempotent_response(idem_key, "msp.record_mental_event", res)
        return res

    def get_mental_event(self, event_id: str) -> dict[str, Any] | None:
        with db() as conn:
            row = conn.execute("select * from msp_mental_events where event_id = ?", (event_id,)).fetchone()
        return self._mental_event_row(row) if row else None

    def list_mental_events(self, user_id: str = "moshe", limit: int = 50) -> list[dict[str, Any]]:
        with db() as conn:
            rows = conn.execute(
                "select * from msp_mental_events where user_id = ? order by occurred_at desc, created_at desc limit ?",
                (user_id, limit),
            ).fetchall()
        return [self._mental_event_row(r) for r in rows]

    def weekly_silent_wins_check(self, user_id: str = "moshe", silent_wins: list[dict[str, Any]] | None = None, notes: str = "") -> dict[str, Any]:
        """
        Section 12 & Rule MENTAL-003:
        Weekly check for situations that previously triggered strong reactions but passed calmly this week.
        """
        from uuid import uuid4
        from app.repository import CompassRepository
        from app.services.rules_engine import RulesEngineAdapter

        repo = CompassRepository()
        now = utc_now()
        recorded_events = []
        for sw in silent_wins or []:
            sw_payload = {**sw, "user_id": user_id, "is_silent_win": True}
            recorded_events.append(self.record_mental_event(sw_payload)["event"])

        check_id = resource_id("sw_chk")
        with db() as conn:
            conn.execute(
                """
                insert into msp_silent_win_checks
                (check_id, user_id, checked_at, silent_wins_recorded, notes)
                values (?, ?, ?, ?, ?)
                """,
                (check_id, user_id, now, len(recorded_events), notes),
            )

        rule_evt = {
            "event_id": f"evt_m3_{uuid4().hex[:10]}",
            "event_type": "weekly_review.silent_wins_check",
            "event_version": "1.0",
            "source": "compass.mental_skills",
            "user_id": user_id,
            "occurred_at": datetime.now(timezone.utc).isoformat(),
            "idempotency_key": f"m3_{check_id}",
            "payload": {"days_since_silent_wins_check": 7, "silent_wins_recorded": len(recorded_events)},
            "metadata": {"dry_run": False, "requested_actions": []},
        }
        eval_res = RulesEngineAdapter().evaluate_event(rule_evt, actor=user_id)
        rule_result = eval_res.get("result", {})
        if eval_res.get("connected") and rule_result:
            repo.save_rule_evaluation(rule_evt, rule_result)

        return {
            "success": True,
            "check_id": check_id,
            "silent_wins_recorded_count": len(recorded_events),
            "recorded_silent_wins": recorded_events,
            "prompt_he": "אילו מצבים השבוע היו מעוררים בעבר תגובה אוטומטית חזקה, אך הפעם עברו בשקט או מתוך בחירה?",
            "rule_evaluation": rule_result,
        }

    def generate_monthly_mental_assessment(self, user_id: str = "moshe", minimum_events_required: int = 5) -> dict[str, Any]:
        """
        Section 12, Rules ASSESS-001, ASSESS-002 & Acceptance Criteria #10, #11:
        Evaluates longitudinal mental progress:
        - Never treats missing (None) fields as 0.
        - Blocks trend inference when event_count < minimum_events_required (ASSESS-002, Acceptance Criterion #10).
        - Reports data quantity, data quality, comparison limitations, confidence level, and comparable event trends (Acceptance Criterion #11).
        - Includes explicit non-diagnostic disclaimer.
        """
        from uuid import uuid4
        from app.repository import CompassRepository
        from app.services.rules_engine import RulesEngineAdapter

        repo = CompassRepository()
        events = list(reversed(self.list_mental_events(user_id=user_id, limit=200)))
        total_count = len(events)
        silent_wins_count = sum(1 for e in events if e["is_silent_win"])

        # Evaluate ASSESS-002
        rule_evt = {
            "event_id": f"evt_assess_{uuid4().hex[:10]}",
            "event_type": "assessment.trend_requested",
            "event_version": "1.0",
            "source": "compass.mental_assessment",
            "user_id": user_id,
            "occurred_at": datetime.now(timezone.utc).isoformat(),
            "idempotency_key": f"assess_trend_{uuid4().hex[:10]}",
            "payload": {"event_count": total_count, "minimum_required": minimum_events_required},
            "metadata": {"dry_run": False, "requested_actions": []},
        }
        eval_res = RulesEngineAdapter().evaluate_event(rule_evt, actor=user_id)
        rule_result = eval_res.get("result", {})
        if eval_res.get("connected") and rule_result:
            repo.save_rule_evaluation(rule_evt, rule_result)

        metric_fields = [
            "initial_emotion_intensity",
            "defensive_or_attack_urge",
            "curiosity_ability",
            "choice_ability",
            "recovery_duration_minutes",
        ]

        def _non_null_values(items: list[dict[str, Any]], key: str) -> list[int]:
            return [int(item[key]) for item in items if item.get(key) is not None]

        def _avg(vals: list[int]) -> float | None:
            return round(sum(vals) / len(vals), 2) if vals else None

        populated_cells = sum(
            1 for e in events for k in metric_fields if e.get(k) is not None
        )
        total_possible_cells = max(1, total_count * len(metric_fields))
        completeness_pct = round((populated_cells / total_possible_cells) * 100.0, 1) if total_count else 0.0
        high_conf_count = sum(1 for e in events if e.get("reporting_confidence") == "high")

        data_quantity = {
            "total_events": total_count,
            "minimum_events_required": minimum_events_required,
            "silent_wins_count": silent_wins_count,
            "field_sample_sizes": {k: len(_non_null_values(events, k)) for k in metric_fields},
        }
        data_quality = {
            "completeness_pct": completeness_pct,
            "high_confidence_reports_count": high_conf_count,
            "missing_values_policy": "שדות חסרים נשמרים כ-NULL ואינם נספרים כ-0 בחישוב הממוצעים.",
        }
        comparison_limitations = [
            "הנתונים מבוססים על דיווח עצמי ועשויים להיות מושפעים מעצימות הטריגר והקשר היום.",
            "השוואת מגמה תקפה רק בין אירועים מאותו סוג/טריגר ולאורך מספר שבועות/חודשים.",
            "שדות שלא דווחו באירועים חלקיים הוחרגו מהמכנה ולא חושבו כאפס.",
        ]
        disclaimer = "המערכת אינה כלי אבחון פסיכולוגי או רפואי; המדדים מיועדים לאימון ומודעות עצמית בלבד."

        if total_count < minimum_events_required or rule_result.get("final_decision") == "block":
            return {
                "success": True,
                "user_id": user_id,
                "sufficient_data": False,
                "trend_status": "insufficient_data",
                "conclusion_confidence": "insufficient",
                "trend": None,
                "message_he": (
                    f"קיימים כעת {total_count} אירועים מתועדים בלבד (נדרשים לפחות {minimum_events_required}). "
                    "אין להסיק מגמת שיפור או נסיגה על סמך כמות נתונים קטנה (ASSESS-002)."
                ),
                "data_quantity": data_quantity,
                "data_quality": data_quality,
                "comparison_limitations": comparison_limitations,
                "non_diagnostic_disclaimer": disclaimer,
                "rule_evaluation": rule_result,
            }

        # Split events into earlier half vs. recent half to evaluate multi-month / longitudinal direction
        mid = total_count // 2
        early_half = events[:mid]
        recent_half = events[mid:]

        early_init = _avg(_non_null_values(early_half, "initial_emotion_intensity"))
        recent_init = _avg(_non_null_values(recent_half, "initial_emotion_intensity"))
        early_rec = _avg(_non_null_values(early_half, "recovery_duration_minutes"))
        recent_rec = _avg(_non_null_values(recent_half, "recovery_duration_minutes"))
        early_cur = _avg(_non_null_values(early_half, "curiosity_ability"))
        recent_cur = _avg(_non_null_values(recent_half, "curiosity_ability"))
        early_choice = _avg(_non_null_values(early_half, "choice_ability"))
        recent_choice = _avg(_non_null_values(recent_half, "choice_ability"))

        # Automatic reaction frequency relative to documented exposure:
        # An event counts as automatic reaction when defensive_or_attack_urge >= 7 and choice_ability <= 4 (and not a silent win)
        auto_reactions = sum(
            1
            for e in events
            if not e["is_silent_win"]
            and (e.get("defensive_or_attack_urge") or 0) >= 7
            and (e.get("choice_ability") if e.get("choice_ability") is not None else 5) <= 4
        )
        auto_reaction_rate_pct = round((auto_reactions / total_count) * 100.0, 1)

        # Comparable event clusters by event_type
        clusters: dict[str, list[dict[str, Any]]] = {}
        for e in events:
            clusters.setdefault(e["event_type"], []).append(e)
        comparable_clusters = []
        for etype, items in clusters.items():
            if len(items) >= 2:
                comparable_clusters.append(
                    {
                        "event_type": etype,
                        "count": len(items),
                        "avg_initial_intensity": _avg(_non_null_values(items, "initial_emotion_intensity")),
                        "avg_recovery_minutes": _avg(_non_null_values(items, "recovery_duration_minutes")),
                        "avg_curiosity": _avg(_non_null_values(items, "curiosity_ability")),
                        "avg_choice": _avg(_non_null_values(items, "choice_ability")),
                    }
                )

        # Determine overall longitudinal trend direction
        improving_signals = 0
        if early_init is not None and recent_init is not None and recent_init < early_init:
            improving_signals += 1
        if early_rec is not None and recent_rec is not None and recent_rec < early_rec:
            improving_signals += 1
        if early_cur is not None and recent_cur is not None and recent_cur > early_cur:
            improving_signals += 1
        if early_choice is not None and recent_choice is not None and recent_choice > early_choice:
            improving_signals += 1

        trend_direction = "improving" if improving_signals >= 2 else "stable_or_mixed"
        confidence = "high" if (total_count >= 10 and completeness_pct >= 70.0) else "medium"

        return {
            "success": True,
            "user_id": user_id,
            "sufficient_data": True,
            "trend_status": "trend_identified",
            "conclusion_confidence": confidence,
            "trend": {
                "direction": trend_direction,
                "initial_emotion_intensity": {"early_avg": early_init, "recent_avg": recent_init},
                "recovery_duration_minutes": {"early_avg": early_rec, "recent_avg": recent_rec},
                "curiosity_ability": {"early_avg": early_cur, "recent_avg": recent_cur},
                "choice_ability": {"early_avg": early_choice, "recent_avg": recent_choice},
                "automatic_reaction_rate_pct": auto_reaction_rate_pct,
                "silent_wins_count": silent_wins_count,
            },
            "comparable_event_clusters": comparable_clusters,
            "data_quantity": data_quantity,
            "data_quality": data_quality,
            "comparison_limitations": comparison_limitations,
            "non_diagnostic_disclaimer": disclaimer,
            "rule_evaluation": rule_result,
        }

    def sanitize_payload_for_target_service(self, target_service: str, payload: dict[str, Any]) -> dict[str, Any]:
        """
        Section 19.21 (Acceptance Criterion #21):
        Ensures private mental event data is NEVER exposed to services that do not need it
        (`task_commander`, `mail_manager`, `economic_manager`, `administrative`).
        """
        sensitive_keys = {
            "mental_events",
            "msp_mental_events",
            "initial_emotion_intensity",
            "defensive_or_attack_urge",
            "curiosity_ability",
            "choice_ability",
            "trigger_text",
            "silent_wins",
            "emotional_notes",
        }
        if target_service in self.FORBIDDEN_OPERATIONAL_SERVICES or target_service not in self.ALLOWED_MENTAL_CONSUMERS:
            return {k: v for k, v in payload.items() if k not in sensitive_keys}
        return dict(payload)

    def _mental_event_row(self, row: Any) -> dict[str, Any]:
        return {
            "event_id": row["event_id"],
            "user_id": row["user_id"],
            "occurred_at": row["occurred_at"],
            "event_type": row["event_type"],
            "training_stage": row["training_stage"],
            "short_description": row["short_description"],
            "trigger_text": row["trigger_text"],
            "initial_emotion_intensity": int(row["initial_emotion_intensity"]) if row["initial_emotion_intensity"] is not None else None,
            "defensive_or_attack_urge": int(row["defensive_or_attack_urge"]) if row["defensive_or_attack_urge"] is not None else None,
            "curiosity_ability": int(row["curiosity_ability"]) if row["curiosity_ability"] is not None else None,
            "choice_ability": int(row["choice_ability"]) if row["choice_ability"] is not None else None,
            "actual_response": row["actual_response"],
            "recovery_duration_minutes": int(row["recovery_duration_minutes"]) if row["recovery_duration_minutes"] is not None else None,
            "notes": row["notes"],
            "reporting_confidence": row["reporting_confidence"],
            "is_silent_win": bool(row["is_silent_win"]),
            "identified_pattern": row["identified_pattern"],
            "lesson_learned": row["lesson_learned"],
            "recommended_practice_id": row["recommended_practice_id"],
            "created_at": row["created_at"],
        }
