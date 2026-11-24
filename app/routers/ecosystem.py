from __future__ import annotations

from fastapi import APIRouter

from app.schemas.ecosystem import EcosystemPatchRequest, EcosystemPatchResponse, EcosystemStateEnvelope
from app.services.ecosystem_hub import service

router = APIRouter(prefix="/api/ecosystem", tags=["ecosystem"])


@router.get("/state", response_model=EcosystemStateEnvelope, operation_id="getEcosystemHubState")
def get_ecosystem_state() -> dict:
    return service.get_state_envelope()


@router.post("/state", response_model=EcosystemPatchResponse, operation_id="saveEcosystemHubState")
def save_ecosystem_state(request: EcosystemPatchRequest) -> dict:
    return service.save_patch(request)
