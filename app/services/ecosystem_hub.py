from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from app.database import db, json_dump, json_load, utc_now
from app.schemas.ecosystem import (
    EcosystemPatchRequest,
    EcosystemPatchResponse,
    EcosystemState,
    EcosystemStateEnvelope,
)

STATE_ID = "ecosystem_hub"
SEED_PATH = Path(__file__).resolve().parents[1] / "data" / "ecosystem-hub.seed.json"
EXPORT_DIR = Path(__file__).resolve().parents[1] / "exports"


class EcosystemHubService:
    def ensure_seeded(self) -> None:
        with db() as conn:
            conn.execute(
                """
                create table if not exists ecosystem_hub_state (
                    id text primary key,
                    revision integer not null,
                    state_json text not null,
                    updated_at text not null
                )
                """
            )
            row = conn.execute(
                "select id from ecosystem_hub_state where id = ?",
                (STATE_ID,),
            ).fetchone()
            if row:
                return
            seed = self._load_seed()
            conn.execute(
                "insert into ecosystem_hub_state (id, revision, state_json, updated_at) values (?, ?, ?, ?)",
                (STATE_ID, int(seed["revision"]), json_dump(seed), utc_now()),
            )

    def get_state_envelope(self) -> dict[str, Any]:
        self.ensure_seeded()
        with db() as conn:
            row = conn.execute(
                "select revision, state_json, updated_at from ecosystem_hub_state where id = ?",
                (STATE_ID,),
            ).fetchone()
        if not row:
            seed = self._load_seed()
            return {"success": True, "state": seed}
        state = json_load(row["state_json"], {})
        state["revision"] = int(row["revision"])
        return {"success": True, "state": state}

    def save_patch(self, request: EcosystemPatchRequest) -> dict[str, Any]:
        self.ensure_seeded()
        with db() as conn:
            row = conn.execute(
                "select revision, state_json from ecosystem_hub_state where id = ?",
                (STATE_ID,),
            ).fetchone()
            if not row:
                seed = self._load_seed()
                current_revision = int(seed["revision"])
                current_state = seed
            else:
                current_revision = int(row["revision"])
                current_state = json_load(row["state_json"], {})
                current_state["revision"] = current_revision

            if request.base_revision != current_revision:
                return EcosystemPatchResponse(
                    success=False,
                    conflict=True,
                    revision=current_revision,
                    state=self._to_model(current_state),
                    conflict_paths=[op.path for op in request.patch_ops],
                    message="Revision conflict. Refetch state and re-apply your changes.",
                ).model_dump(mode="json")

            candidate = deepcopy(current_state)
            patch_ops = [op.model_dump(mode="json") for op in request.patch_ops]
            try:
                for op in patch_ops:
                    self._apply_op(candidate, op["op"], op["path"], op.get("value"))
            except (KeyError, IndexError, TypeError, ValueError) as exc:
                return EcosystemPatchResponse(
                    success=False,
                    conflict=False,
                    revision=current_revision,
                    state=self._to_model(current_state),
                    applied_patch_ops=request.patch_ops,
                    validation_errors=[f"Patch application failed: {exc}"],
                    message="Patch could not be applied.",
                ).model_dump(mode="json")

            candidate["revision"] = current_revision + 1
            validation_errors = self.validate_state(candidate)
            if validation_errors:
                return EcosystemPatchResponse(
                    success=False,
                    conflict=False,
                    revision=current_revision,
                    state=self._to_model(current_state),
                    applied_patch_ops=request.patch_ops,
                    validation_errors=validation_errors,
                    message="Validation failed after applying patch.",
                ).model_dump(mode="json")

            export_file = self._write_exports(candidate, patch_ops)
            with db() as conn:
                conn.execute(
                    "update ecosystem_hub_state set revision = ?, state_json = ?, updated_at = ? where id = ?",
                    (candidate["revision"], json_dump(candidate), utc_now(), STATE_ID),
                )
            return EcosystemPatchResponse(
                success=True,
                revision=candidate["revision"],
                state=self._to_model(candidate),
                applied_patch_ops=request.patch_ops,
                export_file=str(export_file),
            ).model_dump(mode="json")

    def validate_state(self, state: dict[str, Any]) -> list[str]:
        errors: list[str] = []
        try:
            model = EcosystemState.model_validate(state)
        except ValidationError as exc:
            for item in exc.errors():
                loc = "/".join(str(part) for part in item.get("loc", []))
                errors.append(f"{loc}: {item.get('msg')}")
            return errors

        project_refs = {project.project_ref for project in model.project_windows}
        node_ids = {node.id for node in model.meta_window.graph.nodes}
        node_refs = {node.project_ref for node in model.meta_window.graph.nodes if node.project_ref}

        missing_nodes = sorted(project_refs - node_refs)
        if missing_nodes:
            errors.append("Missing graph nodes for project_ref(s): " + ", ".join(missing_nodes))

        duplicate_node_ids = self._duplicate_ids([node.id for node in model.meta_window.graph.nodes])
        if duplicate_node_ids:
            errors.append("Duplicate node id(s): " + ", ".join(duplicate_node_ids))

        duplicate_edge_ids = self._duplicate_ids([edge.id for edge in model.meta_window.graph.edges])
        if duplicate_edge_ids:
            errors.append("Duplicate edge id(s): " + ", ".join(duplicate_edge_ids))

        for edge in model.meta_window.graph.edges:
            if edge.source not in node_ids:
                errors.append(f"Edge {edge.id} source is missing: {edge.source}")
            if edge.target not in node_ids:
                errors.append(f"Edge {edge.id} target is missing: {edge.target}")

        for project in model.project_windows:
            tasks = project.roadmap_and_tasks.tasks
            for task in tasks:
                if not task.title.strip():
                    errors.append(f"Project {project.project_ref} has a task with an empty title")
                if task.priority not in {"low", "medium", "high", "urgent"}:
                    errors.append(f"Project {project.project_ref} task {task.id} has invalid priority")
                if task.status not in {"planned", "open", "in_progress", "blocked", "done", "archived"}:
                    errors.append(f"Project {project.project_ref} task {task.id} has invalid status")

        if model.meta_window.open_alert_count < 0:
            errors.append("open_alert_count must be non-negative")

        return errors

    def _load_seed(self) -> dict[str, Any]:
        if SEED_PATH.exists():
            with SEED_PATH.open("r", encoding="utf-8") as handle:
                seed = json.load(handle)
        else:
            seed = {"revision": 1, "meta_window": {"health": "unknown", "open_alert_count": 0, "meta_tasks": [], "graph": {"nodes": [], "edges": []}}, "project_windows": []}
        if "revision" not in seed:
            seed["revision"] = 1
        return seed

    def _to_model(self, state: dict[str, Any]) -> EcosystemState:
        return EcosystemState.model_validate(state)

    def _duplicate_ids(self, ids: list[str]) -> list[str]:
        seen: set[str] = set()
        dupes: set[str] = set()
        for item in ids:
            if item in seen:
                dupes.add(item)
            seen.add(item)
        return sorted(dupes)

    def _write_exports(self, state: dict[str, Any], patch_ops: list[dict[str, Any]]) -> Path:
        EXPORT_DIR.mkdir(parents=True, exist_ok=True)
        rev = int(state["revision"])
        timestamp = utc_now().replace(":", "-")
        latest = EXPORT_DIR / "ecosystem-hub-latest.json"
        versioned = EXPORT_DIR / f"ecosystem-hub-rev-{rev:04d}-{timestamp}.json"
        payload = {
            "exported_at_utc": utc_now(),
            "revision": rev,
            "state": state,
            "patch_ops": patch_ops,
        }
        latest.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        versioned.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return versioned

    def _apply_op(self, document: dict[str, Any], op: str, path: str, value: Any) -> None:
        tokens = self._parse_pointer(path)
        if not tokens:
            raise ValueError("Empty JSON pointer is not supported")
        parent, last = self._resolve_parent(document, tokens, create_for_add=(op == "add"))
        if op == "add":
            self._set(parent, last, value, add=True)
        elif op == "replace":
            self._set(parent, last, value, add=False)
        elif op == "remove":
            self._remove(parent, last)
        else:
            raise ValueError(f"Unsupported op: {op}")

    def _parse_pointer(self, path: str) -> list[str]:
        if not path.startswith("/"):
            raise ValueError(f"Invalid JSON pointer: {path}")
        parts = path.split("/")[1:]
        return [part.replace("~1", "/").replace("~0", "~") for part in parts]

    def _resolve_parent(self, document: Any, tokens: list[str], create_for_add: bool = False) -> tuple[Any, str]:
        current = document
        for token in tokens[:-1]:
            if isinstance(current, list):
                index = len(current) if token == "-" else int(token)
                if index >= len(current):
                    if not create_for_add:
                        raise IndexError(token)
                    while len(current) <= index:
                        current.append({})
                current = current[index]
            elif isinstance(current, dict):
                if token not in current:
                    if not create_for_add:
                        raise KeyError(token)
                    current[token] = {}
                current = current[token]
            else:
                raise TypeError(f"Cannot traverse through {type(current)!r}")
        return current, tokens[-1]

    def _set(self, parent: Any, key: str, value: Any, add: bool) -> None:
        if isinstance(parent, list):
            if key == "-":
                parent.append(value)
                return
            index = int(key)
            if add:
                parent.insert(index, value)
            else:
                parent[index] = value
            return
        if isinstance(parent, dict):
            parent[key] = value
            return
        raise TypeError(f"Cannot assign into {type(parent)!r}")

    def _remove(self, parent: Any, key: str) -> None:
        if isinstance(parent, list):
            if key == "-":
                raise ValueError("Cannot remove using '-' from a list")
            del parent[int(key)]
            return
        if isinstance(parent, dict):
            del parent[key]
            return
        raise TypeError(f"Cannot remove from {type(parent)!r}")


service = EcosystemHubService()
