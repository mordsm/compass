from __future__ import annotations

from typing import Any

from app.config import get_settings
from app.services.http_adapter import get_json, post_json


class MailManagerAdapter:
    def health(self) -> dict[str, Any]:
        return get_json(get_settings().mail_manager_base_url, "/health")

    def recent_emails(self, limit: int = 10, topic: str | None = None) -> dict[str, Any]:
        path = f"/emails?limit={limit}"
        if topic:
            path += f"&topic={topic}"
        return get_json(get_settings().mail_manager_base_url, path)

    def financial_items(self, limit: int = 20, status: str | None = None) -> dict[str, Any]:
        path = f"/financial-items?limit={limit}"
        if status:
            path += f"&status={status}"
        return get_json(get_settings().mail_manager_base_url, path)

    def daily_report(self, report_date: str | None = None) -> dict[str, Any]:
        path = "/reports/daily"
        if report_date:
            path += f"?date={report_date}"
        return get_json(get_settings().mail_manager_base_url, path)

    def ingest(self, query: str | None = None, max_results: int | None = None) -> dict[str, Any]:
        query_parts = []
        if query:
            query_parts.append(f"q={query}")
        if max_results:
            query_parts.append(f"max_results={max_results}")
        suffix = "?" + "&".join(query_parts) if query_parts else ""
        return post_json(get_settings().mail_manager_base_url, f"/gmail/ingest{suffix}", {})
