# Compass – Current Task Brief: Proactive Personal Development

Last updated: 2026-11-24  
Current Phase: **Phase 0 Completed (Architecture & Capability Mapping) – Waiting for User Approval to Start Phase 1**

---

## 1. Objective

Extend **Compass** and its connected specialist projects (`rules_engine`, `self_manage`, `personal_Assessment`, `TaskCommander`) into a proactive personal development, self-management, habit formation, frog-eating (anti-avoidance), adaptive challenge, and longitudinal mental-progress system.

**Core Principle:**
> The user defines the policy (Planner Role), the system manages daily execution (Executor Role), and the deterministic Rules Engine ensures execution stays strictly within the approved policy.

---

## 2. Connected Repositories

1. **Compass (`c:\workspace\compass`, port `8000`)** – Central coordinator, context manager, daily plan lifecycle, approval queue, mental event & silent-win store, AI usage tracker, and **System Control Center** UI (`/control-center/`).
2. **Rules Engine (`c:\workspace\rules_engine`, port `8003` & in-process `compass_rules.py`)** – Deterministic policy evaluation, rule catalog (`FROG-001`..`CONTROL-002`), conflict resolution logging, and rule version rollback.
3. **Self Manage (`c:\workspace\self_manage`, port `8001`)** – Physical, mental, and cognitive exercise library, routines with minimum viable versions (`HABIT-001`), 6-step pre-action preparation protocol, and safety/pain logging.
4. **Personal Assessment (`c:\workspace\personal_Assessment`, port `8002`)** – Objective test battery (`/battery`), weekly/monthly reviews, confidence scoring, and minimum-evidence guardrails (`ASSESS-001/002`).
5. **TaskCommander (`c:\workspace\hermes_backup\task_reminder` / `c:\workspace\TaskCommander`, port `8006`)** – Operational tasks, recurring task instances, reminders, and completion actions (`done`, `snooze`, `skip`).

---

## 3. Phased Development Plan

- **Phase 0 – Mapping & Gap Analysis (DONE):**
  - Inspected all local repositories and Git states.
  - Located the full `rules_engine` implementation (`compass_rules.py` + `rule_engine_agent.py`) and synced it to GitHub (`727995e`).
  - Documented full architecture, capability map, duplications, data ownership, and open decisions in `CURRENT_STATE.md`.
- **Phase 1 – Control Infrastructure & Rules Catalog (NEXT – Pending Approval):**
  - Versioned rules catalog (`FROG-001`..`CONTROL-002`) with enable/disable, conflict resolution logging, and rollback.
  - Decision explanation API (`explain`) grounded in actual rule evaluations and data.
  - Daily plan gate fix (`proposed -> evaluated -> pending_approval / active`).
  - Autonomy boundaries and initial **System Control Center** view.
- **Phase 2 – Eat That Frog Engine:**
  - Frog repository (one-time vs. ongoing), user-editable scoring (importance, resistance, difficulty, urgency), deterministic morning selection, non-judgmental status tracking, approval gate for ongoing frog removal (`FROG-004`), and evening 4-frog pool check (`FROG-001`).
- **Phase 3 – Routines, Preparation Protocol & Planner/Executor Separation:**
  - Routines with minimum viable version (`HABIT-001`), customizable 6-step pre-action preparation protocol with periodic tension sampling, explicit Planner vs. Executor mode switcher, and deterministic `next-action` guidance.
- **Phase 4 – Long-Term Goals, Adaptive Challenges & Playfulness:**
  - Core domains (Mental, Physical, Professional AI) vs. Enrichment domains (Cooking, Gardening, Music, Drawing), neglect & stagnation detection (`GROWTH-001/002`), adaptive challenges with safety caps (`CHALLENGE-001/002`), and non-punitive playfulness.
- **Phase 5 – Proactive Mental Training & Monthly Assessment:**
  - 4 training modes (baseline, pre-event prep, real-time intervention, post-event reflection), fast partial-friendly event logging (`NULL` for missing fields, never `0`), weekly **Silent Wins** check (`MENTAL-003`), strict mental-data privacy isolation, and monthly trend assessment with minimum-evidence enforcement (`ASSESS-001/002`).
- **Phase 6 – Full Daily/Weekly/Monthly Cycle, Voice/Telegram & E2E Acceptance:**
  - Morning/intraday/evening/weekly/monthly cycle orchestration, voice quick-capture, Telegram integration, complete System Control Center, LLM vs. STT/TTS cost tracking (`AI-001/002`), and all 22 automated acceptance tests.
