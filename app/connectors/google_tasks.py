from __future__ import annotations

import json
from datetime import datetime, timezone

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from ..config import settings
from .base import Connector, ExternalItem
from .google_auth import google_scopes, load_google_credentials


class GoogleTasksConnector(Connector):
    source_name = "google_tasks"

    def __init__(self, *, token_file: str | None = None) -> None:
        self.token_file = token_file or settings.google_token_file

    def sync(self) -> list[ExternalItem]:
        service = self._service()
        items: list[ExternalItem] = []
        try:
            for task_list in self._task_lists(service):
                list_id = task_list["id"]
                list_title = task_list.get("title")
                page_token = None
                while True:
                    response = (
                        service.tasks()
                        .list(
                            tasklist=list_id,
                            showCompleted=False,
                            showDeleted=False,
                            showHidden=False,
                            pageToken=page_token,
                        )
                        .execute()
                    )
                    items.extend(
                        self._to_external_item(task, list_id, list_title)
                        for task in response.get("items", [])
                    )
                    page_token = response.get("nextPageToken")
                    if not page_token:
                        break
        except HttpError as error:
            api_disabled_message = _api_disabled_message(error)
            if api_disabled_message:
                raise RuntimeError(api_disabled_message) from error
            if error.resp.status in {401, 403}:
                raise RuntimeError(
                    "Google Tasks is enabled, but the current token cannot access Google Tasks. "
                    "Run `uv run taskreminder auth-google --tasks` after configuring "
                    "GOOGLE_CLIENT_SECRET_FILE, or set GOOGLE_TASKS_ENABLED=false."
                ) from error
            raise
        return items

    def mark_done(self, source_object_id: str) -> None:
        task_list_id, task_id = _split_source_object_id(source_object_id)
        completed_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        (
            self._service()
            .tasks()
            .patch(
                tasklist=task_list_id,
                task=task_id,
                body={"status": "completed", "completed": completed_at},
            )
            .execute()
        )

    def _service(self):
        return build(
            "tasks",
            "v1",
            credentials=load_google_credentials(
                google_scopes(include_tasks=True),
                self.token_file,
            ),
            cache_discovery=False,
        )

    def _task_lists(self, service) -> list[dict]:
        task_lists: list[dict] = []
        page_token = None
        while True:
            response = service.tasklists().list(pageToken=page_token).execute()
            task_lists.extend(response.get("items", []))
            page_token = response.get("nextPageToken")
            if not page_token:
                return task_lists

    def _to_external_item(self, task: dict, task_list_id: str, task_list_title: str | None) -> ExternalItem:
        raw = dict(task)
        raw["task_list_id"] = task_list_id
        raw["task_list_title"] = task_list_title
        return ExternalItem(
            source=self.source_name,
            source_object_id=f"{task_list_id}:{task['id']}",
            title=task.get("title") or "(Untitled Google Task)",
            description=task.get("notes"),
            task_type="single" if task.get("due") else "backlog",
            due_at=_parse_google_task_time(task.get("due")),
            source_url=task.get("webViewLink") or task.get("selfLink"),
            raw=raw,
        )


def _parse_google_task_time(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _split_source_object_id(source_object_id: str) -> tuple[str, str]:
    parts = source_object_id.split(":", 1)
    if len(parts) != 2 or not parts[0] or not parts[1]:
        raise ValueError("Google Tasks source_object_id must be '<task_list_id>:<task_id>'")
    return parts[0], parts[1]


def _api_disabled_message(error: HttpError) -> str | None:
    try:
        payload = json.loads(error.content.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None
    error_info = payload.get("error") or {}
    errors = error_info.get("errors") or []
    if any(item.get("reason") == "accessNotConfigured" for item in errors):
        return error_info.get("message") or "Google Tasks API is disabled for this Cloud project"
    return None
