const graphSvg = d3.select("#graphSvg");
const tooltip = document.getElementById("tooltip");
const drawer = document.getElementById("drawer");
const drawerTitle = document.getElementById("drawerTitle");
const drawerModeLabel = document.getElementById("drawerModeLabel");
const drawerBody = document.getElementById("drawerBody");
const patchPreview = document.getElementById("patchPreview");
const validationSummary = document.getElementById("validationSummary");
const saveResult = document.getElementById("saveResult");
const revisionLabel = document.getElementById("revisionLabel");
const baseRevisionLabel = document.getElementById("baseRevisionLabel");
const healthPill = document.getElementById("healthPill");
const alertCountStat = document.getElementById("alertCountStat");
const metaTaskStrip = document.getElementById("metaTaskStrip");
const refreshStateButton = document.getElementById("refreshStateButton");
const addProjectButton = document.getElementById("addProjectButton");
const closeDrawerButton = document.getElementById("closeDrawerButton");
const saveExportButton = document.getElementById("saveExportButton");
const sectionButtons = [...document.querySelectorAll(".tab-button")];

const sectionOrder = [
  "identity_and_role",
  "interfaces_and_flows",
  "scheduler",
  "roadmap_and_tasks",
  "export_and_commit",
];

const state = {
  server: null,
  draft: null,
  original: null,
  baseRevision: null,
  drawerMode: null,
  activeSection: "identity_and_role",
  selectedProjectRef: null,
  selectedEdgeId: null,
  simulation: null,
  width: 0,
  height: 0,
};

function clone(value) {
  return structuredClone(value);
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function uuid(prefix = "id") {
  if (crypto?.randomUUID) return `${prefix}_${crypto.randomUUID().slice(0, 8)}`;
  return `${prefix}_${Math.random().toString(16).slice(2, 10)}`;
}

function flattenMetaTasks(tasks = []) {
  return tasks
    .filter((task) => task.show_in_meta && ["urgent", "high"].includes(task.priority))
    .slice(0, 6);
}

function showDrawer() {
  drawer.classList.add("open");
  drawer.setAttribute("aria-hidden", "false");
}

function hideDrawer() {
  drawer.classList.remove("open");
  drawer.setAttribute("aria-hidden", "true");
}

function setSection(section) {
  state.activeSection = section;
  sectionButtons.forEach((button) => button.classList.toggle("active", button.dataset.section === section));
  drawerBody.querySelectorAll(".section-card").forEach((card) => {
    card.classList.toggle("active", card.dataset.section === section);
  });
}

function setSummary(text, type = "info") {
  validationSummary.textContent = text || "";
  validationSummary.dataset.type = type;
}

function setResult(text) {
  saveResult.textContent = text || "";
}

function findProjectIndexByRef(projectRef) {
  return state.server.state.project_windows.findIndex((project) => project.project_ref === projectRef);
}

function findNodeByProjectRef(projectRef) {
  return state.server.state.meta_window.graph.nodes.find((node) => node.project_ref === projectRef);
}

function findEdgeIndex(edgeId) {
  return state.server.state.meta_window.graph.edges.findIndex((edge) => edge.id === edgeId);
}

function defaultProjectWindow() {
  return {
    id: `project-${uuid("window")}`,
    project_ref: "",
    title: "",
    summary: "",
    kind: "agent",
    status: "draft",
    owner: "moshe",
    identity_and_role: {
      slug: "",
      category: "agent",
      purpose: "",
      tags: [],
      show_in_meta: true,
    },
    interfaces_and_flows: {
      inbound: [],
      outbound: [],
      channels: [],
      notes: [],
    },
    scheduler: {
      enabled: false,
      cadence: "manual",
      timezone: "Asia/Jerusalem",
      next_run_utc: null,
      retry_policy: "manual",
    },
    roadmap_and_tasks: {
      tasks: [],
      milestones: [],
      risks: [],
    },
    export_and_commit: {
      export_targets: ["json"],
      commit_message: "",
      commit_policy: "manual",
      last_export_at_utc: null,
      repo_path: "",
    },
  };
}

function defaultNodeForProject(project) {
  return {
    id: `node-${project.project_ref}`,
    label: project.title || project.project_ref,
    kind: project.kind === "hub" ? "project" : "project",
    project_ref: project.project_ref,
    group: project.identity_and_role?.category || "project",
    status: project.status,
    notes: project.summary,
  };
}

function ensureArray(values) {
  if (Array.isArray(values)) return values;
  if (typeof values === "string" && values.trim()) {
    return values.split(/\n|,/).map((part) => part.trim()).filter(Boolean);
  }
  return [];
}

function arrayToText(values) {
  return ensureArray(values).join("\n");
}

function normalizeProject(project) {
  const draft = clone(project);
  draft.identity_and_role ??= { slug: "", category: "agent", purpose: "", tags: [], show_in_meta: true };
  draft.interfaces_and_flows ??= { inbound: [], outbound: [], channels: [], notes: [] };
  draft.scheduler ??= { enabled: false, cadence: "manual", timezone: "Asia/Jerusalem", next_run_utc: null, retry_policy: "manual" };
  draft.roadmap_and_tasks ??= { tasks: [], milestones: [], risks: [] };
  draft.export_and_commit ??= { export_targets: ["json"], commit_message: "", commit_policy: "manual", last_export_at_utc: null, repo_path: "" };
  draft.roadmap_and_tasks.tasks = (draft.roadmap_and_tasks.tasks || []).map((task) => ({
    id: task.id || uuid("task"),
    title: task.title || "",
    status: task.status || "planned",
    priority: task.priority || "medium",
    show_in_meta: Boolean(task.show_in_meta),
    notes: task.notes || "",
  }));
  return draft;
}

function normalizeState(payload) {
  const next = clone(payload);
  next.meta_window ??= { health: "unknown", open_alert_count: 0, meta_tasks: [], graph: { nodes: [], edges: [] } };
  next.meta_window.graph ??= { nodes: [], edges: [] };
  next.meta_window.graph.nodes ??= [];
  next.meta_window.graph.edges ??= [];
  next.project_windows ??= [];
  next.project_windows = next.project_windows.map(normalizeProject);
  return next;
}

function replaceArrayValues(source) {
  return ensureArray(source).slice();
}

function updateField(path, value) {
  const parts = path.split(".");
  let cursor = state.draft;
  for (let index = 0; index < parts.length - 1; index += 1) {
    cursor = cursor[parts[index]];
  }
  cursor[parts[parts.length - 1]] = value;
  state.draft = clone(state.draft);
  updatePatchPreview();
}

function updateTopField(field, value) {
  state.draft[field] = value;
  state.draft = clone(state.draft);
  updatePatchPreview();
}

function addTaskRow() {
  state.draft.roadmap_and_tasks.tasks.push({
    id: uuid("task"),
    title: "",
    status: "planned",
    priority: "medium",
    show_in_meta: false,
    notes: "",
  });
  state.draft = clone(state.draft);
  renderDrawer();
  updatePatchPreview();
}

function removeTaskRow(index) {
  state.draft.roadmap_and_tasks.tasks.splice(index, 1);
  state.draft = clone(state.draft);
  renderDrawer();
  updatePatchPreview();
}

function openProjectDrawer(projectRef, mode = "project") {
  const index = findProjectIndexByRef(projectRef);
  if (index < 0 && mode !== "new") return;
  state.drawerMode = mode;
  state.selectedProjectRef = projectRef;
  state.selectedEdgeId = null;
  if (mode === "new") {
    state.original = null;
    state.baseRevision = state.server.state.revision;
    state.draft = normalizeProject(defaultProjectWindow());
    state.draft.project_ref = "";
    state.draft.title = "New Project/Agent";
    state.draft.identity_and_role.slug = "new_project";
    state.draft.identity_and_role.purpose = "Describe the new system or agent here.";
    state.draft.identity_and_role.tags = ["new"];
    state.draft.summary = "Fresh project window that will create both a project object and a graph node on save.";
    state.draft.roadmap_and_tasks.tasks = [
      { id: uuid("task"), title: "Define the first milestone", status: "planned", priority: "medium", show_in_meta: true, notes: "" },
    ];
    drawerModeLabel.textContent = "Add Project/Agent";
    drawerTitle.textContent = "Fast Project Form";
  } else {
    const original = state.server.state.project_windows[index];
    state.original = clone(original);
    state.baseRevision = state.server.state.revision;
    state.draft = normalizeProject(original);
    drawerModeLabel.textContent = "Edit Project";
    drawerTitle.textContent = original.title || original.project_ref;
  }
  revisionLabel.textContent = String(state.server.state.revision);
  baseRevisionLabel.textContent = String(state.baseRevision);
  renderDrawer();
  updatePatchPreview();
  showDrawer();
}

function openEdgeDrawer(edgeId) {
  const edgeIndex = findEdgeIndex(edgeId);
  if (edgeIndex < 0) return;
  state.drawerMode = "edge";
  state.selectedEdgeId = edgeId;
  state.selectedProjectRef = null;
  state.original = clone(state.server.state.meta_window.graph.edges[edgeIndex]);
  state.baseRevision = state.server.state.revision;
  state.draft = clone(state.original);
  drawerModeLabel.textContent = "Edit Edge";
  drawerTitle.textContent = state.draft.label;
  renderDrawer();
  updatePatchPreview();
  showDrawer();
}

function renderTaskInputs() {
  const tasks = state.draft.roadmap_and_tasks.tasks || [];
  return tasks
    .map(
      (task, index) => `
        <div class="task-row">
          <div class="field">
            <label>Title</label>
            <input data-task-field="title" data-task-index="${index}" value="${escapeHtml(task.title)}" placeholder="Task title" />
          </div>
          <div class="field">
            <label>Status</label>
            <select data-task-field="status" data-task-index="${index}">
              ${["planned", "open", "in_progress", "blocked", "done", "archived"].map((status) => `<option value="${status}" ${status === task.status ? "selected" : ""}>${status}</option>`).join("")}
            </select>
          </div>
          <div class="field">
            <label>Priority</label>
            <select data-task-field="priority" data-task-index="${index}">
              ${["low", "medium", "high", "urgent"].map((priority) => `<option value="${priority}" ${priority === task.priority ? "selected" : ""}>${priority}</option>`).join("")}
            </select>
          </div>
          <div class="show-meta">
            <label class="checkbox-row"><input data-task-field="show_in_meta" data-task-index="${index}" type="checkbox" ${task.show_in_meta ? "checked" : ""} /> show_in_meta</label>
            <button class="inline-button" data-action="remove-task" data-task-index="${index}">Remove</button>
          </div>
        </div>
      `,
    )
    .join("");
}

function renderDrawer() {
  if (!state.draft) return;
  const draft = state.draft;
  const identity = draft.identity_and_role;
  const flows = draft.interfaces_and_flows;
  const scheduler = draft.scheduler;
  const roadmap = draft.roadmap_and_tasks;
  const exportCommit = draft.export_and_commit;

  drawerBody.innerHTML = `
    <section class="section-card active" data-section="identity_and_role">
      <div class="form-grid">
        <div class="field">
          <label>Project title</label>
          <input data-field="title" value="${escapeHtml(draft.title || "")}" placeholder="Project title" />
        </div>
        <div class="field">
          <label>Project ref</label>
          <input data-field="project_ref" value="${escapeHtml(draft.project_ref || "")}" placeholder="unique ref, e.g. compass_hub" />
        </div>
        <div class="field">
          <label>Summary</label>
          <textarea data-field="summary" placeholder="Short summary">${escapeHtml(draft.summary || "")}</textarea>
        </div>
        <div class="field">
          <label>Kind</label>
          <select data-field="kind">
            ${["hub", "agent", "project", "external"].map((kind) => `<option value="${kind}" ${kind === draft.kind ? "selected" : ""}>${kind}</option>`).join("")}
          </select>
        </div>
        <div class="field">
          <label>Status</label>
          <select data-field="status">
            ${["draft", "active", "paused", "archived"].map((status) => `<option value="${status}" ${status === draft.status ? "selected" : ""}>${status}</option>`).join("")}
          </select>
        </div>
        <div class="field">
          <label>Owner</label>
          <input data-field="owner" value="${escapeHtml(draft.owner || "")}" placeholder="owner" />
        </div>
        <div class="field">
          <label>Slug</label>
          <input data-section-field="identity_and_role.slug" value="${escapeHtml(identity.slug || "")}" placeholder="slug" />
        </div>
        <div class="field">
          <label>Category</label>
          <input data-section-field="identity_and_role.category" value="${escapeHtml(identity.category || "")}" placeholder="category" />
        </div>
        <div class="field">
          <label>Purpose</label>
          <textarea data-section-field="identity_and_role.purpose" placeholder="What does this do?">${escapeHtml(identity.purpose || "")}</textarea>
        </div>
        <div class="field">
          <label>Tags, one per line</label>
          <textarea data-section-field="identity_and_role.tags">${escapeHtml(arrayToText(identity.tags || []))}</textarea>
        </div>
        <label class="checkbox-row"><input data-section-field="identity_and_role.show_in_meta" type="checkbox" ${identity.show_in_meta ? "checked" : ""} /> show_in_meta</label>
      </div>
    </section>

    <section class="section-card" data-section="interfaces_and_flows">
      <div class="form-grid">
        <div class="field">
          <label>Inbound</label>
          <textarea data-section-field="interfaces_and_flows.inbound">${escapeHtml(arrayToText(flows.inbound || []))}</textarea>
        </div>
        <div class="field">
          <label>Outbound</label>
          <textarea data-section-field="interfaces_and_flows.outbound">${escapeHtml(arrayToText(flows.outbound || []))}</textarea>
        </div>
        <div class="field">
          <label>Channels</label>
          <textarea data-section-field="interfaces_and_flows.channels">${escapeHtml(arrayToText(flows.channels || []))}</textarea>
        </div>
        <div class="field">
          <label>Notes</label>
          <textarea data-section-field="interfaces_and_flows.notes">${escapeHtml(arrayToText(flows.notes || []))}</textarea>
        </div>
      </div>
    </section>

    <section class="section-card" data-section="scheduler">
      <div class="form-grid">
        <label class="checkbox-row"><input data-section-field="scheduler.enabled" type="checkbox" ${scheduler.enabled ? "checked" : ""} /> enabled</label>
        <div class="field"><label>Cadence</label><input data-section-field="scheduler.cadence" value="${escapeHtml(scheduler.cadence || "")}" placeholder="manual / daily / hourly" /></div>
        <div class="field"><label>Timezone</label><input data-section-field="scheduler.timezone" value="${escapeHtml(scheduler.timezone || "")}" placeholder="Asia/Jerusalem" /></div>
        <div class="field"><label>Next run UTC</label><input data-section-field="scheduler.next_run_utc" value="${escapeHtml(scheduler.next_run_utc || "")}" placeholder="2026-08-21T06:00:00Z" /></div>
        <div class="field"><label>Retry policy</label><input data-section-field="scheduler.retry_policy" value="${escapeHtml(scheduler.retry_policy || "")}" placeholder="idempotent" /></div>
      </div>
    </section>

    <section class="section-card" data-section="roadmap_and_tasks">
      <div class="form-grid">
        <div>
          <div class="array-note">Inline task editing: title, status, priority, and show_in_meta.</div>
          <div class="task-list" id="taskList">${renderTaskInputs()}</div>
          <button id="addTaskButton" class="inline-button" type="button">Add Task</button>
        </div>
        <div class="field">
          <label>Milestones, one per line</label>
          <textarea data-section-field="roadmap_and_tasks.milestones">${escapeHtml(arrayToText(roadmap.milestones || []))}</textarea>
        </div>
        <div class="field">
          <label>Risks, one per line</label>
          <textarea data-section-field="roadmap_and_tasks.risks">${escapeHtml(arrayToText(roadmap.risks || []))}</textarea>
        </div>
      </div>
    </section>

    <section class="section-card" data-section="export_and_commit">
      <div class="form-grid">
        <div class="field">
          <label>Export targets</label>
          <textarea data-section-field="export_and_commit.export_targets">${escapeHtml(arrayToText(exportCommit.export_targets || []))}</textarea>
        </div>
        <div class="field">
          <label>Commit message</label>
          <input data-section-field="export_and_commit.commit_message" value="${escapeHtml(exportCommit.commit_message || "")}" />
        </div>
        <div class="field">
          <label>Commit policy</label>
          <input data-section-field="export_and_commit.commit_policy" value="${escapeHtml(exportCommit.commit_policy || "")}" />
        </div>
        <div class="field">
          <label>Last export at UTC</label>
          <input data-section-field="export_and_commit.last_export_at_utc" value="${escapeHtml(exportCommit.last_export_at_utc || "")}" />
        </div>
        <div class="field">
          <label>Repo path</label>
          <input data-section-field="export_and_commit.repo_path" value="${escapeHtml(exportCommit.repo_path || "")}" />
        </div>
      </div>
    </section>
  `;

  setSection(state.activeSection);
  wireDrawerInputs();
}

function wireDrawerInputs() {
  drawerBody.querySelectorAll("[data-field]").forEach((input) => {
    input.addEventListener("input", (event) => {
      const { field } = event.currentTarget.dataset;
      let value = event.currentTarget.value;
      if (field === "status" || field === "kind") {
        value = event.currentTarget.value;
      }
      updateTopField(field, value);
    });
  });

  drawerBody.querySelectorAll("[data-section-field]").forEach((input) => {
    input.addEventListener("input", (event) => {
      const path = event.currentTarget.dataset.sectionField;
      const raw = event.currentTarget.type === "checkbox" ? event.currentTarget.checked : event.currentTarget.value;
      const value = path.endsWith("tags") || path.endsWith("inbound") || path.endsWith("outbound") || path.endsWith("channels") || path.endsWith("notes") || path.endsWith("milestones") || path.endsWith("risks") || path.endsWith("export_targets")
        ? ensureArray(raw)
        : raw;
      updateField(path, value);
    });
    input.addEventListener("change", (event) => {
      const path = event.currentTarget.dataset.sectionField;
      if (event.currentTarget.type === "checkbox") {
        updateField(path, event.currentTarget.checked);
      }
    });
  });

  drawerBody.querySelectorAll("[data-task-field]").forEach((input) => {
    input.addEventListener("input", onTaskFieldChange);
    input.addEventListener("change", onTaskFieldChange);
  });

  drawerBody.querySelectorAll("[data-action=remove-task]").forEach((button) => {
    button.addEventListener("click", () => removeTaskRow(Number(button.dataset.taskIndex)));
  });

  const addTaskButton = document.getElementById("addTaskButton");
  if (addTaskButton) {
    addTaskButton.addEventListener("click", addTaskRow);
  }
}

function onTaskFieldChange(event) {
  const { taskField, taskIndex } = event.currentTarget.dataset;
  const index = Number(taskIndex);
  const task = state.draft.roadmap_and_tasks.tasks[index];
  if (!task) return;
  const value = event.currentTarget.type === "checkbox" ? event.currentTarget.checked : event.currentTarget.value;
  task[taskField] = value;
  state.draft = clone(state.draft);
  updatePatchPreview();
}

function stringifyPatch(patchOps) {
  return JSON.stringify(patchOps, null, 2);
}

function projectPatchOps() {
  const patchOps = [];
  if (!state.original) {
    patchOps.push({ op: "add", path: "/project_windows/-", value: clone(state.draft) });
    patchOps.push({ op: "add", path: "/meta_window/graph/nodes/-", value: defaultNodeForProject(state.draft) });
    return patchOps;
  }

  const index = findProjectIndexByRef(state.original.project_ref);
  if (index < 0) return patchOps;
  const original = state.original;
  const draft = state.draft;
  const replaceIfChanged = (path, a, b) => {
    if (JSON.stringify(a) !== JSON.stringify(b)) {
      patchOps.push({ op: "replace", path, value: clone(b) });
    }
  };
  replaceIfChanged(`/project_windows/${index}/title`, original.title, draft.title);
  replaceIfChanged(`/project_windows/${index}/project_ref`, original.project_ref, draft.project_ref);
  replaceIfChanged(`/project_windows/${index}/summary`, original.summary, draft.summary);
  replaceIfChanged(`/project_windows/${index}/kind`, original.kind, draft.kind);
  replaceIfChanged(`/project_windows/${index}/status`, original.status, draft.status);
  replaceIfChanged(`/project_windows/${index}/owner`, original.owner, draft.owner);
  replaceIfChanged(`/project_windows/${index}/identity_and_role`, original.identity_and_role, draft.identity_and_role);
  replaceIfChanged(`/project_windows/${index}/interfaces_and_flows`, original.interfaces_and_flows, draft.interfaces_and_flows);
  replaceIfChanged(`/project_windows/${index}/scheduler`, original.scheduler, draft.scheduler);
  replaceIfChanged(`/project_windows/${index}/roadmap_and_tasks`, original.roadmap_and_tasks, draft.roadmap_and_tasks);
  replaceIfChanged(`/project_windows/${index}/export_and_commit`, original.export_and_commit, draft.export_and_commit);

  const nodeIndex = state.server.state.meta_window.graph.nodes.findIndex((node) => node.project_ref === original.project_ref);
  const nextNode = {
    ...(nodeIndex >= 0 ? state.server.state.meta_window.graph.nodes[nodeIndex] : defaultNodeForProject(draft)),
    label: draft.title || draft.project_ref,
    project_ref: draft.project_ref,
    kind: draft.kind === "external" ? "external" : "project",
    group: draft.identity_and_role?.category || "project",
    status: draft.status,
    notes: draft.summary,
  };
  if (nodeIndex >= 0) {
    replaceIfChanged(`/meta_window/graph/nodes/${nodeIndex}`, state.server.state.meta_window.graph.nodes[nodeIndex], nextNode);
  } else {
    patchOps.push({ op: "add", path: "/meta_window/graph/nodes/-", value: nextNode });
  }
  return patchOps;
}

function edgePatchOps() {
  if (!state.original) return [];
  const edgeIndex = findEdgeIndex(state.original.id);
  if (edgeIndex < 0) return [];
  return [{ op: "replace", path: `/meta_window/graph/edges/${edgeIndex}`, value: clone(state.draft) }];
}

function validateDraft() {
  const errors = [];
  if (state.drawerMode === "edge") {
    if (!state.draft.label?.trim()) errors.push("Edge label is required.");
    if (!state.draft.source || !state.draft.target) errors.push("Edge source and target are required.");
    if (!state.draft.payload_format?.trim()) errors.push("payload_format is required.");
    return errors;
  }

  if (!state.draft.title?.trim()) errors.push("Project title is required.");
  if (!state.draft.project_ref?.trim()) errors.push("project_ref is required.");
  if (!state.draft.identity_and_role?.slug?.trim()) errors.push("identity_and_role.slug is required.");
  if (!state.draft.identity_and_role?.purpose?.trim()) errors.push("identity_and_role.purpose is required.");
  if (!state.draft.interfaces_and_flows) errors.push("interfaces_and_flows is required.");
  if (!state.draft.scheduler) errors.push("scheduler is required.");
  if (!state.draft.roadmap_and_tasks) errors.push("roadmap_and_tasks is required.");
  return errors;
}

function updatePatchPreview() {
  const patchOps = state.drawerMode === "edge" ? edgePatchOps() : projectPatchOps();
  patchPreview.textContent = stringifyPatch(patchOps);
  const errors = validateDraft();
  if (errors.length) {
    setSummary(errors.join(" "), "warn");
  } else {
    setSummary(`Ready to save ${patchOps.length} patch operation(s).`, "ok");
  }
}

function colorForNode(node) {
  if (node.kind === "external") return getComputedStyle(document.documentElement).getPropertyValue("--external").trim();
  if (node.group === "hub") return getComputedStyle(document.documentElement).getPropertyValue("--accent").trim();
  if (node.group === "finance") return "#fb7185";
  if (node.group === "wellbeing") return "#22c55e";
  if (node.group === "learning") return "#f59e0b";
  return getComputedStyle(document.documentElement).getPropertyValue("--agent").trim();
}

function renderMetaBanner() {
  const meta = state.server.state.meta_window;
  healthPill.textContent = `Health: ${meta.health}`;
  healthPill.dataset.health = meta.health;
  alertCountStat.textContent = `Open alerts: ${meta.open_alert_count}`;
  metaTaskStrip.innerHTML = flattenMetaTasks(meta.meta_tasks)
    .map((task) => `<button class="task-chip" data-project-ref="${escapeHtml(task.owning_project_ref || "")}"><strong>${escapeHtml(task.priority)}</strong> ${escapeHtml(task.title)}</button>`)
    .join("") || "<span class='muted'>No urgent tasks.</span>";
  metaTaskStrip.querySelectorAll(".task-chip").forEach((button) => {
    button.addEventListener("click", () => {
      const projectRef = button.dataset.projectRef;
      if (projectRef) openProjectDrawer(projectRef, "project");
    });
  });
  revisionLabel.textContent = String(state.server.state.revision);
}

function renderGraph() {
  const container = document.querySelector(".graph-shell");
  const rect = container.getBoundingClientRect();
  state.width = rect.width;
  state.height = rect.height;
  graphSvg.attr("viewBox", `0 0 ${state.width} ${state.height}`);
  graphSvg.selectAll("*").remove();

  const nodes = clone(state.server.state.meta_window.graph.nodes);
  const links = clone(state.server.state.meta_window.graph.edges);
  const linkById = new Map(links.map((link) => [link.id, link]));

  const link = graphSvg
    .append("g")
    .attr("class", "links")
    .selectAll("g")
    .data(links)
    .join("g");

  link.append("line")
    .attr("class", "edge-line")
    .attr("id", (d) => `edge-line-${d.id}`);

  link.append("line")
    .attr("class", "edge-hit")
    .on("mouseenter", (event, d) => showEdgeTooltip(event, d))
    .on("mousemove", (event, d) => showEdgeTooltip(event, d))
    .on("mouseleave", hideTooltip)
    .on("click", (event, d) => {
      event.stopPropagation();
      openEdgeDrawer(d.id);
    });

  link.append("text")
    .attr("class", "edge-label")
    .attr("pointer-events", "none")
    .text((d) => d.label);

  const node = graphSvg
    .append("g")
    .attr("class", "nodes")
    .selectAll("g")
    .data(nodes, (d) => d.id)
    .join("g")
    .attr("class", "node")
    .on("mouseenter", (event, d) => showNodeTooltip(event, d))
    .on("mousemove", (event, d) => showNodeTooltip(event, d))
    .on("mouseleave", hideTooltip)
    .on("click", (event, d) => {
      event.stopPropagation();
      if (d.project_ref) openProjectDrawer(d.project_ref, "project");
    })
    .call(
      d3.drag()
        .on("start", (event, d) => {
          if (!event.active) state.simulation.alphaTarget(0.3).restart();
          d.fx = d.x;
          d.fy = d.y;
        })
        .on("drag", (event, d) => {
          d.fx = event.x;
          d.fy = event.y;
        })
        .on("end", (event, d) => {
          if (!event.active) state.simulation.alphaTarget(0);
          d.fx = null;
          d.fy = null;
        }),
    );

  node.append("circle")
    .attr("r", (d) => (d.group === "hub" ? 22 : 17))
    .attr("fill", (d) => colorForNode(d));

  node.append("text")
    .attr("dy", 34)
    .text((d) => d.label);

  state.simulation = d3
    .forceSimulation(nodes)
    .force("link", d3.forceLink(links).id((d) => d.id).distance((d) => (d.label?.length > 10 ? 150 : 120)).strength(0.8))
    .force("charge", d3.forceManyBody().strength(-360))
    .force("center", d3.forceCenter(state.width / 2, state.height / 2))
    .force("collision", d3.forceCollide().radius((d) => (d.group === "hub" ? 42 : 30)).strength(1))
    .on("tick", ticked);

  function ticked() {
    link.select("line.edge-line")
      .attr("x1", (d) => d.source.x)
      .attr("y1", (d) => d.source.y)
      .attr("x2", (d) => d.target.x)
      .attr("y2", (d) => d.target.y);

    link.select("line.edge-hit")
      .attr("x1", (d) => d.source.x)
      .attr("y1", (d) => d.source.y)
      .attr("x2", (d) => d.target.x)
      .attr("y2", (d) => d.target.y);

    link.select("text.edge-label")
      .attr("x", (d) => (d.source.x + d.target.x) / 2)
      .attr("y", (d) => (d.source.y + d.target.y) / 2 - 6)
      .attr("text-anchor", "middle");

    node.attr("transform", (d) => `translate(${d.x},${d.y})`);
  }
}

function showTooltip(html, event) {
  tooltip.hidden = false;
  tooltip.innerHTML = html;
  const container = document.querySelector(".graph-shell").getBoundingClientRect();
  const left = Math.min(event.clientX - container.left + 18, container.width - 280);
  const top = Math.min(event.clientY - container.top + 18, container.height - 140);
  tooltip.style.left = `${Math.max(left, 12)}px`;
  tooltip.style.top = `${Math.max(top, 12)}px`;
}

function hideTooltip() {
  tooltip.hidden = true;
}

function showNodeTooltip(event, node) {
  showTooltip(
    `
      <strong>${escapeHtml(node.label)}</strong>
      <div>kind: ${escapeHtml(node.kind)}</div>
      <div>project_ref: ${escapeHtml(node.project_ref || "—")}</div>
      <div>group: ${escapeHtml(node.group || "—")}</div>
    `,
    event,
  );
}

function showEdgeTooltip(event, edge) {
  showTooltip(
    `
      <strong>${escapeHtml(edge.label)}</strong>
      <div>payload_format: ${escapeHtml(edge.payload_format)}</div>
      <div>protocol: ${escapeHtml(edge.protocol)}</div>
      <div>channel_type: ${escapeHtml(edge.channel_type)}</div>
      <div>status: ${escapeHtml(edge.status)}</div>
      <div>last_success_at_utc: ${escapeHtml(edge.last_success_at_utc || "—")}</div>
    `,
    event,
  );
}

async function loadState() {
  setResult("");
  const response = await fetch("/api/ecosystem/state");
  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  const payload = await response.json();
  state.server = normalizeState(payload);
  renderMetaBanner();
  renderGraph();
}

function buildSaveRequest() {
  const patch_ops = state.drawerMode === "edge" ? edgePatchOps() : projectPatchOps();
  return { base_revision: state.baseRevision, patch_ops };
}

function createDownload(filename, payload) {
  const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
  const href = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = href;
  anchor.download = filename;
  document.body.append(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(href);
}

async function saveCurrentDrawer() {
  const errors = validateDraft();
  if (errors.length) {
    setSummary(errors.join(" "), "warn");
    return;
  }
  const request = buildSaveRequest();
  patchPreview.textContent = stringifyPatch(request.patch_ops);
  saveExportButton.disabled = true;
  setResult("Saving…");
  try {
    const response = await fetch("/api/ecosystem/state", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(request),
    });
    const payload = await response.json();
    if (!response.ok || payload.success === false) {
      if (payload.conflict) {
        setResult(`Revision conflict at ${payload.revision}. Paths: ${payload.conflict_paths.join(", ")}`);
        await loadState();
        return;
      }
      const message = payload.validation_errors?.length ? payload.validation_errors.join(" ") : payload.message || `HTTP ${response.status}`;
      setResult(message);
      return;
    }
    state.server = normalizeState(payload);
    renderMetaBanner();
    renderGraph();
    setResult(`Saved. Revision ${payload.revision}. Export: ${payload.export_file}`);
    if (payload.state) {
      createDownload(`ecosystem-hub-rev-${payload.revision}.json`, payload.state);
    }
    hideDrawer();
  } catch (error) {
    setResult(error.message || String(error));
  } finally {
    saveExportButton.disabled = false;
  }
}

function wireGlobalActions() {
  refreshStateButton.addEventListener("click", loadState);
  addProjectButton.addEventListener("click", () => openProjectDrawer(null, "new"));
  closeDrawerButton.addEventListener("click", hideDrawer);
  saveExportButton.addEventListener("click", saveCurrentDrawer);
  sectionButtons.forEach((button) => {
    button.addEventListener("click", () => setSection(button.dataset.section));
  });
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") hideDrawer();
  });
  document.querySelector(".graph-shell").addEventListener("click", () => hideTooltip());
  window.addEventListener("resize", () => {
    if (state.server) renderGraph();
  });
}

async function bootstrap() {
  wireGlobalActions();
  try {
    await loadState();
  } catch (error) {
    healthPill.textContent = "Health: offline";
    healthPill.dataset.health = "unknown";
    alertCountStat.textContent = "Open alerts: —";
    metaTaskStrip.innerHTML = `<span class='muted'>Unable to load ecosystem state.</span>`;
    setResult(error.message || String(error));
  }
}

bootstrap();
