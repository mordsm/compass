from __future__ import annotations

from typing import Any
from urllib.parse import urlencode

from app.config import get_settings
from app.services.http_adapter import get_json, post_json


class SelfTrainerAdapter:
    def context(self, user_id: str) -> dict[str, Any]:
        query = urlencode({"user_id": user_id})
        return get_json(get_settings().self_trainer_base_url, f"/training/context?{query}")

    def save_session(self, payload: dict[str, Any]) -> dict[str, Any]:
        return post_json(get_settings().self_trainer_base_url, "/training/sessions", payload)

    def search_history(self, payload: dict[str, Any]) -> dict[str, Any]:
        return post_json(get_settings().self_trainer_base_url, "/training/history/search", payload)

    def progress(self, user_id: str, period: str = "last_30_days") -> dict[str, Any]:
        query = urlencode({"user_id": user_id, "period": period})
        return get_json(get_settings().self_trainer_base_url, f"/training/progress?{query}")
