# Compass

Compass is the central backend gateway for a Custom GPT that helps with daily planning,
tasks, decisions, personal context, and agent orchestration.

The GPT should connect only to Compass through GPT Actions. Compass then coordinates:

- `rules_engine` as the automation and approval backbone.
- `self_manage` for physical, mental, and cognitive management context.
- `personal_Assessment` for current-state assessment context.
- `mail_manager` for Gmail, financial mail, alerts, and email-derived financial items.
- `economic_spending` for spending events, summaries, and spending-risk signals.
- `TaskCommander` for operational tasks, reminders, recurrence, external task/calendar sync, and completion actions.
- `administrative_agent` for government, institutions, obligations, cases, documents, and prepared communications.
- Local Compass storage for tasks, plans, conversation events, and summaries.

## MVP Actions

- `GET /api/health`
- `POST /api/context/morning`
- `POST /api/conversation/event`
- `POST /api/conversation/finalize`
- `POST /api/daily-plan`
- `POST /api/tasks/upsert`
- `POST /api/rules/events`
- `POST /api/agents/invoke`
- `POST /api/approvals`
- `GET /api/approvals`
- `GET /api/approvals/{approval_id}`
- `POST /api/approvals/{approval_id}/approve`
- `POST /api/approvals/{approval_id}/reject`

Every write action accepts `idempotency_key` so GPT retries do not create duplicate records.

## Run Locally

```powershell
uv sync
Copy-Item .env.example .env
uv run uvicorn app.main:app --reload --port 8000
```

Local URL:

```text
http://localhost:8000
```

For a Custom GPT Action, expose this server through a public HTTPS tunnel, then update
`openapi.yaml`:

```yaml
servers:
  - url: https://your-public-domain.example
```

## Recommended Public Deploy

For Custom GPT Actions, prefer an always-on cloud URL over a laptop tunnel. The
server must be public HTTPS and should stay available when your computer sleeps,
restarts, or changes networks.

The included `Dockerfile` can run Compass on any container host:

```powershell
docker build -t compass .
docker run --rm -p 8000:8000 --env-file .env compass
```

For a hosted deployment, use the HTTPS URL assigned by the provider, for example:

```yaml
servers:
  - url: https://your-compass-app.example.com
```

Set these production environment variables in the host:

```text
COMPASS_ACTIONS_API_KEY=<strong secret token>
COMPASS_DATABASE_PATH=/data/compass.db
COMPASS_PUBLIC_BASE_URL=https://your-compass-app.example.com
COMPASS_USER_ID=moshe
```

If you keep SQLite, attach persistent storage at `/data`. Without persistent
storage, approvals, tasks, plans, and conversation history can disappear when the
container restarts.

## GitHub Deploy + Cloudflare Tunnel

Use this setup when you want GitHub to trigger deployments on your local PC and
Cloudflare to provide the public HTTPS URL.

Architecture:

```text
Custom GPT Action -> https://compass.example.com -> Cloudflare Tunnel -> Compass container
GitHub push -> self-hosted GitHub runner on local PC -> docker compose up -d --build
```

Your PC is the host. It must stay awake and connected for the GPT Action to work.
GitHub Actions is only the deployment trigger, not the web server.

1. In Cloudflare Zero Trust, create a remotely-managed tunnel.
2. Add a public hostname such as `compass.example.com`.
3. Point that hostname service to `http://compass:8000` if you run the included
   Docker Compose stack, or `http://127.0.0.1:8000` if `cloudflared` runs directly
   on the host.
4. Copy `deploy/env.example` to `.env` on the host and fill in:

```text
COMPASS_ACTIONS_API_KEY=<strong secret token>
COMPASS_PUBLIC_BASE_URL=https://compass.example.com
CLOUDFLARE_TUNNEL_TOKEN=<token from Cloudflare>
```

5. On the PC, run once:

```bash
docker compose -f deploy/docker-compose.cloudflare.yml up -d --build
```

6. In GitHub, add this repository as a self-hosted runner on your PC:

```text
Settings -> Actions -> Runners -> New self-hosted runner
```

Follow the Windows instructions GitHub shows. Leave the runner app running, or
install it as a service.

7. Push to `main`, or run the `Deploy Compass` workflow manually. The workflow
   runs on your PC and restarts the local Docker Compose stack.

After Cloudflare is healthy, set `openapi.yaml` to:

```yaml
servers:
  - url: https://compass.example.com
```

## Required Environment

```text
COMPASS_ACTIONS_API_KEY=change-me
COMPASS_DATABASE_PATH=data/compass.db
COMPASS_PUBLIC_BASE_URL=https://your-public-domain.example
COMPASS_USER_ID=moshe
COMPASS_SELF_MANAGE_BASE_URL=http://127.0.0.1:8001
COMPASS_ASSESSMENT_BASE_URL=http://127.0.0.1:8002
COMPASS_ASSESSMENT_PATH=../personal_Assessment
COMPASS_RULES_ENGINE_BASE_URL=http://127.0.0.1:8003
COMPASS_MAIL_MANAGER_BASE_URL=http://127.0.0.1:8004
COMPASS_ECONOMIC_SPENDING_BASE_URL=http://127.0.0.1:8005
COMPASS_ECONOMIC_SPENDING_PATH=../economic_spending
COMPASS_AUTOSTART_LOCAL_AGENTS=true
COMPASS_AUTOSTART_WAIT_SECONDS=12
```

## Local Agent Ports

```text
8000  Compass gateway, if you run it on the default uvicorn port
8001  self_manage
8002  personal_Assessment
8003  rules_engine service, using POST /evaluate
8004  mail_manager
8005  economic_spending
8006  TaskCommander
8007  administrative_agent
```

`rules_engine` uses `/evaluate` because the rule engine should decide/recommend first.
Compass should be the component that decides whether a recommended action is safe to execute.

## Dormant Local Agents

Compass can keep specialist local agents dormant until a GPT request actually needs
them. When `COMPASS_AUTOSTART_LOCAL_AGENTS=true`, Compass checks the configured
localhost port before calling `personal_Assessment` or `economic_spending`. If the
port is closed, Compass starts that project in the background, waits briefly, then
sends the original request.

This keeps the usual runtime lighter:

```text
Change Coach GPT -> Compass always on
Compass -> starts personal_Assessment only when assessment is requested
Compass -> starts economic_spending only when spending analysis is requested
```

The child process logs are written under `logs/*.autostart.log`.

## Approval Queue

Compass now has a first-class approval queue. Agents and rules can create proposed
actions, but approval only changes the request status. It does not execute side
effects yet.

Use this for:

- sending or drafting mail;
- spending-related actions;
- creating calendar events;
- changing family-sensitive data;
- any action marked high or critical risk.

Statuses:

```text
pending -> approved
pending -> rejected
approved -> executed, later
pending -> cancelled
```

## Open Questions

- Confirm whether `rules_engine` should run on port `8003`.
- Confirm whether `mail_manager` should run on port `8004`.
- Decide whether `economic_spending` should read from `mail_manager` directly or only receive spending facts from Compass.
- Decide which actions are only recommendations and which actions are allowed to execute after approval.
- Define per-agent execution contracts for approved requests.
- Decide whether TaskCommander should replace Compass local task storage as the durable task source.
- Decide which administrative domains to prioritize first: government, banks, health fund, schools, municipality, insurance, utilities.

## Agent-Style Services

Compass treats connected services as specialist agents when they expose a generic
`POST /api/agent/invoke` contract. The current agent-style services are:

- `personal_Assessment`: evaluates current-state evidence, signals, recommendations,
  confidence, and proposed measurement/review actions.
- `economic_spending`: evaluates spending events, signals, recommendations, and
  proposed review actions.

Agent Forge is not a Compass dependency. `personal_Assessment` has its own optional
Agent Forge export path for generated reviews.

## TaskCommander Role

TaskCommander should be the operational task engine:

- recurring tasks;
- today and overdue task instances;
- Google Calendar, Google Tasks, and Trello sync;
- reminders and Telegram alerts;
- completion actions such as done, snooze, and skip.

Compass should use TaskCommander for execution and reminders, while keeping its own
conversation-derived `mentioned/proposed/approved` task states until something becomes
operational.

## Administrative Agent Role

The administrative agent should track:

- obligations and deadlines;
- institution cases and reference numbers;
- document requirements;
- prepared emails, phone-call scripts, portal tasks, and appointment requests.

It should not submit forms, send mail, make payments, or log into portals unless Compass
has an approved request and a specific connector supports that action safely.
