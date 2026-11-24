# Mental Skills Playground - Game Design

## Design North Star

The product should feel like a coherent training ground, not a library of tips. The user
enters a small world where each session is a drill and each drill trains one capacity.

## Game World

Working metaphor: a mental gym with training zones. Each skill is a training station, but
all stations belong to one map and one progression journey.

## Coach

The coach is stable across sessions:

- Curious.
- Non-judgmental.
- Pleasant.
- Capable of light humor.
- Direct when safety matters.
- Focused on practice, not lectures.

The coach should frame exercises as experiments: "Let us test this once" and "notice what
changed."

## Session Loop

```text
enter
identify user
load context
coach greeting
select skill
baseline challenge
capture response
reflect
teach one tool
retest
compare
short debrief
save session
update model
recommend next step
```

## Challenge Design

Challenges are small weights, not emotional traps. Valid challenge types include waiting,
uncertainty, mild disagreement, changed instructions, a small mistake, or partial
information.

Invalid challenge types include humiliation, threats, trauma, extreme scenarios, or strong
emotional manipulation.

## Difficulty

Difficulty is adaptive:

- Level 1: almost no friction.
- Level 2: mild friction.
- Level 3: moderate friction, only after successful lower-level sessions.
- Level 4+: future only, requiring clear safety criteria.

Difficulty should decrease after overload or stop events.

## Training Modes

`TRAINING_MODE` is available in the Custom GPT MVP.

`FIELD_MODE` is a future app/backend capability because Custom GPT cannot reliably initiate
notifications.

## Progress Feedback

Progress should be described as training evidence, not identity:

- Good: "In recent pause drills, you waited longer before responding."
- Bad: "You are patient now."

## Retention

To avoid novelty decay, use variations within a stable pattern:

- Different scenarios for the same skill.
- Short streaks by skill.
- Occasional retests of older skills.
- User-visible "next drill" recommendations.
