from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path
from typing import Any

import psycopg

from app.database import init_db


TABLES = [
    "idempotency_keys",
    "conversation_events",
    "conversation_summaries",
    "tasks",
    "daily_plans",
    "approval_requests",
    "audit_log",
    "rule_evaluations",
    "financial_transactions",
    "financial_memories",
    "financial_settings",
    "financial_alerts",
    "ecosystem_hub_state",
]


def main() -> None:
    parser = argparse.ArgumentParser(description="Migrate Compass SQLite data into Postgres.")
    parser.add_argument("--sqlite-path", default="data/compass.db")
    parser.add_argument(
        "--postgres-url",
        default="postgresql://compass:compass@127.0.0.1:55436/compass",
    )
    args = parser.parse_args()

    sqlite_path = Path(args.sqlite_path)
    if not sqlite_path.exists():
        raise SystemExit(f"SQLite database not found: {sqlite_path}")

    import os

    os.environ["COMPASS_DATABASE_URL"] = args.postgres_url
    init_db()

    sqlite_conn = sqlite3.connect(sqlite_path)
    sqlite_conn.row_factory = sqlite3.Row
    with sqlite_conn, psycopg.connect(args.postgres_url) as pg_conn:
        for table in TABLES:
            if not _sqlite_table_exists(sqlite_conn, table):
                continue
            rows = sqlite_conn.execute(f"select * from {table}").fetchall()
            if not rows:
                print(f"{table}: 0")
                continue
            columns = rows[0].keys()
            placeholders = ", ".join(["%s"] * len(columns))
            column_list = ", ".join(columns)
            sql = f"insert into {table} ({column_list}) values ({placeholders}) on conflict do nothing"
            pg_conn.executemany(sql, [tuple(row[column] for column in columns) for row in rows])
            print(f"{table}: {len(rows)}")


def _sqlite_table_exists(connection: sqlite3.Connection, table: str) -> bool:
    row: Any = connection.execute(
        "select name from sqlite_master where type = 'table' and name = ?",
        (table,),
    ).fetchone()
    return row is not None


if __name__ == "__main__":
    main()
