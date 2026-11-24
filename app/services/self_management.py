from __future__ import annotations

import os
import subprocess
import sys
from typing import Any
import webbrowser

from app.config import get_settings
from app.services.http_adapter import get_json, post_json
from app.services.local_agent_launcher import ensure_self_manage_running


class SelfManagementAdapter:
    def ui_urls(self, plan_item_id: int | str | None = None) -> dict[str, str]:
        base_url = get_settings().self_manage_base_url.rstrip("/")
        urls = {
            "today": f"{base_url}/static/index.html",
            "profile": f"{base_url}/static/profile.html",
        }
        if plan_item_id:
            urls["session"] = f"{base_url}/static/session.html?plan_item_id={plan_item_id}"
        return urls

    def open_ui(self, plan_item_id: int | str | None = None) -> dict[str, Any]:
        ensure_self_manage_running()
        urls = self.ui_urls(plan_item_id)
        target = urls.get("session") or urls["today"]
        warnings = []

        try:
            if sys.platform.startswith("win"):
                os.startfile(target)  # type: ignore[attr-defined]
                return {"opened": True, "url": target, "urls": urls, "open_method": "os.startfile"}
        except Exception as exc:  # pragma: no cover - depends on local desktop integration
            warnings.append(str(exc))

        try:
            if sys.platform.startswith("win"):
                subprocess.run(
                    [
                        "powershell",
                        "-NoProfile",
                        "-Command",
                        "Start-Process",
                        target,
                    ],
                    check=True,
                    timeout=5,
                )
                return {
                    "opened": True,
                    "url": target,
                    "urls": urls,
                    "open_method": "powershell.Start-Process",
                    "warning": "; ".join(warnings) if warnings else "",
                }
        except Exception as exc:  # pragma: no cover - depends on local desktop integration
            warnings.append(str(exc))

        try:
            opened = bool(webbrowser.open(target, new=2))
            return {
                "opened": opened,
                "url": target,
                "urls": urls,
                "open_method": "webbrowser.open",
                "warning": "; ".join(warnings) if warnings else "",
            }
        except Exception as exc:  # pragma: no cover - depends on local desktop integration
            warnings.append(str(exc))
            return {"opened": False, "url": target, "urls": urls, "warning": "; ".join(warnings)}

    def list_domains(self) -> dict[str, Any]:
        ensure_self_manage_running()
        return get_json(get_settings().self_manage_base_url, "/api/domains")

    def list_exercises(self) -> dict[str, Any]:
        ensure_self_manage_running()
        return get_json(get_settings().self_manage_base_url, "/api/exercises", timeout=3.0)

    def list_cardio_candidates(self) -> dict[str, Any]:
        ensure_self_manage_running()
        return get_json(get_settings().self_manage_base_url, "/api/exercises/cardio-candidates", timeout=3.0)

    def get_today(self) -> dict[str, Any]:
        ensure_self_manage_running()
        return get_json(get_settings().self_manage_base_url, "/api/today")

    def get_hourly_reminder(self) -> dict[str, Any]:
        ensure_self_manage_running()
        return get_json(get_settings().self_manage_base_url, "/api/hourly-reminder")

    def generate_today(self, profile: dict[str, Any] | None = None, overwrite: bool = True) -> dict[str, Any]:
        ensure_self_manage_running()
        return post_json(
            get_settings().self_manage_base_url,
            "/api/today/generate",
            {"overwrite": overwrite, "profile": profile},
        )

    def log_session(
        self,
        plan_item_id: int | str,
        completed: bool = True,
        minutes: int = 10,
        notes: str | None = None,
    ) -> dict[str, Any]:
        ensure_self_manage_running()
        return post_json(
            get_settings().self_manage_base_url,
            f"/api/session/{plan_item_id}/log",
            {
                "completed": completed,
                "minutes": minutes,
                "notes": notes or "Logged via Accountability Coach",
            },
        )
