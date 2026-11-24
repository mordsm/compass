from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator
from uuid import uuid4

from app.config import get_settings


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def connect() -> Any:
    settings = get_settings()
    if settings.database_url:
        return PostgresConnection(settings.database_url)
    path = Path(settings.database_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


@contextmanager
def db() -> Iterator[Any]:
    conn = connect()
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    with db() as conn:
        conn.executescript(
            """
            create table if not exists idempotency_keys (
                key text primary key,
                endpoint text not null,
                response_json text not null,
                created_at text not null
            );

            create table if not exists conversation_events (
                id text primary key,
                user_id text not null,
                conversation_id text,
                event_type text not null,
                content text not null,
                importance text not null,
                structured_payload_json text not null,
                created_at text not null
            );

            create table if not exists conversation_summaries (
                id text primary key,
                user_id text not null,
                conversation_id text,
                summary text not null,
                decisions_json text not null,
                tasks_json text not null,
                open_questions_json text not null,
                created_at text not null
            );

            create table if not exists tasks (
                id text primary key,
                user_id text not null,
                title text not null,
                description text,
                status text not null,
                due_date text,
                priority text,
                source text,
                metadata_json text not null,
                created_at text not null,
                updated_at text not null
            );

            create table if not exists daily_plans (
                id text primary key,
                user_id text not null,
                plan_date text not null,
                status text not null,
                energy_level integer,
                available_minutes integer,
                outcomes_json text not null,
                scheduled_tasks_json text not null,
                deferred_items_json text not null,
                risks_json text not null,
                raw_payload_json text not null,
                created_at text not null,
                updated_at text not null
            );

            create table if not exists approval_requests (
                id text primary key,
                user_id text not null,
                title text not null,
                description text,
                requested_by text not null,
                action_type text not null,
                status text not null,
                risk_level text not null,
                proposed_action_json text not null,
                rule_result_json text not null,
                created_at text not null,
                updated_at text not null,
                decided_at text,
                decision_by text,
                decision_notes text
            );

            create table if not exists audit_log (
                id text primary key,
                action text not null,
                user_id text,
                payload_json text not null,
                created_at text not null
            );

            create table if not exists rule_evaluations (
                id text primary key,
                event_id text not null,
                user_id text not null,
                event_type text not null,
                source text not null,
                final_decision text not null,
                risk_level text not null,
                dry_run integer not null,
                request_json text not null,
                result_json text not null,
                created_at text not null
            );

            create table if not exists financial_transactions (
                id text primary key,
                household_id text not null,
                person_id text,
                user_id text not null,
                account_id text,
                account_owner text,
                visibility_scope text not null,
                consent_status text not null,
                transaction_date text not null,
                kind text not null,
                amount_minor integer not null,
                currency text not null,
                category text,
                merchant text,
                description text not null,
                source text not null,
                confidence real not null,
                verification_status text not null,
                external_id text,
                status text not null,
                metadata_json text not null,
                created_at text not null,
                updated_at text not null
            );

            create unique index if not exists idx_financial_transactions_external
            on financial_transactions(source, external_id)
            where external_id is not null;

            create table if not exists financial_memories (
                id text primary key,
                household_id text not null,
                person_id text,
                memory_type text not null,
                subject text not null,
                value_json text not null,
                source text not null,
                confidence real not null,
                verification_status text not null,
                sensitivity text not null,
                is_current integer not null,
                replaces_memory_id text,
                valid_from text not null,
                valid_until text,
                created_at text not null,
                updated_at text not null
            );

            create table if not exists financial_settings (
                id text primary key,
                household_id text not null,
                setting_type text not null,
                setting_json text not null,
                enabled integer not null,
                created_at text not null,
                updated_at text not null,
                unique(household_id, setting_type)
            );

            create table if not exists financial_alerts (
                id text primary key,
                household_id text not null,
                transaction_id text,
                alert_type text not null,
                severity text not null,
                message text not null,
                status text not null,
                metadata_json text not null,
                created_at text not null,
                updated_at text not null
            );

            create table if not exists ecosystem_hub_state (
                id text primary key,
                revision integer not null,
                state_json text not null,
                updated_at text not null
            );

            create table if not exists msp_users (
                user_id text primary key,
                display_name text not null,
                timezone text not null,
                coach_style text not null,
                identity_method text not null,
                created_at text not null,
                updated_at text not null
            );

            create table if not exists msp_skills (
                skill_id text primary key,
                display_name text not null,
                description text not null,
                status text not null,
                default_min_difficulty integer not null,
                default_max_difficulty integer not null,
                created_at text not null
            );

            create table if not exists msp_exercises (
                exercise_id text primary key,
                skill_id text not null,
                mode text not null,
                challenge_type text not null,
                min_difficulty integer not null,
                max_difficulty integer not null,
                micro_skill text not null,
                templates_json text not null,
                safety_tags_json text not null,
                status text not null
            );

            create table if not exists msp_user_skill_state (
                user_id text not null,
                skill_id text not null,
                current_training_level integer not null,
                confidence real not null,
                sessions_count integer not null,
                recent_performance_json text not null,
                trend text not null,
                last_trained_at text,
                preferred_exercises_json text not null,
                ineffective_exercises_json text not null,
                known_triggers_json text not null,
                effective_regulation_methods_json text not null,
                primary key (user_id, skill_id)
            );

            create table if not exists msp_training_sessions (
                session_id text primary key,
                user_id text not null,
                skill_id text not null,
                exercise_id text,
                mode text not null,
                difficulty integer not null,
                status text not null,
                started_at text not null,
                completed_at text,
                summary text not null,
                safety_state text not null,
                idempotency_key text not null unique
            );

            create table if not exists msp_training_events (
                event_id text primary key,
                session_id text not null,
                user_id text not null,
                event_type text not null,
                occurred_at text not null,
                payload_json text not null,
                idempotency_key text not null unique
            );

            create table if not exists msp_observations (
                observation_id text primary key,
                user_id text not null,
                skill_id text,
                occurred_at text not null,
                source text not null,
                content text not null,
                tags_json text not null,
                idempotency_key text not null unique
            );

            create table if not exists msp_reflections (
                reflection_id text primary key,
                user_id text not null,
                session_id text,
                skill_id text,
                created_at text not null,
                content text not null,
                insight_tags_json text not null,
                idempotency_key text not null unique
            );

            create table if not exists msp_recommendations (
                recommendation_id text primary key,
                user_id text not null,
                created_at text not null,
                recommended_skill_id text not null,
                recommended_exercise_id text,
                difficulty integer not null,
                reason text not null,
                expires_at text
            );

            create table if not exists rule_catalog_overrides (
                rule_id text primary key,
                version integer not null,
                override_json text not null,
                updated_by text not null,
                updated_at text not null
            );

            create table if not exists rule_version_history (
                id text primary key,
                rule_id text not null,
                version integer not null,
                snapshot_json text not null,
                change_note text not null,
                updated_by text not null,
                updated_at text not null
            );

            create table if not exists user_autonomy_policy (
                user_id text primary key,
                active_role text not null,
                automation_paused integer not null,
                max_daily_minutes integer not null,
                max_challenge_difficulty integer not null,
                allow_auto_order_actions integer not null,
                allow_auto_minimum_viable integer not null,
                priority_weights_json text not null,
                version integer not null,
                updated_at text not null
            );

            create table if not exists ai_usage_log (
                id text primary key,
                user_id text not null,
                usage_type text not null,
                provider text not null,
                model text not null,
                purpose text not null,
                reason text not null,
                tokens_or_seconds integer not null,
                estimated_cost_usd real not null,
                created_at text not null
            );

            create table if not exists tc_tasks (
                id text primary key,
                user_id text not null,
                title text not null,
                description text,
                status text not null,
                priority text not null,
                category text,
                task_type text not null,
                due_at text,
                deadline_at text,
                recurrence_rule text,
                estimated_minutes integer not null,
                source text not null,
                source_object_id text,
                source_url text,
                metadata_json text not null,
                created_at text not null,
                updated_at text not null
            );

            create table if not exists tc_task_instances (
                id text primary key,
                task_id text not null,
                user_id text not null,
                occurrence_date text not null,
                scheduled_at text,
                deadline_at text,
                status text not null,
                completed_at text,
                skipped_at text,
                snoozed_until text,
                alert_count integer not null,
                last_alerted_at text,
                created_at text not null,
                unique(task_id, occurrence_date)
            );

            create table if not exists frogs (
                frog_id text primary key,
                user_id text not null,
                name text not null,
                description text not null,
                domain text not null,
                frog_type text not null,
                importance integer not null,
                resistance_level integer not null,
                difficulty_level integer not null,
                urgency integer not null,
                estimated_minutes integer not null,
                attempts_count integer not null,
                completions_count integer not null,
                last_performed_at text,
                status text not null,
                completion_condition text not null,
                safety_constraints_json text not null,
                created_at text not null,
                updated_at text not null
            );

            create table if not exists frog_logs (
                log_id text primary key,
                frog_id text not null,
                user_id text not null,
                plan_date text not null,
                outcome text not null,
                notes text,
                energy_level integer,
                tension_before integer,
                tension_after integer,
                occurred_at text not null
            );

            create table if not exists daily_frog_selections (
                selection_id text primary key,
                user_id text not null,
                plan_date text not null,
                frog_id text,
                recommended_slot text not null,
                selection_score real not null,
                status text not null,
                explanation text not null,
                rule_evaluation_id text,
                created_at text not null,
                updated_at text not null,
                unique(user_id, plan_date)
            );

            create table if not exists prep_protocols (
                protocol_id text primary key,
                user_id text not null,
                name text not null,
                steps_json text not null,
                breathing_seconds integer not null,
                pleasant_starter_action text,
                pleasant_starter_max_seconds integer not null,
                sampling_interval integer not null,
                executions_count integer not null,
                updated_at text not null
            );

            create table if not exists prep_protocol_logs (
                log_id text primary key,
                protocol_id text not null,
                user_id text not null,
                target_type text not null,
                target_id text,
                sampled integer not null,
                tension_before integer,
                tension_after_prep integer,
                feeling_after_execution text,
                action_started integer not null,
                action_completed integer not null,
                occurred_at text not null
            );

            create table if not exists routines (
                routine_id text primary key,
                user_id text not null,
                name text not null,
                domain text not null,
                automation_kind text not null,
                start_condition text not null,
                action_sequence_json text not null,
                trigger_time_or_event text not null,
                frequency text not null,
                minimum_viable_version text not null,
                estimated_minutes integer not null,
                minimum_minutes integer not null,
                skip_condition text not null,
                completion_condition text not null,
                difficulty_level integer not null,
                flexible_streak_count integer not null,
                completions_count integer not null,
                skips_count integer not null,
                last_completed_at text,
                status text not null,
                created_at text not null,
                updated_at text not null
            );

            create table if not exists routine_logs (
                log_id text primary key,
                routine_id text not null,
                user_id text not null,
                outcome text not null,
                used_minimum_version integer not null,
                resistance_level integer,
                energy_level integer,
                notes text,
                occurred_at text not null
            );

            create table if not exists growth_domains (
                domain_id text primary key,
                user_id text not null,
                slug text not null,
                name text not null,
                tier text not null,
                tier_weight integer not null,
                long_term_goal text not null,
                importance integer not null,
                intervention_level text not null,
                current_level integer not null,
                desired_level integer not null,
                progress_metrics_json text not null,
                last_activity_at text,
                current_challenge_id text,
                desired_frequency_per_week integer not null,
                weekly_activity_count integer not null,
                constraints_json text not null,
                next_evaluation_date text not null,
                updated_at text not null,
                unique(user_id, slug)
            );

            create table if not exists challenges (
                challenge_id text primary key,
                user_id text not null,
                domain_slug text not null,
                challenge_type text not null,
                title text not null,
                goal text not null,
                current_level integer not null,
                difficulty_level integer not null,
                max_approved_difficulty integer not null,
                duration_days integer not null,
                start_condition text not null,
                success_condition text not null,
                progress_metric text not null,
                constraints_json text not null,
                stop_condition text not null,
                review_date text not null,
                consecutive_completions integer not null,
                consecutive_stalls integer not null,
                status text not null,
                created_at text not null,
                updated_at text not null
            );

            create table if not exists challenge_logs (
                log_id text primary key,
                challenge_id text not null,
                user_id text not null,
                outcome text not null,
                pain_or_limitation integer not null,
                perceived_effort integer,
                resistance_level integer,
                recommended_adjustment text not null,
                applied_difficulty integer not null,
                notes text,
                occurred_at text not null
            );

            create table if not exists playful_engagement_state (
                user_id text primary key,
                action_start_points integer not null,
                resistance_mastery_points integer not null,
                exploration_points integer not null,
                stage_level integer not null,
                flexible_active_days integer not null,
                unlocked_achievements_json text not null,
                updated_at text not null
            );

            create table if not exists msp_mental_events (
                event_id text primary key,
                user_id text not null,
                occurred_at text not null,
                event_type text not null,
                training_stage text not null,
                short_description text not null,
                trigger_text text not null,
                initial_emotion_intensity integer,
                defensive_or_attack_urge integer,
                curiosity_ability integer,
                choice_ability integer,
                actual_response text not null,
                recovery_duration_minutes integer,
                notes text,
                reporting_confidence text not null,
                is_silent_win integer not null,
                identified_pattern text,
                lesson_learned text,
                recommended_practice_id text,
                idempotency_key text unique,
                created_at text not null
            );

            create table if not exists msp_silent_win_checks (
                check_id text primary key,
                user_id text not null,
                checked_at text not null,
                silent_wins_recorded integer not null,
                notes text
            );
            """
        )


def json_dump(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def json_load(value: str | None, default: Any) -> Any:
    if not value:
        return default
    return json.loads(value)


def resource_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:12]}"


class PostgresConnection:
    def __init__(self, database_url: str) -> None:
        try:
            import psycopg
            from psycopg.rows import dict_row
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError("Install psycopg to use COMPASS_DATABASE_URL.") from exc
        self._conn = psycopg.connect(database_url, row_factory=dict_row)

    def execute(self, sql: str, params: tuple[Any, ...] | list[Any] = ()) -> Any:
        return self._conn.execute(_pg_sql(sql), params)

    def executescript(self, sql: str) -> None:
        for statement in sql.split(";"):
            if statement.strip():
                self.execute(statement)

    def commit(self) -> None:
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()


def _pg_sql(sql: str) -> str:
    translated = sql.replace("insert or ignore into", "insert into")
    translated = translated.replace("INSERT OR IGNORE INTO", "INSERT INTO")
    if translated != sql and "on conflict" not in translated.lower():
        translated = translated.rstrip()
        translated += " on conflict do nothing"
    return translated.replace("?", "%s")
