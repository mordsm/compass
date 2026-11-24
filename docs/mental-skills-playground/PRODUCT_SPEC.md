# Mental Skills Playground - Product Spec

## Product Promise

Mental Skills Playground is a training environment for meta-emotional and meta-cognitive
skills. It treats skills like trainable capacities, not diagnoses or character flaws.

The product loop is:

```text
DISCOVER -> TRAIN -> RETEST -> TRANSFER -> LEARN
```

The GPT is the coach and conversational interface. Compass is the durable backend that
stores history, exposes Actions, and coordinates deterministic training decisions.

## Non-Goals

- Therapy or clinical diagnosis.
- Personality scoring.
- Generic wellbeing advice.
- Long lectures about emotions.
- Hidden reliance on ChatGPT Memory.
- Stressful challenges without explicit stop and cooldown paths.

## Users

MVP targets one known user. The design must still avoid assumptions that would make later
multi-user support unsafe.

Future users may be family members or separate individuals sharing the same GPT. Every
stored event must belong to an explicit `user_id`.

## Core Experience

A session should feel like a short training drill:

1. Load context.
2. Select one skill.
3. Run a brief baseline scenario.
4. Capture the real user response.
5. Reflect without judging.
6. Teach one micro-skill.
7. Retest with a comparable scenario.
8. Compare what changed.
9. Save the session.
10. Recommend the next step.

One session should teach one thing. The system should prefer a practiced micro-skill over
multiple explained concepts.

## Initial Skill Set

The complete initial taxonomy:

- `PAUSE`
- `FRUSTRATION_TOLERANCE`
- `AROUSAL_REGULATION`
- `STIMULUS_TOLERANCE`
- `COGNITIVE_FLEXIBILITY`
- `PERSON_ACTION_SEPARATION`
- `PERSPECTIVE_TAKING`
- `BALANCED_ATTENTION`
- `LOAD_AWARENESS`

MVP ships only:

- `PAUSE`
- `FRUSTRATION_TOLERANCE`
- `AROUSAL_REGULATION`

## Success Measures

Product success is not "the user is fixed." It is observable training continuity:

- Sessions are completed.
- Baseline and retest responses are captured.
- The user can name what changed.
- The backend accumulates evidence by skill.
- Recommendations use stored history rather than model guesses.
- The user can transfer a skill into a real-world observation.

## Product Tone

The coach should be curious, calm, lightly playful, and non-judgmental. It should say
"let us try a drill" rather than "your problem is."

## Key Risks

The product can fail by becoming therapy-shaped, lecture-heavy, too artificial, too
stressful, or too dependent on LLM memory. These risks are handled in `PREMORTEM.md` and
`SAFETY.md`.
