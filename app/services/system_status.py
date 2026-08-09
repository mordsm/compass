from __future__ import annotations

import socket
import time
from typing import Any
from urllib.parse import urlsplit

from app.config import get_settings


def local_system_status() -> dict[str, dict[str, Any]]:
    settings = get_settings()
    systems = {
        "self_manage": settings.self_manage_base_url,
        "training": settings.self_trainer_base_url,
        "assessment": settings.assessment_base_url,
        "rules_engine": settings.rules_engine_base_url,
        "mail_manager": settings.mail_manager_base_url,
        "economic_manager": settings.economic_manager_base_url,
        "task_commander": settings.task_commander_base_url,
        "administrative": settings.administrative_base_url,
    }
    return {name: _check_http_port(base_url) for name, base_url in systems.items()}


def _check_http_port(base_url: str, timeout: float = 0.5) -> dict[str, Any]:
    started = time.perf_counter()
    parsed = urlsplit(base_url)
    host = parsed.hostname or "127.0.0.1"
    port = parsed.port or 80
    try:
        with socket.create_connection((host, port), timeout=timeout):
            latency_ms = int((time.perf_counter() - started) * 1000)
            return {"connected": True, "base_url": base_url, "latency_ms": latency_ms, "warning": ""}
    except OSError as exc:
        return {
            "connected": False,
            "base_url": base_url,
            "latency_ms": 0,
            "warning": str(exc),
        }
