from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services.unified_v6_service import UnifiedV6Service

router = APIRouter(prefix="/api/v6", tags=["unified-v6"])


class CreateV6ActivityTemplateRequest(BaseModel):
    user_id: str = "moshe"
    name: str = ""
    aliases: list[str] = Field(default_factory=list)
    description: str = ""
    open_time: str = "06:00"
    preferred_time: str = "09:10"
    window_end_time: str = "21:00"
    check_time: str = "10:00"
    frequency: str = "daily"
    content_blocks: list[dict[str, Any]] = Field(default_factory=list)
    media_only: bool = False
    completion_condition: str = "דיווח עצמי או סימון השלמה"
    evidence_type: str = "self_report"
    estimated_minutes: int = 20
    minimum_viable_version: str = "2 דקות צעד ראשון קטן"
    importance: int = 7
    impact: int = 7
    difficulty: int = 5
    energy_requirement: int = 3
    exception_action: str = "offer_completion_or_clarify"
    ttl_policy: str = "close_daily_without_debt"
    goal_ids: list[str] = Field(default_factory=list)
    rule_id: str | None = None
    instantiate_for_today: bool = True
    instance_date: str | None = None
    current_time: str = "08:00"


class ReportV6InstanceExecutionRequest(BaseModel):
    user_id: str = "moshe"
    outcome: str = "completed"
    source: str = "checkbox_web"
    reported_execution_at: str | None = None
    partial_value: float | None = None
    partial_unit: str | None = None
    partial_target: float | None = None
    partial_note: str | None = None
    used_minimum_version: bool = False
    alternative_performed: str | None = None
    deferred_until: str | None = None
    expected_entity_version: int | None = None
    action_idempotency_key: str | None = None


class VoiceCommandRequest(BaseModel):
    user_id: str = "moshe"
    transcript: str
    target_date: str | None = None
    source_device: str = "web_mic"


class ConfirmVoiceCommandRequest(BaseModel):
    user_id: str = "moshe"
    selected_instance_id: str | None = None
    learn_phrase_on_confirm: bool = False


class RegisterMediaAssetRequest(BaseModel):
    user_id: str = "moshe"
    title: str = ""
    media_type: str = "infographic"
    mime_type: str = "image/png"
    file_path_or_url: str
    size_bytes: int = 4096
    duration_seconds: int | None = None
    alt_text_or_transcript: str | None = None
    language: str = "he"
    offline_cached: bool = True
    ttl_days: int = 30


class CreateScheduledMessageRequest(BaseModel):
    user_id: str = "moshe"
    name: str
    text_content: str | None = None
    media_id: str | None = None
    media_blocks: list[dict[str, Any]] = Field(default_factory=list)
    start_date: str | None = None
    schedule_times: list[str] = Field(default_factory=lambda: ["08:00"])
    recurrence: str = "daily"
    display_mode: str = "tts"
    require_response: bool = False
    auto_tts_allowed: bool = False
    tts_speed: float = 1.0
    tts_voice: str = "he-IL-Standard"
    importance: int = 6


class UpdateContextModeRequest(BaseModel):
    user_id: str = "moshe"
    active_mode: str | None = None
    global_mute_tts: bool | None = None
    quiet_hours_start: str | None = None
    quiet_hours_end: str | None = None
    max_concurrent_prompts: int | None = None
    server_sleep_start: str | None = None
    server_sleep_end: str | None = None


class CaptureInboxItemRequest(BaseModel):
    user_id: str = "moshe"
    raw_text: str
    item_kind: str = "idea"
    source: str = "quick_inbox"


class AnswerOnboardingQuestionRequest(BaseModel):
    user_id: str = "moshe"
    action: str = "answer"
    answer_text: str | None = None
    fact_or_inference: str = "explicit_fact"
    mute_topic: bool = False


class SyncSelfManageMorningRequest(BaseModel):
    user_id: str = "moshe"
    target_date: str | None = None
    manual_exercises: list[dict[str, Any]] | None = None
    mark_11am_inquiry_resolved: bool = True


class SetMorningIntentRequest(BaseModel):
    user_id: str = "moshe"
    meaningful_win_text: str
    expected_blocker_text: str | None = None
    linked_goal_slug: str = "mental"
    create_as_today_activity: bool = True
    target_date: str | None = None


class LogEnergy4DRequest(BaseModel):
    user_id: str = "moshe"
    physical_energy: int = Field(default=3, ge=1, le=5)
    focus_clarity: int = Field(default=3, ge=1, le=5)
    motivation_drive: int = Field(default=3, ge=1, le=5)
    emotional_load: int = Field(default=2, ge=1, le=5)
    helpful_system_day: bool | None = None
    source: str = "self_report"
    notes: str | None = None


class DecideRecommendationRequest(BaseModel):
    user_id: str = "moshe"
    decision: str = "approved"


class SyncOfflineQueueRequest(BaseModel):
    user_id: str = "moshe"
    queued_actions: list[dict[str, Any]] = Field(default_factory=list)


class LogAttentionSelfReportRequest(BaseModel):
    user_id: str = "moshe"
    category: str = Field(default="worked", description="worked | browsed | break")
    context_note: str | None = None


class ToggleAttentionPauseRequest(BaseModel):
    user_id: str = "moshe"
    paused: bool = True


class SchedulerTickRequest(BaseModel):
    user_id: str = "moshe"
    target_date: str | None = None
    current_time: str = "18:00"
    auto_backup: bool = False


@router.get("/today-screen", operation_id="getV6TodayScreen")
def get_today_screen(user_id: str = "moshe", target_date: str | None = None, current_time: str = "09:30") -> dict[str, Any]:
    return UnifiedV6Service().get_today_screen(user_id=user_id, target_date=target_date, current_time=current_time)


@router.post("/activities", operation_id="createV6ActivityTemplate")
def create_activity_template(request: CreateV6ActivityTemplateRequest) -> dict[str, Any]:
    try:
        return UnifiedV6Service().create_activity_template(request.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/instances/{instance_id}/report", operation_id="reportV6InstanceExecution")
def report_instance_execution(instance_id: str, request: ReportV6InstanceExecutionRequest) -> dict[str, Any]:
    return UnifiedV6Service().report_instance_execution(
        instance_id,
        user_id=request.user_id,
        outcome=request.outcome,
        source=request.source,
        reported_execution_at=request.reported_execution_at,
        partial_value=request.partial_value,
        partial_unit=request.partial_unit,
        partial_target=request.partial_target,
        partial_note=request.partial_note,
        used_minimum_version=request.used_minimum_version,
        alternative_performed=request.alternative_performed,
        deferred_until=request.deferred_until,
        expected_entity_version=request.expected_entity_version,
        action_idempotency_key=request.action_idempotency_key,
    )


@router.post("/instances/{instance_id}/undo", operation_id="undoV6InstanceExecution")
def undo_instance_execution(instance_id: str, user_id: str = "moshe") -> dict[str, Any]:
    return UnifiedV6Service().undo_last_instance_report(instance_id, user_id=user_id)


@router.get("/instances/{instance_id}/stuck", operation_id="getV6StuckAssistance")
def get_stuck_assistance(instance_id: str, user_id: str = "moshe") -> dict[str, Any]:
    return UnifiedV6Service().get_stuck_assistance(instance_id, user_id=user_id)


@router.post("/instances/{instance_id}/check-rule", operation_id="evaluateV6InstanceRuleAtCheckTime")
def evaluate_instance_rule_at_check_time(instance_id: str, user_id: str = "moshe", check_time: str = "18:00") -> dict[str, Any]:
    return UnifiedV6Service().evaluate_daily_activity_rule_at_check_time(instance_id, user_id=user_id, check_time=check_time)


@router.post("/voice/command", operation_id="interpretV6VoiceCommand")
def interpret_voice_command(request: VoiceCommandRequest) -> dict[str, Any]:
    return UnifiedV6Service().interpret_voice_task_command(
        user_id=request.user_id,
        transcript=request.transcript,
        target_date=request.target_date,
        source_device=request.source_device,
    )


@router.post("/voice/confirm/{command_id}", operation_id="confirmV6VoiceCommand")
def confirm_voice_command(command_id: str, request: ConfirmVoiceCommandRequest) -> dict[str, Any]:
    return UnifiedV6Service().confirm_voice_task_command(
        command_id,
        user_id=request.user_id,
        selected_instance_id=request.selected_instance_id,
        learn_phrase_on_confirm=request.learn_phrase_on_confirm,
    )


@router.post("/media", operation_id="registerV6MediaAsset")
def register_media_asset(request: RegisterMediaAssetRequest) -> dict[str, Any]:
    try:
        return UnifiedV6Service().register_media_asset(request.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/media", operation_id="listV6MediaAssets")
def list_media_assets(user_id: str = "moshe") -> dict[str, Any]:
    items = UnifiedV6Service().list_media_assets(user_id=user_id)
    return {"success": True, "count": len(items), "media_assets": items}


@router.post("/scheduled-messages", operation_id="createV6ScheduledMessage")
def create_scheduled_message(request: CreateScheduledMessageRequest) -> dict[str, Any]:
    try:
        return UnifiedV6Service().create_scheduled_message(request.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/scheduled-messages", operation_id="listV6ScheduledMessages")
def list_scheduled_messages(user_id: str = "moshe") -> dict[str, Any]:
    items = UnifiedV6Service().list_scheduled_messages(user_id=user_id)
    return {"success": True, "count": len(items), "scheduled_messages": items}


@router.post("/scheduled-messages/{message_id}/preview", operation_id="previewV6ScheduledMessage")
def preview_scheduled_message(message_id: str, user_id: str = "moshe") -> dict[str, Any]:
    return UnifiedV6Service().preview_or_trigger_scheduled_message(message_id, user_id=user_id)


@router.get("/context-mode", operation_id="getV6ContextMode")
def get_context_mode(user_id: str = "moshe") -> dict[str, Any]:
    return {"success": True, "context_mode": UnifiedV6Service().get_context_mode(user_id=user_id)}


@router.patch("/context-mode", operation_id="updateV6ContextMode")
def update_context_mode(request: UpdateContextModeRequest) -> dict[str, Any]:
    patch = request.model_dump(exclude_none=True, exclude={"user_id"})
    return {"success": True, "context_mode": UnifiedV6Service().update_context_mode(request.user_id, patch)}


@router.post("/catch-up", operation_id="runV6PostSleepCatchup")
def run_post_sleep_catchup(user_id: str = "moshe", target_date: str | None = None, wake_time: str = "06:15") -> dict[str, Any]:
    return UnifiedV6Service().run_post_sleep_catchup(user_id=user_id, target_date=target_date, wake_time=wake_time)


@router.post("/inbox", operation_id="captureV6InboxItem")
def capture_inbox_item(request: CaptureInboxItemRequest) -> dict[str, Any]:
    return UnifiedV6Service().capture_inbox_item(request.model_dump())


@router.get("/inbox", operation_id="listV6InboxItems")
def list_inbox_items(user_id: str = "moshe") -> dict[str, Any]:
    items = UnifiedV6Service().list_inbox_items(user_id=user_id)
    return {"success": True, "count": len(items), "items": items}


@router.get("/onboarding", operation_id="getV6OnboardingState")
def get_onboarding_state(user_id: str = "moshe") -> dict[str, Any]:
    return UnifiedV6Service().get_next_onboarding_question(user_id=user_id)


@router.post("/onboarding/{question_id}", operation_id="answerV6OnboardingQuestion")
def answer_onboarding_question(question_id: str, request: AnswerOnboardingQuestionRequest) -> dict[str, Any]:
    return UnifiedV6Service().answer_or_skip_onboarding_question(
        question_id,
        user_id=request.user_id,
        action=request.action,
        answer_text=request.answer_text,
        fact_or_inference=request.fact_or_inference,
        mute_topic=request.mute_topic,
    )


@router.post("/self-manage/sync-morning", operation_id="syncV6SelfManageMorningExercises")
def sync_self_manage_morning(request: SyncSelfManageMorningRequest) -> dict[str, Any]:
    return UnifiedV6Service().sync_self_manage_morning_exercises(
        user_id=request.user_id,
        target_date=request.target_date,
        manual_exercises=request.manual_exercises,
        mark_11am_inquiry_resolved=request.mark_11am_inquiry_resolved,
    )


@router.get("/morning-intent", operation_id="getV6MorningIntent")
def get_morning_intent(user_id: str = "moshe", target_date: str | None = None) -> dict[str, Any]:
    return UnifiedV6Service().get_morning_intent(user_id=user_id, target_date=target_date)


@router.post("/morning-intent", operation_id="setV6MorningIntent")
def set_morning_intent(request: SetMorningIntentRequest) -> dict[str, Any]:
    return UnifiedV6Service().set_morning_intent(
        user_id=request.user_id,
        meaningful_win_text=request.meaningful_win_text,
        expected_blocker_text=request.expected_blocker_text,
        linked_goal_slug=request.linked_goal_slug,
        create_as_today_activity=request.create_as_today_activity,
        target_date=request.target_date,
    )


@router.get("/energy-4d", operation_id="getV6Energy4DSummary")
def get_energy_4d(user_id: str = "moshe") -> dict[str, Any]:
    return UnifiedV6Service().get_energy_4d_summary(user_id=user_id)


@router.post("/energy-4d", operation_id="logV6Energy4D")
def log_energy_4d(request: LogEnergy4DRequest) -> dict[str, Any]:
    return UnifiedV6Service().log_energy_4d(
        user_id=request.user_id,
        physical_energy=request.physical_energy,
        focus_clarity=request.focus_clarity,
        motivation_drive=request.motivation_drive,
        emotional_load=request.emotional_load,
        helpful_system_day=request.helpful_system_day,
        source=request.source,
        notes=request.notes,
    )


@router.get("/learning/recommendations", operation_id="getV6AntiDriftAndRecommendations")
def get_anti_drift_and_recommendations(user_id: str = "moshe") -> dict[str, Any]:
    return UnifiedV6Service().analyze_anti_drift_and_recommendations(user_id=user_id)


@router.post("/learning/recommendations/{recommendation_id}/decide", operation_id="decideV6Recommendation")
def decide_recommendation(recommendation_id: str, request: DecideRecommendationRequest) -> dict[str, Any]:
    return UnifiedV6Service().decide_recommendation(
        recommendation_id,
        user_id=request.user_id,
        decision=request.decision,
    )


@router.post("/offline/sync", operation_id="syncV6OfflineQueue")
def sync_offline_queue(request: SyncOfflineQueueRequest) -> dict[str, Any]:
    return UnifiedV6Service().sync_offline_action_queue(
        user_id=request.user_id,
        queued_actions=request.queued_actions,
    )


@router.post("/backup/create", operation_id="createV6VerifiedDbBackup")
def create_verified_db_backup(user_id: str = "moshe") -> dict[str, Any]:
    return UnifiedV6Service().create_verified_db_backup(user_id=user_id)


@router.get("/attention", operation_id="getV6AttentionState")
def get_attention_state(user_id: str = "moshe") -> dict[str, Any]:
    return UnifiedV6Service().get_attention_state(user_id=user_id)


@router.post("/attention/report", operation_id="logV6AttentionSelfReport")
def log_attention_self_report(request: LogAttentionSelfReportRequest) -> dict[str, Any]:
    try:
        return UnifiedV6Service().log_attention_self_report(
            user_id=request.user_id,
            category=request.category,
            context_note=request.context_note,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/attention/pause", operation_id="toggleV6AttentionPause")
def toggle_attention_pause(request: ToggleAttentionPauseRequest) -> dict[str, Any]:
    return UnifiedV6Service().toggle_attention_pause(user_id=request.user_id, paused=request.paused)


@router.post("/scheduler/tick", operation_id="runV6ServerSchedulerTick")
def run_server_scheduler_tick(request: SchedulerTickRequest) -> dict[str, Any]:
    return UnifiedV6Service().run_server_scheduler_tick(
        user_id=request.user_id,
        target_date=request.target_date,
        current_time=request.current_time,
        auto_backup=request.auto_backup,
    )


@router.post("/bootstrap/day-one", operation_id="bootstrapV6PersonalDayOne")
def bootstrap_personal_day_one(user_id: str = "moshe", target_date: str | None = None) -> dict[str, Any]:
    return UnifiedV6Service().bootstrap_personal_day_one(user_id=user_id, target_date=target_date)


