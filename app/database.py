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
    return sql.replace("?", "%s")
