# Mental Skills Playground - Memory Architecture

## Core Rule

Do not rely on ChatGPT Memory for product memory. Durable personal state belongs in
Compass and is loaded through Actions.

## Layers

### Layer 1: Raw Events

Every meaningful action in a session:

- session started
- baseline scenario shown
- user response captured
- reflection captured
- micro-skill taught
- retest response captured
- debrief captured
- stop requested
- cooldown completed

### Layer 2: Session Summaries

A compact summary of one training session:

- skill trained
- exercise used
- difficulty
- what happened
- before/after indicators
- safety events
- next recommendation hint

### Layer 3: Skill History

Aggregated history by user and skill:

- sessions count
- recent trend
- effective exercises
- ineffective exercises
- known triggers
- overload markers

### Layer 4: User Model

Cross-skill picture:

- current focus
- preferred coach style
- pacing preferences
- recent load pattern
- active constraints

### Layer 5: Current Context

Small Action response for the GPT:

- who the user is
- current recommended skill
- recent relevant history
- safety notes
- last session summary
- what not to repeat

## Retrieval Principle

Full history exists in the backend. Only task-relevant context enters the GPT context
window.

## Privacy And Isolation

Every record must include `user_id`. Later multi-user support must not infer identity from
free text alone.

## Retention

MVP can keep all data locally. Future versions should define retention, export, and delete
policies before broader use.
