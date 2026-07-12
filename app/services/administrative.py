from __future__ import annotations

from typing import Any

from app.config import get_settings
from app.services.http_adapter import get_json, post_json


class AdministrativeAdapter:
    def health(self) -> dict[str, Any]:
        return get_json(get_settings().administrative_base_url, "/health")

    def obligations(self, user_id: str, status: str = "open") -> dict[str, Any]:
        return get_json(
            get_settings().administrative_base_url,
            f"/api/obligations?user_id={user_id}&status={status}",
        )

    def cases(self, user_id: str, status: str = "open") -> dict[str, Any]:
        return get_json(
            get_settings().administrative_base_url,
            f"/api/cases?user_id={user_id}&status={status}",
        )

    def record_obligation(self, payload: dict[str, Any]) -> dict[str, Any]:
        return post_json(get_settings().administrative_base_url, "/api/obligations", payload)
