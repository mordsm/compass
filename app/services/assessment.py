from __future__ import annotations

from typing import Any

from app.config import get_settings
from app.services.http_adapter import get_json


class AssessmentAdapter:
    def list_recent(self) -> dict[str, Any]:
        return get_json(get_settings().assessment_base_url, "/api/assessments")

    def list_objective_results(self) -> dict[str, Any]:
        return get_json(get_settings().assessment_base_url, "/api/assessments/objective")
