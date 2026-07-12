from __future__ import annotations

from fastapi import APIRouter, Depends

from app.auth import require_actions_key
from app.repository import CompassRepository
from app.schemas.common import WriteResult
from app.schemas.conversations import ConversationEventRequest, FinalizeConversationRequest

router = APIRouter(prefix="/api/conversation", tags=["conversation"], dependencies=[Depends(require_actions_key)])


@router.post("/event", response_model=WriteResult, operation_id="recordConversationEvent")
def record_conversation_event(request: ConversationEventRequest) -> dict:
    repo = CompassRepository()
    if request.idempotency_key and (cached := repo.get_idempotent_response(request.idempotency_key)):
        return {**cached, "already_existed": True}
    payload = request.model_dump(mode="json")
    result = repo.save_conversation_event(payload)
    repo.audit("conversation.event", request.user_id, payload)
    repo.remember_idempotent_response(request.idempotency_key, "conversation.event", result)
    return result


@router.post("/finalize", response_model=WriteResult, operation_id="finalizeConversation")
def finalize_conversation(request: FinalizeConversationRequest) -> dict:
    repo = CompassRepository()
    if request.idempotency_key and (cached := repo.get_idempotent_response(request.idempotency_key)):
        return {**cached, "already_existed": True}
    payload = request.model_dump(mode="json")
    result = repo.finalize_conversation(payload)
    repo.audit("conversation.finalize", request.user_id, payload)
    repo.remember_idempotent_response(request.idempotency_key, "conversation.finalize", result)
    return result
