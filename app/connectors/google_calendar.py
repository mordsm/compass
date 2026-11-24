from __future__ import annotations

from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from googleapiclient.discovery import build

from ..config import settings
from .base import Connector, ExternalItem
from .google_auth import google_scopes, load_google_credentials


class GoogleCalendarConnector(Connector):
    source_name = "google_calendar"

    def __init__(
        self,
        *,
        token_file: str | None = None,
        calendar_id: str = "primary",
        lookahead_days: int = 14,
    ) -> None:
        self.token_file = token_file or settings.google_token_file
        self.calendar_id = calendar_id
        self.lookahead_days = lookahead_days

    def sync(self) -> list[ExternalItem]:
        service = build("calendar", "v3", credentials=self._credentials(), cache_discovery=False)
        now = datetime.now(ZoneInfo(settings.app_timezone))
        end = now + timedelta(days=self.lookahead_days)
        response = (
            service.events()
            .list(
                calendarId=self.calendar_id,
                timeMin=now.isoformat(),
                timeMax=end.isoformat(),
                singleEvents=True,
                orderBy="startTime",
            )
            .execute()
        )
        return [self._to_external_item(event) for event in response.get("items", [])]

    def _credentials(self):
        return load_google_credentials(
            google_scopes(include_tasks=settings.google_tasks_enabled),
            self.token_file,
        )

    def _to_external_item(self, event: dict) -> ExternalItem:
        start = _parse_event_time(event.get("start", {}))
        end = None
        if "dateTime" in event.get("end", {}):
            end = _parse_event_time(event.get("end", {}))
        source_url = event.get("htmlLink")
        return ExternalItem(
            source=self.source_name,
            source_object_id=event["id"],
            title=event.get("summary") or "(Untitled calendar event)",
            description=event.get("description"),
            task_type="appointment",
            due_at=start,
            deadline_at=end,
            source_url=source_url,
            raw=event,
        )

    def mark_done(self, source_object_id: str) -> None:
        # Calendar is read-only in MVP.
        return None


def _parse_event_time(value: dict) -> datetime | None:
    if "dateTime" in value:
        return datetime.fromisoformat(value["dateTime"].replace("Z", "+00:00"))
    if "date" in value:
        event_date = datetime.fromisoformat(value["date"]).date()
        return datetime.combine(event_date, time.min, tzinfo=ZoneInfo(settings.app_timezone))
    return None
