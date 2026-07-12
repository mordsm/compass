from __future__ import annotations

import json
import socket
from typing import Any
from urllib.parse import urlsplit


def get_json(base_url: str, path: str, timeout: float = 3.0) -> dict[str, Any]:
    if not base_url:
        return {"connected": False, "warning": "base URL is not configured"}
    url = base_url.rstrip("/") + "/" + path.lstrip("/")
    try:
        body = _request("GET", url, None, timeout=timeout)
        return {"connected": True, "url": url, "result": json.loads(body or "{}")}
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return {"connected": False, "url": url, "warning": str(exc)}


def post_json(base_url: str, path: str, payload: dict[str, Any], timeout: float = 5.0) -> dict[str, Any]:
    if not base_url:
        return {"connected": False, "warning": "base URL is not configured"}
    url = base_url.rstrip("/") + "/" + path.lstrip("/")
    try:
        response_body = _request("POST", url, json.dumps(payload).encode("utf-8"), timeout=timeout)
        return {"connected": True, "url": url, "result": json.loads(response_body or "{}")}
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return {"connected": False, "url": url, "warning": str(exc)}


def _request(method: str, url: str, body: bytes | None, timeout: float) -> str:
    parsed = urlsplit(url)
    if parsed.scheme != "http":
        raise ValueError("local agent adapter only supports http URLs")
    host = parsed.hostname or "127.0.0.1"
    port = parsed.port or 80
    target = parsed.path or "/"
    if parsed.query:
        target += "?" + parsed.query

    body = body or b""
    headers = [
        f"{method} {target} HTTP/1.1",
        f"Host: {host}:{port}",
        "Accept: application/json",
        "Connection: close",
    ]
    if method == "POST":
        headers.extend(
            [
                "Content-Type: application/json",
                f"Content-Length: {len(body)}",
            ]
        )
    request_bytes = ("\r\n".join(headers) + "\r\n\r\n").encode("utf-8") + body

    with socket.create_connection((host, port), timeout=timeout) as conn:
        conn.settimeout(timeout)
        conn.sendall(request_bytes)
        chunks = []
        while True:
            chunk = conn.recv(65536)
            if not chunk:
                break
            chunks.append(chunk)

    raw = b"".join(chunks)
    header_bytes, _, response_body = raw.partition(b"\r\n\r\n")
    status_line = header_bytes.splitlines()[0].decode("iso-8859-1") if header_bytes else ""
    if " 200 " not in status_line:
        raise ValueError(status_line or "empty HTTP response")
    return response_body.decode("utf-8")
