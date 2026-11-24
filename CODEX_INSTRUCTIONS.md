```markdown
# Codex Instructions — Compass

## Primary Principle

Solve the requested task with the smallest reasonable repository scope,
context, tool usage, and code change.

Do not explore the whole Compass repository unless it is genuinely necessary.

---

## Compass Architecture

Compass is a modular system.

Major modules may include:

- personal_assessment
- self_manage
- rules_engine
- mail_manager
- finance
- dashboard
- calendar/tasks
- personal_history
- agents
- health/training

Treat modules as independent unless an explicit contract connects them.

Prefer cross-module communication through:

- structured events
- APIs
- schemas/contracts
- explicit service interfaces

Avoid hidden coupling.

---

## Rules Engine

The Rules Engine should remain deterministic.

Do not put open-ended LLM reasoning inside deterministic rule evaluation.

Prefer:

event -> deterministic rule -> explicit action/output

---

## Personal Assessment

personal_assessment should produce structured assessment results/events.

It should not directly contain downstream Self Manage behavior when that behavior
can instead be routed explicitly.

---

## Self Manage

self_manage should consume explicit assessment/rule outputs where practical.

Do not duplicate assessment logic inside self_manage.

---

# Context Efficiency

## Repository Exploration

Do NOT inspect the entire repository by default.

Start with:

1. TASK_BRIEF.md
2. CURRENT_STATE.md
3. relevant architecture/interface documentation
4. only the files directly related to the task

Prefer targeted searches for:

- function names
- class names
- endpoints
- event names
- schema names
- imports
- error messages

Do not recursively inspect unrelated directories.

---

## File Budget

Default discovery budget:

Inspect no more than approximately 5–6 implementation files before forming an
initial hypothesis.

If substantially more files are required, first explain briefly why.

This is not a hard safety limit:
if another file is clearly required to produce a correct solution, inspect it.

---

## Avoid Re-reading

Do not repeatedly reopen files already inspected unless:

- the file changed
- a specific missing detail is required
- verification requires it

---

# Scope Control

Do not:

- refactor unrelated code
- reorganize folders
- rename unrelated components
- upgrade dependencies
- change frameworks
- clean up unrelated code
- redesign architecture outside the task

unless explicitly requested.

If the requested task exposes a separate architectural problem,
report it separately instead of automatically expanding the task.

---

# Testing

Start with the smallest relevant validation.

Prefer:

1. targeted unit test
2. relevant module tests
3. integration test only when required
4. full repository test suite only when justified

Do not fix unrelated pre-existing test failures.

Report them separately.

---

# Work Sequence

For every substantial task:

## A. Scope

Briefly state:

- module involved
- likely files
- external dependency/interface if any
- what is explicitly out of scope
- intended validation

## B. Inspect

Read only the minimum necessary context.

## C. Implement

Make the smallest coherent change that solves the requested problem.

## D. Validate

Run targeted checks/tests.

## E. Stop

When the requested success criteria are satisfied, stop.

Do not automatically continue to optional improvements.

---

# Missing Context

If you cannot safely proceed because important information is missing:

Do not scan the whole repository looking for clues.

State exactly:

- what information is missing
- why it matters
- the smallest place likely to contain it

Then proceed only if the required context is reasonably available.

---

# State Handoff

At the end of a substantial completed task, update CURRENT_STATE.md.

Keep CURRENT_STATE.md concise.

Do not turn it into a transcript or activity log.

---

# Token / Context Discipline

Before opening another file, ask:

"Will this file materially affect the implementation decision?"

If not, do not open it.

Prefer precision of context over quantity of context.
```
