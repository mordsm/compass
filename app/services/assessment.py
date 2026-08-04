from __future__ import annotations

from typing import Any

from app.config import get_settings
from app.services.http_adapter import get_json, post_json
from app.services.local_agent_launcher import ensure_assessment_running


class AssessmentAdapter:
    def list_recent(self) -> dict[str, Any]:
        ensure_assessment_running()
        return get_json(get_settings().assessment_base_url, "/api/assessments")

    def list_objective_results(self) -> dict[str, Any]:
        ensure_assessment_running()
        return get_json(get_settings().assessment_base_url, "/api/assessments/objective")

    def invoke_agent(self, payload: dict[str, Any]) -> dict[str, Any]:
        ensure_assessment_running()
        return post_json(get_settings().assessment_base_url, "/api/agent/invoke", payload)
