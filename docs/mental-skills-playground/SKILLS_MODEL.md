# Mental Skills Playground - Skills Model

## Principle

Skills must be data-driven. Adding a new skill should usually require new data and
exercise definitions, not new router logic.

## Skill Definition

Recommended fields:

```yaml
skill_id: PAUSE
display_name: Pause
description: Create space between stimulus and response.
status: active
default_min_difficulty: 1
default_max_difficulty: 2
exercise_families:
  - impulse_delay
measurement_indicators:
  - response_latency_self_report
  - urge_intensity_before
  - urge_intensity_after
  - user_noticed_change
safety_notes:
  - keep friction mild
```

## Exercise Definition

Recommended fields:

```yaml
exercise_id: pause_waiting_mild_001
skill_id: PAUSE
mode: TRAINING_MODE
challenge_type: waiting
min_difficulty: 1
max_difficulty: 2
micro_skill: wait_three_seconds
baseline_prompt_template: string
retest_prompt_template: string
reflection_questions:
  - string
safety_tags:
  - low_intensity
```

## User Skill State

Each user has one state record per skill:

- `user_id`
- `skill_id`
- `current_training_level`
- `confidence`
- `sessions_count`
- `recent_performance`
- `trend`
- `last_trained_at`
- `preferred_exercises`
- `ineffective_exercises`
- `known_triggers`
- `effective_regulation_methods`

## Session Measurements

Measurements are training indicators only. MVP indicators can be simple:

- User completed the drill.
- User reported intensity before and after.
- User described first response.
- User identified one change.
- User stopped or overloaded.
- GPT observed whether required steps were completed.

## MVP Skills

### PAUSE

Trains the gap between urge and action.

MVP exercises:

- Wait before answering.
- Notice the first impulse.
- Rewrite a fast response into a delayed response.

### FRUSTRATION_TOLERANCE

Trains steadiness when something does not work quickly.

MVP exercises:

- Mild blocked-task scenario.
- Changed instruction scenario.
- Small failed attempt followed by reset.

### AROUSAL_REGULATION

Trains noticing body activation and using one regulation move.

MVP exercises:

- Body scan.
- Slow exhale.
- Notice-change comparison.

## Future Skill

`COGNITIVE_FLEXIBILITY` should be next after MVP. It requires capturing the user's first
interpretation before asking for alternatives.
