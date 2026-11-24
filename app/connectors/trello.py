"""
Trello API Connector for Compass & Hermes Workspace.
Supports listing boards, lists, cards, creating cards, and moving cards.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any
import requests

CREDENTIALS_PATH = Path("C:/workspace/compass/data/trello_credentials.json")


class TrelloClient:
    BASE_URL = "https://api.trello.com/1"

    def __init__(self, api_key: str | None = None, token: str | None = None):
        if not api_key or not token:
            creds = self.load_credentials()
            api_key = api_key or creds.get("api_key")
            token = token or creds.get("token")

        if not api_key or not token:
            raise ValueError(
                "Trello API Key and Token are required. Save them in C:/workspace/compass/data/trello_credentials.json"
            )

        self.api_key = api_key
        self.token = token

    @classmethod
    def load_credentials(cls) -> dict[str, str]:
        if CREDENTIALS_PATH.exists():
            try:
                return json.loads(CREDENTIALS_PATH.read_text(encoding="utf-8"))
            except Exception:
                return {}
        return {}

    @classmethod
    def save_credentials(cls, api_key: str, token: str) -> None:
        CREDENTIALS_PATH.parent.mkdir(parents=True, exist_ok=True)
        CREDENTIALS_PATH.write_text(
            json.dumps({"api_key": api_key.strip(), "token": token.strip()}, indent=2),
            encoding="utf-8",
        )

    def _params(self, extra: dict[str, Any] | None = None) -> dict[str, Any]:
        p = {"key": self.api_key, "token": self.token}
        if extra:
            p.update(extra)
        return p

    def get_me(self) -> dict[str, Any]:
        """Fetch current user info to test authentication."""
        resp = requests.get(f"{self.BASE_URL}/members/me", params=self._params(), timeout=10)
        resp.raise_for_status()
        return resp.json()

    def get_boards(self) -> list[dict[str, Any]]:
        """List all open boards for the authenticated member."""
        resp = requests.get(
            f"{self.BASE_URL}/members/me/boards",
            params=self._params({"filter": "open", "fields": "name,url,closed,desc"}),
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json()

    def get_lists(self, board_id: str) -> list[dict[str, Any]]:
        """List all lists in a board."""
        resp = requests.get(
            f"{self.BASE_URL}/boards/{board_id}/lists",
            params=self._params({"filter": "open", "fields": "name,closed"}),
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json()

    def get_cards(self, list_id: str) -> list[dict[str, Any]]:
        """List open cards in a list."""
        resp = requests.get(
            f"{self.BASE_URL}/lists/{list_id}/cards",
            params=self._params({"filter": "open", "fields": "name,desc,due,dueComplete,url"}),
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json()

    def create_card(
        self,
        list_id: str,
        name: str,
        desc: str = "",
        due: str | None = None,
    ) -> dict[str, Any]:
        """Create a new card on a list."""
        payload = {"idList": list_id, "name": name, "desc": desc}
        if due:
            payload["due"] = due
        resp = requests.post(f"{self.BASE_URL}/cards", params=self._params(payload), timeout=10)
        resp.raise_for_status()
        return resp.json()

    def move_card(self, card_id: str, target_list_id: str) -> dict[str, Any]:
        """Move a card to a different list."""
        resp = requests.put(
            f"{self.BASE_URL}/cards/{card_id}",
            params=self._params({"idList": target_list_id}),
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json()
