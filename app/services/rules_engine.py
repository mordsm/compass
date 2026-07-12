from __future__ import annotations

from typing import Any

from app.config import get_settings
from app.services.http_adapter import post_json


class RulesEngineAdapter:
    def evaluate(self, context: dict[str, Any], actor: str | None = None) -> dict[str, Any]:
        settings = get_settings()
        return post_json(
            settings.rules_engine_base_url,
            "/evaluate",
            {"context": context, "actor": actor},
        )
