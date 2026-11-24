# Compass - Architectural Decisions

This file contains only decisions that future development sessions need to know.

Do not use this as a work log.

---

## D001 - Modular Architecture

Compass is divided into relatively independent modules.

Cross-module behavior should normally use explicit:

- APIs
- events
- schemas
- contracts

Avoid hidden direct coupling.

Status: Active

---

## D002 - Deterministic Rules Engine

`rules_engine` is deterministic.

LLM interpretation may happen before an event reaches the Rules Engine, but deterministic
rules should operate on structured input.

Example:

```text
unstructured input
-> interpretation/classification
-> structured event
-> deterministic rules_engine
-> action
```

Status: Active

---

## D003 - Assessment Output

`personal_Assessment` produces structured assessment results/events.

Downstream behavior should generally be routed explicitly rather than tightly embedded
inside the assessment module.

Status: Active

---

## D004 - Self Manage

`self_manage` consumes explicit recommendations/events where practical.

Assessment calculations should not be duplicated inside `self_manage`.

Status: Active

---

## D005 - Prefer Explicit Event Contracts

Important cross-module events should have explicit schemas.

Events should contain enough information for the receiving module to act without needing
to inspect the internals of the sender.

Status: Active

---

## D006 - Approval Is Separate From Execution

Compass approval requests record and decide whether a proposed action is allowed.
Approval alone must not execute downstream side effects.

Reason:

Approval is a safety and audit boundary. Execution can involve external systems, money,
mail, calendar changes, personal data, or local agents, so it needs an explicit per-agent
contract, idempotency behavior, audit logging, and clear failure handling.

Affected modules:

- `app/routers/approvals.py`
- `app/repository.py`
- `app/routers/rules.py`
- downstream agent adapters under `app/services/`
- future approved-action execution routes

Consequences:

- The approval queue may move a request from `pending` to `approved` or `rejected`, but it
  should not perform the proposed action by itself.
- Any future execution path must read an approved request, validate the expected action
  contract, call the target component explicitly, and record the result.
- Existing assessment workflows may execute `self_manage` only when the request explicitly
  includes `approval_confirmed=True`; this is a temporary bridge until a first-class
  approved-action executor exists.

Status: Active

---

## D007 - TaskCommander Integrated Natively Under Compass

Decision:

Develop and run `TaskCommander` (`tc_tasks` and `tc_task_instances`) directly inside
Compass (`app/services/task_commander.py` and `app/routers/task_commander.py`) using the
Compass database.

Reason:

Keeping operational tasks and recurring daily task instances inside Compass eliminates
a separate fragile process boundary on port `8006`, guarantees transactional consistency
between approved daily plans/frogs and operational task instances, and preserves the
separation between template tasks (`tc_tasks`) and daily occurrences (`tc_task_instances`).

Affected modules:

- `app/database.py`
- `app/services/task_commander.py`
- `app/routers/task_commander.py`
- `app/routers/control_center.py`

Consequences:

- `TaskCommanderAdapter` executes in-process against Compass storage by default.
- Recurring tasks generate daily instances without re-showing completed instances on the
  same day.

Status: Active

---

## D008 - Rule Engine First & Daily Plan Pre-Activation Gate

Decision:

1. All 20 Proactive Personal Development rules (`FROG-001`..`CONTROL-002`) run
   deterministically via `compass_rules.py` with version history, conflict resolution
   logging, and rollback support.
2. `POST /api/daily-plan` evaluates the proposed plan through `rules_engine` **before**
   activating it. Plans requiring approval are saved with `status="pending_approval"`.
   If `rules_engine` is unavailable, Compass fails closed with
   `status="rules_engine_unavailable"`.

Status: Active

---

# New Decision Template

## DXXX - Decision Name

Decision:

Reason:

Affected modules:

Consequences:

Status: Active
