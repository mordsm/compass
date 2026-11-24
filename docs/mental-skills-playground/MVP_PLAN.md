# Mental Skills Playground - MVP Plan

## MVP Goal

Deliver a single-user Custom GPT plus Compass backend capability for three training
skills:

- `PAUSE`
- `FRUSTRATION_TOLERANCE`
- `AROUSAL_REGULATION`

## MVP Includes

- Skill catalog.
- Exercise catalog with 3-5 exercises per MVP skill.
- Session start/event/complete flow.
- Persistent training history.
- Personal muscle map.
- Session summaries.
- Basic deterministic recommendation engine.
- Custom GPT Actions schema.
- Paste-ready GPT instructions.
- Safety guardrails for controlled challenge.

## MVP Excludes

- Real notifications.
- Sensors, microphone, watch, or biometrics.
- Multi-user production authentication.
- Clinical interpretation.
- Approval execution workflows.
- High-intensity controlled stress.

## Implementation Phases

### Phase 1: Backend Contracts

Add schemas, routes, and repository methods for skills, sessions, events, observations,
reflections, progress, and recommendations.

### Phase 2: Deterministic Training Rules

Implement simple progression:

- New skills cap difficulty at level 2.
- Overload reduces next difficulty.
- Skills not trained for 14 days gain recommendation priority.
- Recent successful completion can allow gradual progression.

### Phase 3: GPT Actions

Create a small GPT-facing OpenAPI schema and update Custom GPT instructions.

### Phase 4: Validation

Add targeted tests for idempotency, user isolation, session flow, recommendation logic,
and safety stop behavior.

## First Vertical Slice

Start with `PAUSE` only:

1. Load user context.
2. Recommend `PAUSE`.
3. Start session.
4. Save baseline response.
5. Save micro-skill and retest response.
6. Complete session.
7. Update muscle map.
8. Return next recommendation.

Then add the other two MVP skills using the same contracts.
