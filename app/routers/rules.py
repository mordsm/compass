from __future__ import annotations

from fastapi import APIRouter, Depends

from app.auth import require_actions_key
from app.schemas.rules import RulesEventRequest
from app.services.rules_engine import RulesEngineAdapter

router = APIRouter(prefix="/api/rules", tags=["rules"], dependencies=[Depends(require_actions_key)])


@router.post("/events", operation_id="submitEventToRulesEngine")
def submit_event_to_rules_engine(request: RulesEventRequest) -> dict:
    context = {
        **request.context,
        "event_type": request.event_type,
        "user_id": request.user_id,
        "signals": request.signals,
        "dry_run": request.dry_run,
    }
    return RulesEngineAdapter().evaluate(context=context, actor=request.actor or request.user_id)
