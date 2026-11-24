from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import RedirectResponse

router = APIRouter(tags=["health"])


@router.get("/", include_in_schema=False)
def root() -> RedirectResponse:
    return RedirectResponse(url="/control-center/")


@router.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "compass"}

