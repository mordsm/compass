from __future__ import annotations

from datetime import date as dt_date
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.services.cycle_service import ProactiveCycleService

router = APIRouter(prefix="/api/cycles", tags=["proactive-cycles"])


class MorningCycleRequest(BaseModel):
    user_id: str = "moshe"
    date: dt_date | None = None
    energy_level: int = Field(default=3, ge=1, le=5)
    available_minutes: int = Field(default=180, ge=15, le=960)
    outcomes: list[str] | None = None
    extra_tasks: list[dict[str, Any]] | None = None
    idempotency_key: str | None = None


class IntradayCycleRequest(BaseModel):
    user_id: str = "moshe"
    date: dt_date | None = None
    energy_level: int = Field(default=3, ge=1, le=5)
    available_minutes: int = Field(default=60, ge=5, le=960)
    recent_unanswered_reminders: int = Field(default=0, ge=0)


class EveningCycleRequest(BaseModel):
    user_id: str = "moshe"
    date: dt_date | None = None
    wins_today: list[str] = Field(default_factory=list)
    difficulties_today: list[str] = Field(default_factory=list)
    notes_for_tomorrow: str = ""


class WeeklyCycleRequest(BaseModel):
    user_id: str = "moshe"
    silent_wins: list[dict[str, Any]] = Field(default_factory=list)
    notes: str = ""


class MonthlyCycleRequest(BaseModel):
    user_id: str = "moshe"
    minimum_events_required: int = Field(default=5, ge=2, le=50)
    proposed_policy_changes: dict[str, Any] | None = None


class QuickCaptureRequest(BaseModel):
    user_id: str = "moshe"
    text: str
    channel: str = Field(default="voice", description="voice | telegram | web")
    speech_seconds: int = Field(default=0, ge=0)
    tts_seconds: int = Field(default=0, ge=0)
    llm_available: bool = True


@router.post("/morning", operation_id="runMorningProactiveCycle")
def run_morning_cycle(request: MorningCycleRequest) -> dict[str, Any]:
    return ProactiveCycleService().run_morning_cycle(
        user_id=request.user_id,
        target_date=request.date,
        energy_level=request.energy_level,
        available_minutes=request.available_minutes,
        outcomes=request.outcomes,
        extra_tasks=request.extra_tasks,
        idempotency_key=request.idempotency_key,
    )


@router.post("/intraday", operation_id="runIntradayProactiveCycle")
def run_intraday_cycle(request: IntradayCycleRequest) -> dict[str, Any]:
    return ProactiveCycleService().run_intraday_cycle(
        user_id=request.user_id,
        target_date=request.date,
        energy_level=request.energy_level,
        available_minutes=request.available_minutes,
        recent_unanswered_reminders=request.recent_unanswered_reminders,
    )


@router.post("/evening", operation_id="runEveningProactiveCycle")
def run_evening_cycle(request: EveningCycleRequest) -> dict[str, Any]:
    return ProactiveCycleService().run_evening_cycle(
        user_id=request.user_id,
        target_date=request.date,
        wins_today=request.wins_today,
        difficulties_today=request.difficulties_today,
        notes_for_tomorrow=request.notes_for_tomorrow,
    )


@router.post("/weekly", operation_id="runWeeklyProactiveCycle")
def run_weekly_cycle(request: WeeklyCycleRequest) -> dict[str, Any]:
    return ProactiveCycleService().run_weekly_cycle(
        user_id=request.user_id,
        silent_wins=request.silent_wins,
        notes=request.notes,
    )


@router.post("/monthly", operation_id="runMonthlyProactiveCycle")
def run_monthly_cycle(request: MonthlyCycleRequest) -> dict[str, Any]:
    return ProactiveCycleService().run_monthly_cycle(
        user_id=request.user_id,
        minimum_events_required=request.minimum_events_required,
        proposed_policy_changes=request.proposed_policy_changes,
    )


@router.post("/quick-capture", operation_id="processProactiveQuickCapture")
def process_quick_capture(request: QuickCaptureRequest) -> dict[str, Any]:
    return ProactiveCycleService().process_quick_capture(
        user_id=request.user_id,
        text=request.text,
        channel=request.channel,
        speech_seconds=request.speech_seconds,
        tts_seconds=request.tts_seconds,
        llm_available=request.llm_available,
    )
