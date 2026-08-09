from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/")
def root() -> dict[str, str]:
    return {
        "status": "ok",
        "service": "compass",
        "health_url": "/api/health",
    }


@router.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "compass"}
