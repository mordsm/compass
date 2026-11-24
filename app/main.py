from __future__ import annotations

from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.database import init_db
from app.services.local_agent_launcher import ensure_drawmentor_running
from app.routers import (
    agents,
    approvals,
    assessment_ui,
    context,
    control_center,
    conversations,
    cycles,
    daily_plan,
    ecosystem,
    frogs,
    gpt,
    growth,
    health,
    mental_skills,
    progress,
    routines,
    rules,
    task_commander,
    tasks,
    training,
    unified_v6,
)


def create_app() -> FastAPI:
    app = FastAPI(
        title="Compass Gateway",
        version="0.1.0",
        description="Central GPT Actions gateway for life, family, and agent orchestration.",
    )

    @app.on_event("startup")
    def startup() -> None:
        init_db()
        ensure_drawmentor_running()

    app.include_router(health.router)
    app.include_router(gpt.router)
    app.include_router(context.router)
    app.include_router(conversations.router)
    app.include_router(daily_plan.router)
    app.include_router(cycles.router)
    app.include_router(tasks.router)
    app.include_router(task_commander.router)
    app.include_router(frogs.router)
    app.include_router(routines.router)
    app.include_router(growth.router)
    app.include_router(training.router)
    app.include_router(mental_skills.router)
    app.include_router(progress.router)
    app.include_router(rules.router)
    app.include_router(control_center.router)
    app.include_router(unified_v6.router)
    app.include_router(agents.router)
    app.include_router(approvals.router)
    app.include_router(ecosystem.router)
    app.include_router(assessment_ui.router)
    app.mount("/familybiz", StaticFiles(directory="app/static/familybiz", html=True), name="familybiz")
    app.mount("/ecosystem-hub", StaticFiles(directory="app/static/ecosystem-hub", html=True), name="ecosystem-hub")
    app.mount("/control-center", StaticFiles(directory="app/static/control-center", html=True), name="control-center")

    @app.get("/familybiz-app", include_in_schema=False)
    def familybiz_app() -> RedirectResponse:
        return RedirectResponse(url="/familybiz/")

    return app


app = create_app()
