from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.auth import require_actions_key
from app.repository import CompassRepository

router = APIRouter(
    prefix="/api/progress",
    tags=["progress"],
    dependencies=[Depends(require_actions_key)],
)


@router.get("/weekly", operation_id="getWeeklyProgress")
def get_weekly_progress(
    user_id: str = Query(..., min_length=1),
    week_start: str | None = Query(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$"),
) -> dict:
    """Return deterministic weekly metrics derived from Compass records."""
    return CompassRepository().get_weekly_progress(user_id=user_id, week_start=week_start)
