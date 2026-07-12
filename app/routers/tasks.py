from __future__ import annotations

from fastapi import APIRouter, Depends

from app.auth import require_actions_key
from app.repository import CompassRepository
from app.schemas.common import WriteResult
from app.schemas.tasks import UpsertTaskRequest

router = APIRouter(prefix="/api/tasks", tags=["tasks"], dependencies=[Depends(require_actions_key)])


@router.post("/upsert", response_model=WriteResult, operation_id="upsertTask")
def upsert_task(request: UpsertTaskRequest) -> dict:
    repo = CompassRepository()
    if request.idempotency_key and (cached := repo.get_idempotent_response(request.idempotency_key)):
        return {**cached, "already_existed": True}
    payload = request.model_dump(mode="json")
    result = repo.upsert_task(payload)
    repo.audit("tasks.upsert", request.user_id, payload)
    repo.remember_idempotent_response(request.idempotency_key, "tasks.upsert", result)
    return result
