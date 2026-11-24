from __future__ import annotations

import sys
from typing import Any

from app.config import get_settings
from app.repository import CompassRepository
from app.services.http_adapter import post_json
from app.services.local_agent_launcher import ensure_rules_engine_running


class RulesEngineAdapter:
    def evaluate(self, context: dict[str, Any], actor: str | None = None) -> dict[str, Any]:
        settings = get_settings()
        ensure_rules_engine_running()
        return post_json(
            settings.rules_engine_base_url,
            "/evaluate",
            {"context": context, "actor": actor},
        )

    def evaluate_event(
        self,
        event: dict[str, Any],
        actor: str | None = None,
        dry_run: bool = False,
        force_unavailable: bool = False,
    ) -> dict[str, Any]:
        if force_unavailable:
            return {"connected": False, "mode": "forced_unavailable", "warning": "rules_engine unavailable"}
        settings = get_settings()
        rule_overrides = CompassRepository().get_rule_overrides_map()
        if local_result := self._evaluate_event_in_process(event, dry_run=dry_run, rule_overrides=rule_overrides):
            return local_result
        ensure_rules_engine_running()
        return post_json(
            settings.rules_engine_base_url,
            "/api/rules/evaluate",
            {"event": event, "actor": actor, "dry_run": dry_run, "rule_overrides": rule_overrides},
        )

    def _evaluate_event_in_process(
        self,
        event: dict[str, Any],
        dry_run: bool,
        rule_overrides: dict[str, dict[str, Any]] | None = None,
    ) -> dict[str, Any] | None:
        rules_path = get_settings().rules_engine_path.resolve()
        if not (rules_path / "compass_rules.py").exists():
            return None
        inserted = False
        rules_path_text = str(rules_path)
        if rules_path_text not in sys.path:
            sys.path.insert(0, rules_path_text)
            inserted = True
        try:
            from compass_rules import RuleEvaluationError, evaluate_structured_event

            result = evaluate_structured_event(event, dry_run=dry_run, rule_overrides=rule_overrides)
            return {"connected": True, "mode": "in_process", "result": result.model_dump(mode="json")}
        except RuleEvaluationError as exc:
            return {"connected": False, "mode": "in_process", "warning": "; ".join(exc.warnings)}
        except (ImportError, OSError, ValueError):
            return None
        finally:
            if inserted:
                try:
                    sys.path.remove(rules_path_text)
                except ValueError:
                    pass

    def get_catalog(self) -> list[dict[str, Any]]:
        rules_path = get_settings().rules_engine_path.resolve()
        if not (rules_path / "compass_rules.py").exists():
            return []
        inserted = False
        rules_path_text = str(rules_path)
        if rules_path_text not in sys.path:
            sys.path.insert(0, rules_path_text)
            inserted = True
        try:
            from compass_rules import get_rules_catalog

            overrides = CompassRepository().get_rule_overrides_map()
            return get_rules_catalog(overrides)
        finally:
            if inserted:
                try:
                    sys.path.remove(rules_path_text)
                except ValueError:
                    pass
