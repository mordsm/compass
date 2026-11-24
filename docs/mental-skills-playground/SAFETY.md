# Mental Skills Playground - Safety

## Safety Position

This is a training product, not therapy, diagnosis, or crisis care. It should avoid
clinical claims and avoid presenting scores as psychological truth.

## Prohibited Content

The system must not generate controlled challenges involving:

- Humiliation.
- Trauma reenactment.
- Threats.
- Extreme scenarios.
- Strong emotional manipulation.
- Provocation without boundaries.
- Shaming identity statements.
- Medical or psychiatric diagnosis.

## Required Guardrails

Every challenge should include:

- `challenge_intensity`
- `user_stop`
- `cool_down`
- `post_challenge_check`

## Stop Rule

If the user asks to stop, the exercise stops immediately. The GPT should acknowledge the
stop, avoid debating, and offer a short cooldown.

## Challenge Intensity

MVP should only use levels 1 and 2.

Level 3 may be designed but should not be active until there is evidence that the lower
levels are safe and useful.

## Overload Handling

If the user reports overload, distress increase, confusion, or discomfort:

1. Stop the challenge.
2. Run cooldown.
3. Save the safety event.
4. Lower future difficulty for that skill.
5. Avoid interpreting the event as failure.

## Clinical Boundary

The GPT should not diagnose, treat, or claim clinical improvement. It may suggest seeking
human professional support if the user describes serious distress, danger, or clinical
concerns.

## Evidence Boundary

Training indicators can support cautious language:

- "In this drill, you noticed the body signal faster."
- "Across the last few sessions, this exercise seems easier."

They must not support identity claims:

- "You are emotionally regulated."
- "You have a disorder."
- "Your score proves..."
