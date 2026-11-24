from __future__ import annotations

from typing import Any

from app.config import get_settings
from app.services.http_adapter import get_json, post_json
from app.services.local_agent_launcher import ensure_economic_manager_running


class EconomicManagerAdapter:
    def health(self) -> dict[str, Any]:
        ensure_economic_manager_running()
        return get_json(get_settings().economic_manager_base_url, "/health")

    def summary(self, household_id: str = "moshe_household", days: int = 30) -> dict[str, Any]:
        ensure_economic_manager_running()
        return get_json(
            get_settings().economic_manager_base_url,
            f"/api/summary?household_id={household_id}&days={days}",
        )

    def cashflow(self, household_id: str = "moshe_household", year: int | None = None, month: int | None = None) -> dict[str, Any]:
        ensure_economic_manager_running()
        query = f"/api/cashflow?household_id={household_id}"
        if year:
            query += f"&year={year}"
        if month:
            query += f"&month={month}"
        return get_json(get_settings().economic_manager_base_url, query)

    def record_transaction(self, payload: dict[str, Any]) -> dict[str, Any]:
        ensure_economic_manager_running()
        return post_json(get_settings().economic_manager_base_url, "/api/transactions", payload)

    def import_csv(self, payload: dict[str, Any]) -> dict[str, Any]:
        ensure_economic_manager_running()
        return post_json(get_settings().economic_manager_base_url, "/api/import/csv", payload)

    def import_financial_items(self, payload: dict[str, Any]) -> dict[str, Any]:
        ensure_economic_manager_running()
        return post_json(get_settings().economic_manager_base_url, "/api/import/financial-items", payload)

    def ingest_sources(self, payload: dict[str, Any]) -> dict[str, Any]:
        ensure_economic_manager_running()
        return post_json(get_settings().economic_manager_base_url, "/api/import/sources", payload)

    def invoke_agent(self, payload: dict[str, Any]) -> dict[str, Any]:
        ensure_economic_manager_running()
        return post_json(get_settings().economic_manager_base_url, "/api/agent/invoke", payload)
