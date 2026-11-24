# Mental Skills Playground - Database Schema

## Scope

This is a planning schema, not a migration. It should guide the future Compass
implementation.

## Tables

### `msp_users`

- `user_id` text primary key
- `display_name` text
- `timezone` text
- `coach_style` text
- `identity_method` text
- `created_at` timestamp
- `updated_at` timestamp

### `msp_skills`

- `skill_id` text primary key
- `display_name` text
- `description` text
- `status` text
- `default_min_difficulty` integer
- `default_max_difficulty` integer
- `created_at` timestamp

### `msp_exercises`

- `exercise_id` text primary key
- `skill_id` text foreign key
- `mode` text
- `challenge_type` text
- `min_difficulty` integer
- `max_difficulty` integer
- `micro_skill` text
- `templates_json` json
- `safety_tags_json` json
- `status` text

### `msp_user_skill_state`

- `user_id` text
- `skill_id` text
- `current_training_level` integer
- `confidence` real
- `sessions_count` integer
- `recent_performance_json` json
- `trend` text
- `last_trained_at` timestamp
- `preferred_exercises_json` json
- `ineffective_exercises_json` json
- `known_triggers_json` json
- `effective_regulation_methods_json` json
- primary key: `user_id`, `skill_id`

### `msp_training_sessions`

- `session_id` text primary key
- `user_id` text
- `skill_id` text
- `exercise_id` text
- `mode` text
- `difficulty` integer
- `status` text
- `started_at` timestamp
- `completed_at` timestamp nullable
- `summary` text
- `safety_state` text
- `idempotency_key` text unique

### `msp_training_events`

- `event_id` text primary key
- `session_id` text
- `user_id` text
- `event_type` text
- `occurred_at` timestamp
- `payload_json` json
- `idempotency_key` text unique

### `msp_observations`

- `observation_id` text primary key
- `user_id` text
- `skill_id` text nullable
- `occurred_at` timestamp
- `source` text
- `content` text
- `tags_json` json
- `idempotency_key` text unique

### `msp_reflections`

- `reflection_id` text primary key
- `user_id` text
- `session_id` text nullable
- `skill_id` text nullable
- `created_at` timestamp
- `content` text
- `insight_tags_json` json
- `idempotency_key` text unique

### `msp_recommendations`

- `recommendation_id` text primary key
- `user_id` text
- `created_at` timestamp
- `recommended_skill_id` text
- `recommended_exercise_id` text nullable
- `difficulty` integer
- `reason` text
- `expires_at` timestamp nullable

## Idempotency

Every write endpoint should require `idempotency_key`, consistent with existing Compass
patterns.

## Multi-User Safety

Every user-owned table includes `user_id`. Queries must filter by `user_id`.
