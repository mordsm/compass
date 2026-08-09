from __future__ import annotations

from fastapi import APIRouter, Depends

from app.auth import require_actions_key
from app.schemas.training import (
    TrainingContextRequest,
    TrainingHistorySearchRequest,
    TrainingProgressRequest,
    TrainingSessionRequest,
)
from app.services.self_trainer import SelfTrainerAdapter

router = APIRouter(prefix="/api/training", tags=["training"], dependencies=[Depends(require_actions_key)])


@router.post("/context", operation_id="loadTrainingContext")
def load_training_context(request: TrainingContextRequest) -> dict:
    return SelfTrainerAdapter().context(user_id=request.user_id)


@router.post("/sessions", operation_id="saveTrainingSession")
def save_training_session(request: TrainingSessionRequest) -> dict:
    return SelfTrainerAdapter().save_session(request.model_dump(mode="json"))


@router.post("/history/search", operation_id="searchTrainingHistory")
def search_training_history(request: TrainingHistorySearchRequest) -> dict:
    return SelfTrainerAdapter().search_history(request.model_dump(mode="json"))


@router.post("/progress", operation_id="getProgressReview")
def get_progress_review(request: TrainingProgressRequest) -> dict:
    return SelfTrainerAdapter().progress(user_id=request.user_id, period=request.period)
