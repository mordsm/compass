# Mental Skills Playground - Architecture

## Context

Compass is already the central FastAPI gateway for a Custom GPT. This feature should fit
that pattern: GPT Actions call Compass, and Compass owns persistence, routing,
deterministic decisions, and auditability.

## High-Level Architecture

```text
Custom GPT
  -> Compass Action API
      -> Identity/session layer
      -> Training engine
      -> Skill catalog
      -> Memory repository
      -> Safety guardrails
      -> Recommendation rules
      -> Audit/events
```

## Responsibilities

### Custom GPT

- Coach conversation.
- Generate scenario wording.
- Ask reflection questions.
- Teach one micro-skill.
- Personalize tone from backend context.
- Call Actions to load and save state.

### Compass Backend

- Authenticate Action requests.
- Resolve user identity.
- Store raw events, summaries, skill history, and user model data.
- Enforce user isolation.
- Validate session state transitions.
- Run deterministic recommendation and difficulty rules.
- Mark limits and safety states.
- Return compact context for the GPT.

### Training Engine

- Select recommended skill.
- Select exercise family and difficulty.
- Decide whether to progress, repeat, or reduce difficulty.
- Compute training indicators from stored evidence.
- Avoid psychological conclusions.

### Safety Layer

- Validate challenge intensity.
- Block prohibited scenario content.
- Respect `user_stop` immediately.
- Require cooldown and post-challenge check where needed.

## Data Flow

```text
1. User starts conversation.
2. GPT calls GET /user/context after the first user message.
3. Compass returns compact current context and recommendation.
4. GPT starts a session through POST /sessions/start.
5. GPT records baseline, response, reflection, micro-skill, retest, and debrief events.
6. GPT completes session through POST /sessions/{id}/complete.
7. Compass updates session summary, skill history, and recommendation state.
```

## Custom GPT Limitations

`CUSTOM_GPT_LIMITATION`: The GPT should not be assumed to run code, hold reliable durable
memory, initiate random notifications, call an Action before the first user message, or
perform background work outside the chat turn.

Field Mode and notifications should be designed as future backend/app capabilities.

## Integration With Existing Compass

Use the existing Compass pattern:

- Small GPT-facing API.
- Bearer authentication.
- Explicit schemas and contracts.
- Idempotency for writes.
- Deterministic logic on structured inputs.

Do not route training progress through approval execution unless the action has external
side effects. Most training writes are normal persistence, not approval-gated actions.

## First MVP Boundary

The first implementation should add a dedicated training domain while keeping other
Compass modules unchanged. It should not modify existing finance, mail, assessment, task,
or administrative flows.
