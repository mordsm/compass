from __future__ import annotations

from typing import Any
import webbrowser

from app.config import Settings, get_settings
from app.services.http_adapter import get_json, post_json
from app.services.local_agent_launcher import ensure_assessment_running


class AssessmentAdapter:
    def list_recent(self) -> dict[str, Any]:
        ensure_assessment_running()
        return get_json(get_settings().assessment_base_url, "/api/assessments", timeout=5.0)

    def list_objective_results(self) -> dict[str, Any]:
        ensure_assessment_running()
        return get_json(get_settings().assessment_base_url, "/api/assessments/objective", timeout=5.0)

    def invoke_agent(self, payload: dict[str, Any]) -> dict[str, Any]:
        ensure_assessment_running()
        return post_json(get_settings().assessment_base_url, "/api/agent/invoke", payload, timeout=8.0)

    def ui_urls(self) -> dict[str, str]:
        settings = get_settings()
        public_base_url = Settings().public_base_url
        if public_base_url.startswith("https://"):
            base_url = public_base_url.rstrip("/") + "/assessment-ui"
        else:
            base_url = settings.assessment_base_url.rstrip("/")
        return {
            "home": f"{base_url}/",
            "assessments": f"{base_url}/assessments",
            "battery": f"{base_url}/battery",
            "focus": f"{base_url}/assessments/focus",
            "energy": f"{base_url}/assessments/energy",
            "mental": f"{base_url}/assessments/mental",
            "physical": f"{base_url}/assessments/physical",
        }

    def open_ui(self, target: str = "battery") -> dict[str, Any]:
        ensure_assessment_running()
        urls = self.ui_urls()
        url = urls.get(target, urls["battery"])
        opened = webbrowser.open(url, new=2)
        return {"opened": bool(opened), "target": target, "url": url, "urls": urls}
