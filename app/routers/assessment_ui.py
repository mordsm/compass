from __future__ import annotations

import socket
from urllib.parse import urlsplit

from fastapi import APIRouter, Request
from fastapi.responses import Response

from app.config import get_settings
from app.services.local_agent_launcher import ensure_assessment_running


router = APIRouter(prefix="/assessment-ui", tags=["assessment-ui"])


@router.api_route("/{path:path}", methods=["GET", "POST"], include_in_schema=False)
async def proxy_assessment_ui(path: str, request: Request) -> Response:
    ensure_assessment_running()
    body = await request.body()
    upstream_path = "/" + path
    if request.url.query:
        upstream_path += "?" + request.url.query
    status_code, headers, content = _request_upstream(request.method, upstream_path, body, request.headers.get("content-type"))
    content_type = headers.get("content-type", "")
    if content_type.startswith("text/html"):
        public_prefix = str(request.base_url).rstrip("/") + "/assessment-ui"
        text = content.decode("utf-8", errors="replace")
        text = _rewrite_html(text, public_prefix)
        content = text.encode("utf-8")
    return Response(content=content, status_code=status_code, media_type=content_type or None)


def _request_upstream(method: str, path: str, body: bytes, content_type: str | None) -> tuple[int, dict[str, str], bytes]:
    parsed = urlsplit(get_settings().assessment_base_url)
    host = parsed.hostname or "127.0.0.1"
    port = parsed.port or 80
    headers = [
        f"{method} {path} HTTP/1.1",
        f"Host: {host}:{port}",
        "Accept: */*",
        "Connection: close",
    ]
    if body:
        headers.append(f"Content-Length: {len(body)}")
        if content_type:
            headers.append(f"Content-Type: {content_type}")
    request_bytes = ("\r\n".join(headers) + "\r\n\r\n").encode("utf-8") + body
    with socket.create_connection((host, port), timeout=8.0) as conn:
        conn.settimeout(8.0)
        conn.sendall(request_bytes)
        chunks: list[bytes] = []
        while True:
            chunk = conn.recv(65536)
            if not chunk:
                break
            chunks.append(chunk)
    raw = b"".join(chunks)
    header_bytes, _, response_body = raw.partition(b"\r\n\r\n")
    header_lines = header_bytes.decode("iso-8859-1", errors="replace").splitlines()
    status_code = int(header_lines[0].split()[1]) if header_lines else 502
    response_headers: dict[str, str] = {}
    for line in header_lines[1:]:
        if ":" in line:
            key, value = line.split(":", 1)
            response_headers[key.lower()] = value.strip()
    return status_code, response_headers, response_body


def _rewrite_html(text: str, public_prefix: str) -> str:
    replacements = {
        'href="/': f'href="{public_prefix}/',
        'src="/': f'src="{public_prefix}/',
        'action="/': f'action="{public_prefix}/',
        "href='/": f"href='{public_prefix}/",
        "src='/": f"src='{public_prefix}/",
        "action='/": f"action='{public_prefix}/",
    }
    for source, target in replacements.items():
        text = text.replace(source, target)
    return text
