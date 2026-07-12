from __future__ import annotations

from fastapi import FastAPI

from app.database import init_db
from app.routers import agents, approvals, context, conversations, daily_plan, health, rules, tasks


def create_app() -> FastAPI:
    app = FastAPI(
        title="Compass Gateway",
        version="0.1.0",
        description="Central GPT Actions gateway for life, family, and agent orchestration.",
    )

    @app.on_event("startup")
    def startup() -> None:
        init_db()

    app.include_router(health.router)
    app.include_router(context.router)
    app.include_router(conversations.router)
    app.include_router(daily_plan.router)
    app.include_router(tasks.router)
    app.include_router(rules.router)
    app.include_router(agents.router)
    app.include_router(approvals.router)
    return app


app = create_app()
