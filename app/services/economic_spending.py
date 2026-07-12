from __future__ import annotations

from typing import Any

from app.config import get_settings
from app.services.http_adapter import get_json, post_json


class EconomicSpendingAdapter:
    def health(self) -> dict[str, Any]:
        return get_json(get_settings().economic_spending_base_url, "/health")

    def summary(self, user_id: str, days: int = 30) -> dict[str, Any]:
        return get_json(
            get_settings().economic_spending_base_url,
            f"/api/spending/summary?user_id={user_id}&days={days}",
        )

    def record_event(self, payload: dict[str, Any]) -> dict[str, Any]:
        return post_json(get_settings().economic_spending_base_url, "/api/spending/event", payload)
