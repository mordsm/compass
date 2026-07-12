from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


Importance = Literal["low", "medium", "high", "critical"]
TaskStatus = Literal["mentioned", "proposed", "approved", "active", "open", "done", "cancelled"]


class IdempotentRequest(BaseModel):
    idempotency_key: str | None = Field(default=None, description="Unique key for write retries.")


class WriteResult(BaseModel):
    success: bool
    status: str
    resource_id: str
    already_existed: bool = False
    approval_request_id: str | None = None
    warnings: list[str] = Field(default_factory=list)
    downstream: dict[str, Any] = Field(default_factory=dict)
