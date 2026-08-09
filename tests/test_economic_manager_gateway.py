from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path


class EconomicManagerGatewayTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)
        os.environ["COMPASS_DATABASE_URL"] = ""
        os.environ["COMPASS_DATABASE_PATH"] = str(Path(self.tmpdir.name) / "compass.db")
        os.environ["COMPASS_ACTIONS_API_KEY"] = "test-token"

        from app.config import get_settings
        from app.database import init_db

        get_settings.cache_clear()
        init_db()

    def test_compass_invokes_external_economic_manager(self):
        from app.routers.agents import invoke_agent
        from app.schemas.agents import InvokeAgentRequest
        from app.services.economic_manager import EconomicManagerAdapter

        original = EconomicManagerAdapter.invoke_agent

        def invoke_agent_stub(_self, payload):
            return {
                "connected": True,
                "result": {
                    "agent_id": "economic_manager",
                    "task": payload["task"],
                    "status": "complete",
                    "signals": ["large_transaction"],
                },
            }

        EconomicManagerAdapter.invoke_agent = invoke_agent_stub
        self.addCleanup(setattr, EconomicManagerAdapter, "invoke_agent", original)

        result = invoke_agent(
            InvokeAgentRequest(
                agent_id="economic_manager",
                task="record_transaction",
                user_id="moshe",
                context={
                    "household_id": "moshe_household",
                    "description": "demo",
                    "amount": {"amount_minor": 60000, "currency": "ILS"},
                },
            )
        )

        self.assertTrue(result["connected"])
        self.assertEqual(result["result"]["agent_id"], "economic_manager")
        self.assertEqual(result["result"]["signals"], ["large_transaction"])

    def test_compass_syncs_mail_financial_items_to_economic_manager(self):
        from app.routers.agents import invoke_agent
        from app.schemas.agents import InvokeAgentRequest
        from app.services.economic_manager import EconomicManagerAdapter
        from app.services.mail_manager import MailManagerAdapter

        original_financial_items = MailManagerAdapter.financial_items
        original_import = EconomicManagerAdapter.import_financial_items
        captured = {}

        def financial_items_stub(_self, limit=20, status=None):
            captured["mail_args"] = {"limit": limit, "status": status}
            return {
                "items": [
                    {
                        "id": "financial-1",
                        "supplier_name": "Electric Company",
                        "document_type": "invoice",
                        "amount": 321.45,
                        "currency": "ILS",
                        "due_date": "2026-08-20",
                    }
                ]
            }

        def import_stub(_self, payload):
            captured["payload"] = payload
            return {"status": "complete", "created": 1, "duplicates": 0, "failed": []}

        MailManagerAdapter.financial_items = financial_items_stub
        EconomicManagerAdapter.import_financial_items = import_stub
        self.addCleanup(setattr, MailManagerAdapter, "financial_items", original_financial_items)
        self.addCleanup(setattr, EconomicManagerAdapter, "import_financial_items", original_import)

        result = invoke_agent(
            InvokeAgentRequest(
                agent_id="economic_manager",
                task="sync_mail_financial_items",
                user_id="moshe",
                context={"household_id": "home", "limit": 10, "status": "unknown"},
            )
        )

        self.assertTrue(result["connected"])
        self.assertEqual(result["result"]["created"], 1)
        self.assertEqual(captured["mail_args"], {"limit": 10, "status": "unknown"})
        self.assertEqual(captured["payload"]["household_id"], "home")
        self.assertEqual(captured["payload"]["items"][0]["id"], "financial-1")


if __name__ == "__main__":
    unittest.main()
