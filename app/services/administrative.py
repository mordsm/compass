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

    def open_case(self, payload: dict[str, Any]) -> dict[str, Any]:
        return post_json(get_settings().administrative_base_url, "/api/cases/open-case", payload)

    def add_case_event(self, case_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        return post_json(get_settings().administrative_base_url, f"/api/cases/{case_id}/events", payload)

    def add_case_document(self, case_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        return post_json(get_settings().administrative_base_url, f"/api/cases/{case_id}/documents", payload)

    def add_case_checklist_item(self, case_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        return post_json(get_settings().administrative_base_url, f"/api/cases/{case_id}/checklist", payload)

    def draft_case_communication(self, case_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        return post_json(
            get_settings().administrative_base_url,
            f"/api/cases/{case_id}/communications/draft",
            payload,
        )
