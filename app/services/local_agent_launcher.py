from __future__ import annotations

import os
import socket
import subprocess
import time
from pathlib import Path
from urllib.parse import urlsplit

from app.config import get_settings


_PROCESSES: dict[str, subprocess.Popen] = {}


def ensure_assessment_running() -> None:
    settings = get_settings()
    ensure_local_service(
        name="personal_Assessment",
        base_url=settings.assessment_base_url,
        project_path=settings.assessment_path,
        command=["uv", "run", "personal-assessment"],
        env_from_url=True,
    )


def ensure_economic_spending_running() -> None:
    settings = get_settings()
    ensure_local_service(
        name="economic_spending",
        base_url=settings.economic_spending_base_url,
        project_path=settings.economic_spending_path,
        command=["uv", "run", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", _port(settings.economic_spending_base_url)],
    )


def ensure_local_service(
    *,
    name: str,
    base_url: str,
    project_path: Path,
    command: list[str],
    env_from_url: bool = False,
) -> None:
    settings = get_settings()
    if not settings.autostart_local_agents or not _is_local_http(base_url):
        return
    host, port = _host_port(base_url)
    if _port_open(host, port):
        return
    existing = _PROCESSES.get(name)
    if existing and existing.poll() is None:
        _wait_for_port(host, port, settings.autostart_wait_seconds)
        return

    resolved_path = project_path.resolve()
    if not resolved_path.exists():
        return

    env = os.environ.copy()
    if env_from_url:
        env["HOST"] = host
        env["PORT"] = str(port)

    log_dir = Path("logs")
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = (log_dir / f"{name}.autostart.log").open("ab")

    creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    _PROCESSES[name] = subprocess.Popen(
        command,
        cwd=resolved_path,
        env=env,
        stdout=log_file,
        stderr=subprocess.STDOUT,
        stdin=subprocess.DEVNULL,
        creationflags=creationflags,
    )
    _wait_for_port(host, port, settings.autostart_wait_seconds)


def _is_local_http(base_url: str) -> bool:
    parsed = urlsplit(base_url)
    return parsed.scheme == "http" and (parsed.hostname or "").lower() in {"127.0.0.1", "localhost"}


def _host_port(base_url: str) -> tuple[str, int]:
    parsed = urlsplit(base_url)
    return parsed.hostname or "127.0.0.1", parsed.port or 80


def _port(base_url: str) -> str:
    return str(_host_port(base_url)[1])


def _port_open(host: str, port: int) -> bool:
    try:
        with socket.create_connection((host, port), timeout=0.5):
            return True
    except OSError:
        return False


def _wait_for_port(host: str, port: int, timeout_seconds: float) -> None:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        if _port_open(host, port):
            return
        time.sleep(0.25)
