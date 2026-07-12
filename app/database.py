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


def connect() -> sqlite3.Connection:
    path = Path(get_settings().database_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


@contextmanager
def db() -> Iterator[sqlite3.Connection]:
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
