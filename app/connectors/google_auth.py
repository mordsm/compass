from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from ..config import settings


CALENDAR_READONLY_SCOPE = "https://www.googleapis.com/auth/calendar.readonly"
TASKS_SCOPE = "https://www.googleapis.com/auth/tasks"


@dataclass(frozen=True)
class GoogleSetupCheck:
    status: str
    name: str
    detail: str


def google_scopes(*, include_tasks: bool = False) -> list[str]:
    scopes = [CALENDAR_READONLY_SCOPE]
    if include_tasks:
        scopes.append(TASKS_SCOPE)
    return scopes


def load_google_credentials(
    scopes: list[str],
    token_file: str | None = None,
    *,
    force_refresh: bool = False,
) -> Credentials:
    configured_token_file = token_file or settings.google_token_file
    if not configured_token_file:
        raise RuntimeError("GOOGLE_TOKEN_FILE is not configured")

    token_path = Path(configured_token_file)
    if not token_path.exists():
        raise RuntimeError(f"Google token file does not exist: {token_path}")

    existing_token_data = json.loads(token_path.read_text(encoding="utf-8"))
    credentials = Credentials.from_authorized_user_file(str(token_path), scopes)
    if (credentials.expired or force_refresh) and credentials.refresh_token:
        credentials.refresh(Request())
        refreshed_token_data = json.loads(credentials.to_json())
        refreshed_token_data["scopes"] = sorted(
            set(existing_token_data.get("scopes") or []) | set(scopes)
        )
        token_path.write_text(json.dumps(refreshed_token_data), encoding="utf-8")
    if not credentials.valid:
        raise RuntimeError("Google credentials are invalid; recreate google_token.json")
    return credentials


def authorize_google_credentials(
    *,
    include_tasks: bool = False,
    client_secret_file: str | None = None,
    token_file: str | None = None,
    port: int = 0,
    backup_existing: bool = True,
) -> Path:
    configured_client_secret_file = client_secret_file or settings.google_client_secret_file
    configured_token_file = token_file or settings.google_token_file
    if not configured_client_secret_file:
        raise RuntimeError("GOOGLE_CLIENT_SECRET_FILE is not configured")
    if not configured_token_file:
        raise RuntimeError("GOOGLE_TOKEN_FILE is not configured")

    client_secret_path = Path(configured_client_secret_file)
    if not client_secret_path.exists():
        raise RuntimeError(f"Google client secret file does not exist: {client_secret_path}")

    token_path = Path(configured_token_file)
    token_path.parent.mkdir(parents=True, exist_ok=True)
    if backup_existing and token_path.exists():
        backup_path = token_path.with_suffix(f"{token_path.suffix}.bak")
        backup_path.write_text(token_path.read_text(encoding="utf-8"), encoding="utf-8")

    flow = InstalledAppFlow.from_client_secrets_file(
        str(client_secret_path),
        google_scopes(include_tasks=include_tasks),
    )
    credentials = flow.run_local_server(
        port=port,
        prompt="consent",
        access_type="offline",
    )
    granted_scopes = getattr(credentials, "granted_scopes", None)
    if granted_scopes is not None:
        missing_scopes = set(google_scopes(include_tasks=include_tasks)) - set(granted_scopes)
        if missing_scopes:
            missing = ", ".join(sorted(missing_scopes))
            raise RuntimeError(f"Google did not grant required scope(s): {missing}")
    token_path.write_text(credentials.to_json(), encoding="utf-8")
    return token_path


def check_google_setup(
    *,
    token_file: str | None = None,
    client_secret_file: str | None = None,
    require_tasks: bool | None = None,
    live: bool = False,
    refresh: bool = False,
) -> list[GoogleSetupCheck]:
    checks: list[GoogleSetupCheck] = []
    configured_token_file = token_file or settings.google_token_file
    configured_client_secret_file = client_secret_file or settings.google_client_secret_file
    tasks_required = settings.google_tasks_enabled if require_tasks is None else require_tasks
    if refresh and configured_token_file:
        try:
            load_google_credentials(
                google_scopes(include_tasks=tasks_required),
                configured_token_file,
                force_refresh=True,
            )
        except Exception:
            pass

    token_data = _read_token_data(configured_token_file, checks)
    _check_client_secret(configured_client_secret_file, checks)
    if token_data is not None:
        _check_token_data(token_data, tasks_required, checks)
    if live and configured_token_file:
        _check_live_google_access(configured_token_file, tasks_required, checks, refresh=refresh)

    return checks


def google_setup_ok(checks: list[GoogleSetupCheck]) -> bool:
    return all(check.status != "FAIL" for check in checks)


def _read_token_data(
    configured_token_file: str | None,
    checks: list[GoogleSetupCheck],
) -> dict | None:
    if not configured_token_file:
        checks.append(GoogleSetupCheck("FAIL", "token file", "GOOGLE_TOKEN_FILE is not configured"))
        return None

    token_path = Path(configured_token_file)
    if not token_path.exists():
        checks.append(GoogleSetupCheck("FAIL", "token file", f"not found: {token_path}"))
        return None

    checks.append(GoogleSetupCheck("OK", "token file", str(token_path)))
    try:
        return json.loads(token_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        checks.append(GoogleSetupCheck("FAIL", "token json", f"invalid JSON: {error}"))
        return None


def _check_client_secret(
    configured_client_secret_file: str | None,
    checks: list[GoogleSetupCheck],
) -> None:
    if not configured_client_secret_file:
        checks.append(
            GoogleSetupCheck("WARN", "client secret", "GOOGLE_CLIENT_SECRET_FILE is not configured")
        )
        return

    client_secret_path = Path(configured_client_secret_file)
    if client_secret_path.exists():
        checks.append(GoogleSetupCheck("OK", "client secret", str(client_secret_path)))
    else:
        checks.append(
            GoogleSetupCheck(
                "WARN",
                "client secret",
                f"not found: {client_secret_path}; needed only for auth-google",
            )
        )


def _check_token_data(
    token_data: dict,
    tasks_required: bool,
    checks: list[GoogleSetupCheck],
) -> None:
    scopes = set(token_data.get("scopes") or [])
    _check_scope(CALENDAR_READONLY_SCOPE, scopes, checks, required=True)
    _check_scope(TASKS_SCOPE, scopes, checks, required=tasks_required)

    if token_data.get("refresh_token"):
        checks.append(GoogleSetupCheck("OK", "refresh token", "present"))
    else:
        checks.append(GoogleSetupCheck("WARN", "refresh token", "missing; token may expire permanently"))

    expiry = _parse_expiry(token_data.get("expiry"))
    if expiry is None:
        checks.append(GoogleSetupCheck("WARN", "token expiry", "missing or invalid"))
    elif expiry <= datetime.now(timezone.utc):
        checks.append(GoogleSetupCheck("WARN", "token expiry", f"expired at {expiry.isoformat()}"))
    else:
        checks.append(GoogleSetupCheck("OK", "token expiry", expiry.isoformat()))


def _check_scope(
    scope: str,
    scopes: set[str],
    checks: list[GoogleSetupCheck],
    *,
    required: bool,
) -> None:
    if scope in scopes:
        checks.append(GoogleSetupCheck("OK", "scope", scope))
    elif required:
        checks.append(GoogleSetupCheck("FAIL", "scope", f"missing required scope: {scope}"))
    else:
        checks.append(GoogleSetupCheck("WARN", "scope", f"optional scope missing: {scope}"))


def _parse_expiry(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _check_live_google_access(
    configured_token_file: str,
    tasks_required: bool,
    checks: list[GoogleSetupCheck],
    *,
    refresh: bool = False,
) -> None:
    scopes = google_scopes(include_tasks=tasks_required)
    try:
        credentials = load_google_credentials(scopes, configured_token_file, force_refresh=refresh)
        (
            build("calendar", "v3", credentials=credentials, cache_discovery=False)
            .calendarList()
            .list(maxResults=1)
            .execute()
        )
        checks.append(GoogleSetupCheck("OK", "live calendar", "Calendar API accepted token"))
    except Exception as error:
        checks.append(GoogleSetupCheck("FAIL", "live calendar", str(error)))
        return

    if not tasks_required:
        return

    try:
        (
            build("tasks", "v1", credentials=credentials, cache_discovery=False)
            .tasklists()
            .list(maxResults=1)
            .execute()
        )
        checks.append(GoogleSetupCheck("OK", "live tasks", "Tasks API accepted token"))
    except HttpError as error:
        api_disabled_message = _api_disabled_message(error)
        if api_disabled_message:
            checks.append(GoogleSetupCheck("FAIL", "live tasks", api_disabled_message))
            return
        if error.resp.status in {401, 403}:
            checks.append(
                GoogleSetupCheck(
                    "FAIL",
                    "live tasks",
                    "Tasks API rejected token; delete google_token.json and run auth-google --tasks",
                )
            )
            return
        checks.append(GoogleSetupCheck("FAIL", "live tasks", str(error)))
    except Exception as error:
        checks.append(GoogleSetupCheck("FAIL", "live tasks", str(error)))


def _api_disabled_message(error: HttpError) -> str | None:
    try:
        payload = json.loads(error.content.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None
    error_info = payload.get("error") or {}
    errors = error_info.get("errors") or []
    if any(item.get("reason") == "accessNotConfigured" for item in errors):
        return error_info.get("message") or "Google API is disabled for this Cloud project"
    return None
