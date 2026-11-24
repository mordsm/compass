# Mental Skills Playground - Test Plan

## Planning Validation

- Confirm docs use one consistent product model.
- Confirm no document treats the GPT as durable memory.
- Confirm Custom GPT limitations are explicitly marked.
- Confirm safety and product boundaries are reflected in API and MVP plan.

## Future Backend Tests

### Identity And Isolation

- Requests require or resolve `user_id`.
- History for one user is never returned for another user.
- Missing user identity returns a safe error.

### Session Flow

- Start session creates one pending session.
- Duplicate start with same `idempotency_key` returns existing session.
- Events append in order.
- Complete session updates status and summary.
- Completing twice is idempotent.

### Skill State

- Completing a session increments `sessions_count`.
- Stop or overload decreases or caps future difficulty.
- Successful low-difficulty sessions can increase readiness.

### Recommendation Engine

- New user gets one of the MVP skills.
- Skill not trained for 14 days gains priority.
- Recently overloaded skill is not escalated.
- Recommendation includes reason.

### Safety

- Prohibited challenge types are rejected.
- `user_stop` event changes session safety state.
- Cooldown can be recorded after stop.

### GPT Action Schema

- OpenAPI parses as YAML.
- Operation IDs are unique.
- All write operations include `idempotency_key`.
- Server URL can be configured for public HTTPS.

## Manual GPT Tests

1. Start a new GPT conversation and verify it loads context after the first user message.
2. Run a short `PAUSE` drill.
3. Ask to stop mid-drill and verify the GPT stops immediately.
4. Complete a session and verify the next recommendation uses saved context.
