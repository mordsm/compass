from __future__ import annotations

from fastapi import APIRouter, Depends

from app.auth import require_actions_key
from app.schemas.context import MorningContextRequest, MorningContextResponse
from app.services.context_service import ContextService

router = APIRouter(prefix="/api/context", tags=["context"], dependencies=[Depends(require_actions_key)])


@router.post("/morning", response_model=MorningContextResponse, operation_id="getMorningContext")
def get_morning_context(request: MorningContextRequest) -> dict:
    return ContextService().morning_context(
        user_id=request.user_id,
        target_date=request.date,
        timezone=request.timezone,
        include=request.include,
    )
