from __future__ import annotations

from typing import Any

from app.config import get_settings
from app.services.http_adapter import get_json


class SelfManagementAdapter:
    def get_today(self) -> dict[str, Any]:
        return get_json(get_settings().self_manage_base_url, "/api/today")

    def get_hourly_reminder(self) -> dict[str, Any]:
        return get_json(get_settings().self_manage_base_url, "/api/hourly-reminder")
