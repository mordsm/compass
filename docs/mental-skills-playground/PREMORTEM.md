# Mental Skills Playground - Premortem

## Failure Modes

| Failure mode | Probability | Impact | Early warning signal | Mitigation |
|---|---:|---:|---|---|
| User knows scenarios are artificial and does not respond naturally. | Medium | Medium | Responses become performative or detached. | Make drills short, ask for first impulse, and use real-life observations as transfer tasks. |
| Product becomes therapy in disguise. | Medium | High | Coach uses clinical framing or sessions become long emotional processing. | Keep language training-based, enforce non-goals, and keep one micro-skill per session. |
| GPT talks too much instead of training. | High | Medium | Long explanations before action. | Custom instructions require short prompts, one tool, and immediate practice. |
| Scores do not really measure capability. | High | High | User or GPT treats metrics as objective truth. | Label all metrics as training indicators and store evidence behind trends. |
| Controlled stress becomes annoying instead of useful. | Medium | High | Stop events, negative feedback, or session abandonment increase. | Cap MVP at levels 1-2, adapt downward after overload, and make stop easy. |
| System infers psychological conclusions from weak data. | Medium | High | Summaries say "you are" instead of "in this drill." | Add wording guardrails and evidence thresholds. |
| Memory grows until context is unmanageable. | High | Medium | GPT receives long history dumps. | Use layered memory and focused retrieval endpoints. |
| Data is mixed between family members. | Medium | Critical | Events have missing or ambiguous user IDs. | Require explicit `user_id`, use MVP passcode or fixed profile, and design future auth. |
| Product depends too much on the LLM. | High | High | Difficulty, progress, or safety decisions are free-form. | Move selection, scoring, progression, and safety checks into deterministic backend rules. |
| Custom GPT cannot support required behavior. | Medium | High | Need for notifications, background jobs, or pre-message action calls. | Mark as `CUSTOM_GPT_LIMITATION` and move to future app/backend plan. |
| Game is interesting for one week and then loses novelty. | Medium | Medium | Session frequency drops after early use. | Use varied scenarios, progression, transfer tasks, and visible next recommendations. |
| User learns to beat the exercise rather than transfer the skill. | Medium | Medium | User gives ideal answers but real-life observations do not change. | Add Field Mode observations and retests with varied comparable situations. |

## Highest-Risk Assumptions

1. The GPT can reliably keep the session loop tight.
2. The user will provide enough honest signal for training indicators.
3. Mild controlled challenge can be useful without feeling manipulative.
4. The MVP identity model will be safe enough for single-user use.

## Mitigation Priority

Start with safety and memory. A playful product with weak memory or unclear safety will
fail faster than a plain product with strong boundaries.
