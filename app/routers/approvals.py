from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.auth import require_actions_key
from app.repository import CompassRepository
from app.schemas.approvals import ApprovalRequest, CreateApprovalRequest, DecideApprovalRequest
from app.schemas.common import WriteResult

router = APIRouter(prefix="/api/approvals", tags=["approvals"], dependencies=[Depends(require_actions_key)])


@router.post("", response_model=WriteResult, operation_id="createApprovalRequest")
def create_approval_request(request: CreateApprovalRequest) -> dict:
    repo = CompassRepository()
    if request.idempotency_key and (cached := repo.get_idempotent_response(request.idempotency_key)):
        return {**cached, "already_existed": True}
    payload = request.model_dump(mode="json")
    result = repo.create_approval_request(payload)
    repo.audit("approvals.create", request.user_id, payload)
    repo.remember_idempotent_response(request.idempotency_key, "approvals.create", result)
    return result


@router.get("", response_model=list[ApprovalRequest], operation_id="listApprovalRequests")
def list_approval_requests(user_id: str, status: str = "pending", limit: int = 50) -> list[dict]:
    return CompassRepository().list_approval_requests(user_id=user_id, status=status, limit=limit)


@router.get("/{approval_id}", response_model=ApprovalRequest, operation_id="getApprovalRequest")
def get_approval_request(approval_id: str) -> dict:
    approval = CompassRepository().get_approval_request(approval_id)
    if not approval:
        raise HTTPException(status_code=404, detail="approval-not-found")
    return approval


@router.post("/{approval_id}/approve", response_model=ApprovalRequest, operation_id="approveRequest")
def approve_request(approval_id: str, request: DecideApprovalRequest) -> dict:
    repo = CompassRepository()
    approval = repo.decide_approval_request(
        approval_id=approval_id,
        status="approved",
        decision_by=request.decision_by,
        decision_notes=request.decision_notes,
    )
    if not approval:
        raise HTTPException(status_code=404, detail="approval-not-found")
    repo.audit("approvals.approve", request.user_id, {"approval_id": approval_id, **request.model_dump(mode="json")})
    return approval


@router.post("/{approval_id}/reject", response_model=ApprovalRequest, operation_id="rejectRequest")
def reject_request(approval_id: str, request: DecideApprovalRequest) -> dict:
    repo = CompassRepository()
    approval = repo.decide_approval_request(
        approval_id=approval_id,
        status="rejected",
        decision_by=request.decision_by,
        decision_notes=request.decision_notes,
    )
    if not approval:
        raise HTTPException(status_code=404, detail="approval-not-found")
    repo.audit("approvals.reject", request.user_id, {"approval_id": approval_id, **request.model_dump(mode="json")})
    return approval
