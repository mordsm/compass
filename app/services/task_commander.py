from __future__ import annotations

from typing import Any

from app.config import get_settings
from app.services.http_adapter import get_json, post_json


class TaskCommanderAdapter:
    def health(self) -> dict[str, Any]:
        return get_json(get_settings().task_commander_base_url, "/health")

    def status(self, limit: int = 10) -> dict[str, Any]:
        return get_json(get_settings().task_commander_base_url, f"/status?limit={limit}")

    def today(self, limit: int = 20) -> dict[str, Any]:
        return get_json(get_settings().task_commander_base_url, f"/today?limit={limit}")

    def overdue(self, limit: int = 20) -> dict[str, Any]:
        return get_json(get_settings().task_commander_base_url, f"/overdue?limit={limit}")

    def create_task(self, payload: dict[str, Any]) -> dict[str, Any]:
        return post_json(get_settings().task_commander_base_url, "/tasks", payload)

    def generate_instances(self, days: int = 2) -> dict[str, Any]:
        return post_json(get_settings().task_commander_base_url, f"/instances/generate?days={days}", {})

    def mark_done(self, instance_id: str) -> dict[str, Any]:
        return post_json(get_settings().task_commander_base_url, f"/instances/{instance_id}/done", {})

    def snooze(self, instance_id: str, minutes: int = 60) -> dict[str, Any]:
        return post_json(
            get_settings().task_commander_base_url,
            f"/instances/{instance_id}/snooze",
            {"minutes": minutes},
        )

    def skip(self, instance_id: str) -> dict[str, Any]:
        return post_json(get_settings().task_commander_base_url, f"/instances/{instance_id}/skip", {})
