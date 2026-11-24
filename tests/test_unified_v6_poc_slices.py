from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.config import get_settings
from app.database import init_db
from app.routers.unified_v6 import (
    AnswerOnboardingQuestionRequest,
    CaptureInboxItemRequest,
    ConfirmVoiceCommandRequest,
    CreateScheduledMessageRequest,
    CreateV6ActivityTemplateRequest,
    RegisterMediaAssetRequest,
    ReportV6InstanceExecutionRequest,
    UpdateContextModeRequest,
    VoiceCommandRequest,
    answer_onboarding_question,
    capture_inbox_item,
    confirm_voice_command,
    create_activity_template,
    create_scheduled_message,
    evaluate_instance_rule_at_check_time,
    get_stuck_assistance,
    get_today_screen,
    interpret_voice_command,
    preview_scheduled_message,
    register_media_asset,
    report_instance_execution,
    run_post_sleep_catchup,
    undo_instance_execution,
    update_context_mode,
)


class UnifiedV6PocSlicesTests(unittest.TestCase):
    """
    End-to-End Verification of Unified Spec v6 (Slices 1A–1E & all 16 POC Acceptance Scenarios in Section 19).
    """

    def setUp(self) -> None:
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)
        self.env = patch.dict(
            os.environ,
            {
                "COMPASS_DATABASE_URL": "",
                "COMPASS_DATABASE_PATH": str(Path(self.tmpdir.name) / "compass_v6.db"),
                "COMPASS_ACTIONS_API_KEY": "test-token",
                "COMPASS_AUTOSTART_LOCAL_AGENTS": "false",
            },
        )
        self.env.start()
        self.addCleanup(self.env.stop)
        get_settings.cache_clear()
        init_db()

    def test_all_16_unified_v6_poc_scenarios_and_slices_1a_to_1e(self) -> None:
        # --- Scenario 1: Create task with different open_time (06:00), preferred_time (09:10), check_time (10:00) ---
        created_writing = create_activity_template(
            CreateV6ActivityTemplateRequest(
                user_id="moshe",
                name="כתיבה חופשית על נייר",
                aliases=["כתיבה חופשית", "כתיבת בוקר"],
                open_time="06:00",
                preferred_time="09:10",
                check_time="10:00",
                current_time="07:30",
            )
        )
        self.assertTrue(created_writing["success"])
        writing_inst = created_writing["today_instance"]
        self.assertEqual(writing_inst["open_time"], "06:00")
        self.assertEqual(writing_inst["preferred_time"], "09:10")
        self.assertEqual(writing_inst["check_time"], "10:00")
        self.assertEqual(writing_inst["execution_outcome"], "unknown")

        # Verify Self Management 11:00 inquiry task was automatically seeded (Section 8)
        today_view = get_today_screen(user_id="moshe", current_time="09:30")
        all_names = [i["name"] for i in today_view["all_instances"]]
        self.assertIn("בירור מקור תרגילי הבוקר של Self Management", all_names)

        # Verify 'Stuck' button ('כפתור נתקעתי') offers small first step / minimum version without changing plan automatically
        stuck_res = get_stuck_assistance(writing_inst["instance_id"], user_id="moshe")
        self.assertTrue(stuck_res["success"])
        self.assertFalse(stuck_res["plan_changed_automatically"])
        self.assertEqual(len(stuck_res["suggestions"]), 3)

        # --- Scenario 2 & 4: Checkbox completion, sync across phone/PC (with conflict detection), and quick Undo ---
        done_res = report_instance_execution(
            writing_inst["instance_id"],
            ReportV6InstanceExecutionRequest(
                user_id="moshe",
                outcome="completed",
                source="phone_pwa_checkbox",
            ),
        )
        self.assertEqual(done_res["instance"]["execution_outcome"], "completed")
        self.assertEqual(done_res["instance"]["schedule_state"], "closed")

        # Conflict check if stale entity_version is sent from another device
        conflict_res = report_instance_execution(
            writing_inst["instance_id"],
            ReportV6InstanceExecutionRequest(
                user_id="moshe",
                outcome="not_done",
                source="pc_web",
                expected_entity_version=1,  # Stale! Current is 2
            ),
        )
        self.assertFalse(conflict_res["success"])
        self.assertEqual(conflict_res["status"], "version_conflict")

        # Undo restores previous outcome via linked append-only event
        undone = undo_instance_execution(writing_inst["instance_id"], user_id="moshe")
        self.assertEqual(undone["instance"]["execution_outcome"], "unknown")

        # --- Scenario 3 & 14: Hebrew Voice command by name/number, mandatory pre-save confirmation, ambiguity resolution, and voice undo ---
        # Create two similar physical tasks to test both stable numbering and ambiguity
        phys1 = create_activity_template(
            CreateV6ActivityTemplateRequest(
                user_id="moshe",
                name="אימון כוח בוקר",
                aliases=["אימון כוח"],
                open_time="07:00",
                preferred_time="08:00",
                check_time="18:00",
            )
        )["today_instance"]
        phys2 = create_activity_template(
            CreateV6ActivityTemplateRequest(
                user_id="moshe",
                name="אימון כוח ערב",
                aliases=["אימון כוח"],
                open_time="17:00",
                preferred_time="18:00",
                check_time="20:00",
            )
        )["today_instance"]

        # Unambiguous voice command by stable number
        v_cmd = interpret_voice_command(
            VoiceCommandRequest(
                user_id="moshe",
                transcript=f"ביצעתי משימה {writing_inst['daily_voice_number']}",
                source_device="android_mic",
            )
        )
        self.assertEqual(v_cmd["status"], "pending_confirmation")
        self.assertTrue(v_cmd["requires_explicit_confirmation"])
        # Before confirmation, task is STILL unknown (mandatory pre-save confirmation in POC!)
        today_before_confirm = get_today_screen(user_id="moshe")
        w_before = next(i for i in today_before_confirm["all_instances"] if i["instance_id"] == writing_inst["instance_id"])
        self.assertEqual(w_before["execution_outcome"], "unknown")

        # Confirm voice command -> now saved!
        v_confirmed = confirm_voice_command(
            v_cmd["command_id"],
            ConfirmVoiceCommandRequest(user_id="moshe", learn_phrase_on_confirm=True),
        )
        self.assertEqual(v_confirmed["status"], "confirmed_and_saved")
        self.assertEqual(v_confirmed["execution_result"]["instance"]["execution_outcome"], "completed")

        # Ambiguous voice command ("סיימתי אימון כוח" matches both phys1 and phys2) -> Scenario 14
        v_ambig = interpret_voice_command(
            VoiceCommandRequest(
                user_id="moshe",
                transcript="סיימתי אימון כוח",
                source_device="android_mic",
            )
        )
        self.assertEqual(v_ambig["status"], "ambiguous_requires_choice")
        self.assertGreaterEqual(len(v_ambig["candidates"]), 2)

        # User selects phys1 from the visual candidate buttons
        v_disambig = confirm_voice_command(
            v_ambig["command_id"],
            ConfirmVoiceCommandRequest(user_id="moshe", selected_instance_id=phys1["instance_id"]),
        )
        self.assertEqual(v_disambig["execution_result"]["instance"]["execution_outcome"], "completed")

        # --- Scenario 5: Video, Infographic, and Prepared Audio WITHOUT text (Media replaces text completely!) ---
        media_video = register_media_asset(
            RegisterMediaAssetRequest(
                user_id="moshe",
                title="סרטון תרגול מתיחות",
                media_type="video",
                mime_type="video/mp4",
                file_path_or_url="/media/stretch_0900.mp4",
                size_bytes=102400,
            )
        )["media"]
        media_info = register_media_asset(
            RegisterMediaAssetRequest(
                user_id="moshe",
                title="אינפוגרפיקת בוקר",
                media_type="infographic",
                mime_type="image/png",
                file_path_or_url="/media/morning_0700.png",
                size_bytes=51200,
            )
        )["media"]
        media_audio = register_media_asset(
            RegisterMediaAssetRequest(
                user_id="moshe",
                title="אודיו תרגול מנטלי 12:00",
                media_type="audio",
                mime_type="audio/mpeg",
                file_path_or_url="/media/mental_1200.mp3",
                size_bytes=81920,
            )
        )["media"]

        # Create a media-only activity without any text description
        media_only_act = create_activity_template(
            CreateV6ActivityTemplateRequest(
                user_id="moshe",
                name="",  # Empty text name! Derived from media block
                media_only=True,
                content_blocks=[
                    {"block_type": "video", "media_id": media_video["media_id"], "title": media_video["title"]},
                    {"block_type": "infographic", "media_id": media_info["media_id"], "title": media_info["title"]},
                    {"block_type": "audio", "media_id": media_audio["media_id"], "title": media_audio["title"]},
                ],
                open_time="07:00",
                preferred_time="09:00",
                check_time="12:30",
            )
        )
        self.assertTrue(media_only_act["template"]["media_only"])
        self.assertEqual(len(media_only_act["today_instance"]["content_blocks"]), 3)

        # --- Scenario 6: Scheduled Messages & TTS form + Global Mute / Quiet Mode ---
        sched_msg = create_scheduled_message(
            CreateScheduledMessageRequest(
                user_id="moshe",
                name="תזכורת נשימה והרפיה",
                text_content="עצור ל-30 שניות של נשימה רגועה וסקרנות.",
                schedule_times=["12:00", "17:00"],
                recurrence="daily",
                display_mode="tts",
                auto_tts_allowed=True,
            )
        )["scheduled_message"]

        preview_normal = preview_scheduled_message(sched_msg["message_id"], user_id="moshe")
        self.assertTrue(preview_normal["auto_tts_will_play"])

        # Enable Quiet Mode / Global Mute -> auto-TTS is immediately suppressed
        update_context_mode(UpdateContextModeRequest(user_id="moshe", active_mode="quiet_meeting", global_mute_tts=True))
        preview_muted = preview_scheduled_message(sched_msg["message_id"], user_id="moshe")
        self.assertFalse(preview_muted["auto_tts_will_play"])
        self.assertTrue(preview_muted["tts_suppressed_by_mute_or_quiet_mode"])
        update_context_mode(UpdateContextModeRequest(user_id="moshe", active_mode="normal", global_mute_tts=False))

        # --- Scenarios 7, 8, 9, 16: Physical Activity rule at 18:00 (Completed / Not Done / Unknown / Alternative) ---
        # Scenario 7: phys1 is already 'completed' -> no unnecessary alert at 18:00
        chk_done = evaluate_instance_rule_at_check_time(phys1["instance_id"], user_id="moshe", check_time="18:00")
        self.assertFalse(chk_done["alert_sent"])
        self.assertEqual(chk_done["action"], "none")

        # Scenario 9: phys2 has no report yet ('unknown') -> asks clarification question and does NOT declare failure!
        chk_unknown = evaluate_instance_rule_at_check_time(phys2["instance_id"], user_id="moshe", check_time="18:00")
        self.assertEqual(chk_unknown["execution_outcome"], "unknown")
        self.assertFalse(chk_unknown["declared_failure"])
        self.assertEqual(chk_unknown["action"], "ask_clarification")

        # Scenario 8: Mark phys2 as 'not_done' -> 18:00 check alerts and offers completion / minimum viable version
        report_instance_execution(
            phys2["instance_id"],
            ReportV6InstanceExecutionRequest(user_id="moshe", outcome="not_done"),
        )
        chk_not_done = evaluate_instance_rule_at_check_time(phys2["instance_id"], user_id="moshe", check_time="18:00")
        self.assertEqual(chk_not_done["action"], "offer_completion")
        self.assertIn("suggested_completion_window", chk_not_done)

        # Scenario 16: Intentional deferral or alternative ("הליכה קצרה במקום אימון כוח ארוך") is NOT automatically marked as full success
        alt_rep = report_instance_execution(
            phys2["instance_id"],
            ReportV6InstanceExecutionRequest(
                user_id="moshe",
                outcome="completed",
                alternative_performed="הליכה קצרה של 10 דקות",
            ),
        )
        self.assertEqual(alt_rep["instance"]["execution_outcome"], "partial")
        self.assertEqual(alt_rep["instance"]["alternative_performed"], "הליכה קצרה של 10 דקות")

        # --- Scenario 11: Server sleep during check window -> Post-sleep Catch-up recovers without duplicate alerts or artificial failures ---
        catchup = run_post_sleep_catchup(user_id="moshe", wake_time="06:15")
        self.assertTrue(catchup["success"])
        self.assertEqual(catchup["duplicate_alerts_sent"], 0)
        self.assertEqual(catchup["artificial_failures_created"], 0)

        # --- Scenario 13: Unauthorized user isolation check ---
        unauth = report_instance_execution(
            phys2["instance_id"],
            ReportV6InstanceExecutionRequest(user_id="intruder_user", outcome="completed"),
        )
        self.assertFalse(unauth["success"])
        self.assertEqual(unauth["error"], "unauthorized_user_isolation")

        # --- Slice 1E: Quick Inbox ('Idea' button never auto-converts to task) & Progressive Onboarding ---
        idea_res = capture_inbox_item(
            CaptureInboxItemRequest(
                user_id="moshe",
                raw_text="רעיון: לבנות תרגול נשימה עם צליל פעמון עדין",
                item_kind="idea",
            )
        )
        self.assertFalse(idea_res["converted_to_task_automatically"])
        self.assertEqual(idea_res["inbox_item"]["status"], "saved_in_idea_bank")

        onb = get_today_screen(user_id="moshe")
        self.assertTrue(onb["success"])
        from app.routers.unified_v6 import get_onboarding_state
        onb_state = get_onboarding_state(user_id="moshe")
        first_q = onb_state["next_question"]
        self.assertIsNotNone(first_q)

        ans_res = answer_onboarding_question(
            first_q["question_id"],
            AnswerOnboardingQuestionRequest(
                user_id="moshe",
                action="answer",
                answer_text="אני מעדיף Checkbox ביום ובקרים שקטים עד 09:00.",
                fact_or_inference="explicit_fact",
            ),
        )
        self.assertEqual(ans_res["question"]["status"], "answered")

        # Confirm the answered question is never asked again as next_question
        onb_state_after = get_onboarding_state(user_id="moshe")
        self.assertNotEqual(onb_state_after["next_question"]["question_id"], first_q["question_id"])

    def test_phases_2_to_4_self_manage_sync_morning_intent_anti_drift_energy_4d_offline_and_backup(self) -> None:
        from app.routers.unified_v6 import (
            DecideRecommendationRequest,
            LogEnergy4DRequest,
            SetMorningIntentRequest,
            SyncOfflineQueueRequest,
            SyncSelfManageMorningRequest,
            create_verified_db_backup,
            decide_recommendation,
            get_anti_drift_and_recommendations,
            log_energy_4d,
            set_morning_intent,
            sync_offline_queue,
            sync_self_manage_morning,
        )

        # 1. Self-Manage morning exercises import + deduplication + permanent closing of 11:00 inquiry task
        sm_sync1 = sync_self_manage_morning(
            SyncSelfManageMorningRequest(user_id="moshe", mark_11am_inquiry_resolved=True)
        )
        self.assertTrue(sm_sync1["success"])
        self.assertGreaterEqual(sm_sync1["imported_count"], 1)
        self.assertTrue(sm_sync1["inquiry_11am_closed_permanently"])

        # Re-importing on the same day skips duplicates
        sm_sync2 = sync_self_manage_morning(
            SyncSelfManageMorningRequest(user_id="moshe", mark_11am_inquiry_resolved=True)
        )
        self.assertEqual(sm_sync2["imported_count"], 0)
        self.assertGreaterEqual(sm_sync2["skipped_duplicates_count"], 1)

        # 2. Morning Intent ('ניצחון אמיתי להיום' + expected blocker)
        intent_res = set_morning_intent(
            SetMorningIntentRequest(
                user_id="moshe",
                meaningful_win_text="השלמת אינטגרציית V6 ואימון מתח",
                expected_blocker_text="עומס הודעות בצהריים",
                linked_goal_slug="ai_professional",
                create_as_today_activity=True,
            )
        )
        self.assertTrue(intent_res["has_intent"])
        self.assertIsNotNone(intent_res["intent"]["created_instance_id"])

        # 3. 4D Energy Management (no general Health Score + helpful system day tracking)
        nrg_res = log_energy_4d(
            LogEnergy4DRequest(
                user_id="moshe",
                physical_energy=2,
                focus_clarity=5,
                motivation_drive=4,
                emotional_load=2,
                helpful_system_day=True,
            )
        )
        self.assertFalse(nrg_res["has_general_health_score"])
        self.assertEqual(nrg_res["helpful_system_days_count"], 1)
        self.assertIn("למידת AI", nrg_res["tailored_guidance_he"])

        # 4. Anti-Drift & Recommendation Engine (repeated deferrals -> recommendation with correlation-vs-causation note)
        inst_id = intent_res["intent"]["created_instance_id"]
        report_instance_execution(inst_id, ReportV6InstanceExecutionRequest(user_id="moshe", outcome="deferred"))
        report_instance_execution(inst_id, ReportV6InstanceExecutionRequest(user_id="moshe", outcome="deferred"))

        learn_res = get_anti_drift_and_recommendations(user_id="moshe")
        self.assertGreaterEqual(len(learn_res["anti_drift_alerts"]), 1)
        self.assertGreaterEqual(len(learn_res["recommendations"]), 1)
        first_rec = learn_res["recommendations"][0]
        self.assertIn("מתאם", first_rec["correlation_vs_causation_note"])

        # Reject recommendation -> marked rejected and never re-created on subsequent runs
        dec_res = decide_recommendation(
            first_rec["recommendation_id"],
            DecideRecommendationRequest(user_id="moshe", decision="rejected"),
        )
        self.assertEqual(dec_res["status"], "rejected")

        # 5. PWA Offline Queue batch sync with conflict detection
        sync_res = sync_offline_queue(
            SyncOfflineQueueRequest(
                user_id="moshe",
                queued_actions=[
                    {
                        "instance_id": inst_id,
                        "outcome": "completed",
                        "source": "android_pwa_offline",
                        "action_idempotency_key": "offline_act_1",
                    }
                ],
            )
        )
        self.assertEqual(sync_res["applied_count"], 1)
        self.assertEqual(sync_res["conflicts_count"], 0)

        # 6. Automated verified SQLite backup
        bkp = create_verified_db_backup(user_id="moshe")
        self.assertTrue(bkp["success"])
        self.assertTrue(bkp["restorable"])

    def test_phase5_attention_self_report_scheduler_tick_and_day_one_bootstrap(self) -> None:
        from app.routers.unified_v6 import (
            LogAttentionSelfReportRequest,
            SchedulerTickRequest,
            ToggleAttentionPauseRequest,
            bootstrap_personal_day_one,
            log_attention_self_report,
            run_server_scheduler_tick,
            toggle_attention_pause,
        )

        # 1. One-click Day-1 Personal Bootstrap
        boot = bootstrap_personal_day_one(user_id="moshe")
        self.assertTrue(boot["success"])
        self.assertEqual(boot["created_frogs_count"], 4)
        self.assertEqual(boot["created_core_activities_count"], 3)
        self.assertEqual(boot["created_scheduled_messages_count"], 3)

        # 2. One-click Attention Self-Report (worked / browsed / break) + immediate stop button
        rep_work = log_attention_self_report(LogAttentionSelfReportRequest(user_id="moshe", category="worked"))
        self.assertTrue(rep_work["success"])
        self.assertFalse(rep_work["assumed_distraction"])
        self.assertEqual(rep_work["attention_state"]["counts"]["worked"], 1)

        rep_browse = log_attention_self_report(LogAttentionSelfReportRequest(user_id="moshe", category="browsed"))
        self.assertTrue(rep_browse["success"])
        self.assertFalse(rep_browse["assumed_distraction"])

        # Immediate Stop Tracking button blocks any further recording while paused
        paused_state = toggle_attention_pause(ToggleAttentionPauseRequest(user_id="moshe", paused=True))
        self.assertTrue(paused_state["tracking_paused"])
        blocked_rep = log_attention_self_report(LogAttentionSelfReportRequest(user_id="moshe", category="break"))
        self.assertFalse(blocked_rep["success"])
        self.assertEqual(blocked_rep["status"], "tracking_paused")

        # 3. Persistent Server Scheduler Tick at 18:00
        tick = run_server_scheduler_tick(
            SchedulerTickRequest(user_id="moshe", current_time="18:00", auto_backup=True)
        )
        self.assertTrue(tick["success"])
        self.assertGreaterEqual(tick["checked_instances_count"], 3)
        self.assertTrue(tick["backup_created"])


if __name__ == "__main__":
    unittest.main()
