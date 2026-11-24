from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, ConfigDict

HealthStatus = Literal["green", "amber", "red", "unknown"]
NodeKind = Literal["project", "agent", "external"]
TaskPriority = Literal["low", "medium", "high", "urgent"]
TaskStatus = Literal["planned", "open", "in_progress", "blocked", "done", "archived"]
ProjectStatus = Literal["draft", "active", "paused", "archived"]


class EcosystemPatchOp(BaseModel):
    op: Literal["add", "replace", "remove"]
    path: str
    value: Any | None = None


class GraphNode(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: str
    label: str
    kind: NodeKind = "project"
    project_ref: str | None = None
    group: str | None = None
    icon: str | None = None
    status: str | None = None
    notes: str | None = None


class GraphEdge(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: str
    source: str
    target: str
    label: str
    payload_format: str
    protocol: str
    channel_type: str
    status: str
    last_success_at_utc: str | None = None
    notes: str | None = None


class MetaTask(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: str
    title: str
    priority: TaskPriority = "medium"
    status: str = "open"
    show_in_meta: bool = True
    owning_project_ref: str | None = None
    due_at_utc: str | None = None


class Graph(BaseModel):
    model_config = ConfigDict(extra="allow")

    nodes: list[GraphNode] = Field(default_factory=list)
    edges: list[GraphEdge] = Field(default_factory=list)


class MetaWindow(BaseModel):
    model_config = ConfigDict(extra="allow")

    health: HealthStatus = "unknown"
    open_alert_count: int = 0
    meta_tasks: list[MetaTask] = Field(default_factory=list)
    graph: Graph = Field(default_factory=Graph)


class ProjectTask(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: str
    title: str
    status: TaskStatus = "planned"
    priority: TaskPriority = "medium"
    show_in_meta: bool = False
    notes: str | None = None


class IdentityAndRole(BaseModel):
    model_config = ConfigDict(extra="allow")

    slug: str
    category: str
    purpose: str
    tags: list[str] = Field(default_factory=list)
    show_in_meta: bool = True


class InterfacesAndFlows(BaseModel):
    model_config = ConfigDict(extra="allow")

    inbound: list[str] = Field(default_factory=list)
    outbound: list[str] = Field(default_factory=list)
    channels: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class SchedulerSection(BaseModel):
    model_config = ConfigDict(extra="allow")

    enabled: bool = False
    cadence: str = "manual"
    timezone: str = "Asia/Jerusalem"
    next_run_utc: str | None = None
    retry_policy: str = "manual"


class RoadmapAndTasks(BaseModel):
    model_config = ConfigDict(extra="allow")

    tasks: list[ProjectTask] = Field(default_factory=list)
    milestones: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)


class ExportAndCommit(BaseModel):
    model_config = ConfigDict(extra="allow")

    export_targets: list[str] = Field(default_factory=list)
    commit_message: str = ""
    commit_policy: str = "manual"
    last_export_at_utc: str | None = None
    repo_path: str = ""


class ProjectWindow(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: str
    project_ref: str
    title: str
    summary: str
    kind: str = "agent"
    status: ProjectStatus = "draft"
    owner: str = "moshe"
    identity_and_role: IdentityAndRole
    interfaces_and_flows: InterfacesAndFlows = Field(default_factory=InterfacesAndFlows)
    scheduler: SchedulerSection = Field(default_factory=SchedulerSection)
    roadmap_and_tasks: RoadmapAndTasks = Field(default_factory=RoadmapAndTasks)
    export_and_commit: ExportAndCommit = Field(default_factory=ExportAndCommit)


class EcosystemState(BaseModel):
    model_config = ConfigDict(extra="allow")

    revision: int = 1
    meta_window: MetaWindow
    project_windows: list[ProjectWindow] = Field(default_factory=list)


class EcosystemStateEnvelope(BaseModel):
    success: bool = True
    state: EcosystemState


class EcosystemPatchRequest(BaseModel):
    base_revision: int
    patch_ops: list[EcosystemPatchOp]


class EcosystemPatchResponse(BaseModel):
    success: bool
    revision: int | None = None
    state: EcosystemState | None = None
    applied_patch_ops: list[EcosystemPatchOp] = Field(default_factory=list)
    export_file: str | None = None
    conflict: bool = False
    conflict_paths: list[str] = Field(default_factory=list)
    validation_errors: list[str] = Field(default_factory=list)
    message: str | None = None
