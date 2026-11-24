# Mental Skills Playground - Actions API

## Design Rules

- Use a small GPT-facing API.
- Use bearer authentication.
- Require `idempotency_key` for writes.
- Keep responses compact and text-friendly.
- Return structured state for deterministic backend decisions.
- Mark Custom GPT limitations explicitly.

## Endpoints

### `GET /api/msp/user/context`

Returns compact current context for the GPT after the user's first message.

`CUSTOM_GPT_LIMITATION`: Do not assume this can run before the user's first message.

### `GET /api/msp/user/profile`

Returns the current user's profile and coach preferences.

### `GET /api/msp/skills`

Returns available skills and exercise families.

### `GET /api/msp/skills/{skill_id}/history`

Returns focused history for one skill.

### `GET /api/msp/training/recommendation`

Returns the deterministic next training recommendation.

### `POST /api/msp/sessions/start`

Starts a training session.

### `POST /api/msp/sessions/{session_id}/event`

Records a session event such as baseline response, reflection, retest response, stop, or
cooldown.

### `POST /api/msp/sessions/{session_id}/complete`

Completes the session, stores summary, and updates skill state.

### `POST /api/msp/observations`

Stores a real-world observation for Field Mode or transfer.

### `GET /api/msp/patterns`

Returns discovered training patterns with evidence notes.

### `POST /api/msp/reflection`

Stores a user reflection.

### `GET /api/msp/progress`

Returns skill progress as training indicators.

## Consequentiality

Most MVP endpoints write personal training memory but do not trigger external side
effects. In a Custom GPT schema, write endpoints should still be treated carefully and may
be marked consequential because they persist personal data.

## Limitations

- Actions require a reachable HTTPS backend for production use.
- Actions require a valid OpenAPI schema.
- A GPT can use apps or actions, but not both at the same time.
- Workspace domain restrictions may block custom action execution.
- Public GPTs with Actions require a privacy policy URL.
- Users may be prompted to approve actions before execution.
- Custom GPT should not be relied on for background notifications or durable memory.
