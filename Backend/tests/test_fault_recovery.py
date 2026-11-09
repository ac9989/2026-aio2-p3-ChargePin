"""Integration Test Checker for deterministic ChargePin fault scenarios."""
from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app, authenticator, orchestrator
from app.store import MemoryKeeper


SEARCH_BODY = {
    "center": {"lat": 37.498, "lng": 127.027},
    "radius_km": 0.5,
    "connector_types": ["FAST", "SLOW"],
    "region_filters": [],
}


class FaultRecoveryCheckerTests(unittest.TestCase):
    """Exercise Test API → normal request → Critic/Handoff/operations evidence."""

    def setUp(self) -> None:
        self.environment = patch.dict(os.environ, {
            "CHARGEPIN_ENABLE_FAULT_INJECTION": "true",
            "HIGH_MANAGER_SERVICE_KEY": "test-high-manager",
            "LOW_MANAGER_SERVICE_KEY": "test-low-manager",
            "CUSTOMER_SERVICE_KEY": "test-customer",
        }, clear=False)
        self.environment.start()
        authenticator._sessions.clear()
        orchestrator.memory = MemoryKeeper()
        orchestrator.test_scenarios.clear()
        self.client = TestClient(app)
        login = self.client.post("/api/v1/auth/login", json={"service_key": "test-high-manager"})
        self.assertEqual(login.status_code, 200)
        self.headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    def tearDown(self) -> None:
        orchestrator.test_scenarios.clear()
        authenticator._sessions.clear()
        self.environment.stop()

    def activate(self, scenario: str) -> None:
        response = self.client.post(f"/api/v1/test/faults/{scenario}", headers=self.headers)
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["active"], scenario)

    def search(self) -> dict:
        response = self.client.post("/api/v1/search", json=SEARCH_BODY, headers=self.headers)
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    def test_test_api_is_disabled_without_its_explicit_environment_switch(self) -> None:
        with patch.dict(os.environ, {"CHARGEPIN_ENABLE_FAULT_INJECTION": "false"}, clear=False):
            response = self.client.get("/api/v1/test/faults", headers=self.headers)
        self.assertEqual(response.status_code, 404)

    def test_normal_fixture_returns_a_verified_result(self) -> None:
        self.activate("normal")
        payload = self.search()

        self.assertEqual(payload["status"], "completed")
        self.assertEqual(payload["critic_decision"], "PASS")
        self.assertEqual(payload["results"][0]["availability"]["state"], "AVAILABLE")

    def test_stale_and_invalid_count_fixtures_are_safe_without_retry(self) -> None:
        for scenario, expected_state in (("stale", "DELAYED"), ("invalid_count", "UNAVAILABLE")):
            with self.subTest(scenario=scenario):
                self.activate(scenario)
                payload = self.search()
                availability = payload["results"][0]["availability"]
                handoff = orchestrator.memory.handoffs[payload["request_id"]]

                self.assertEqual(payload["status"], "degraded")
                self.assertEqual(payload["critic_decision"], "SAFE_UNAVAILABLE")
                self.assertEqual(availability["state"], expected_state)
                self.assertIsNone(availability["available_chargers"])
                self.assertIsNone(availability["total_chargers"])
                self.assertEqual(handoff["retry_history"], [])

    def test_ft01_timeout_retries_twice_then_records_safe_response_and_operations(self) -> None:
        self.activate("timeout")
        with patch("app.agents.sleep"):
            payload = self.search()
        handoff = orchestrator.memory.handoffs[payload["request_id"]]
        summary = self.client.get("/api/v1/ops/summary", headers=self.headers).json()

        self.assertEqual(payload["status"], "degraded")
        self.assertEqual(payload["critic_decision"], "SAFE_UNAVAILABLE")
        self.assertEqual(len(handoff["retry_history"]), 2)
        self.assertTrue(all(item["kind"] == "automatic" for item in handoff["retry_history"]))
        self.assertEqual(
            len([event for event in orchestrator.memory.operation_events if event.get("event_type") == "test_fault"]),
            3,
        )
        self.assertGreaterEqual(summary["metrics"]["retry_count"], 2)

    def test_ft02_executor_exception_is_safe_and_auditable(self) -> None:
        self.activate("executor_exception")
        payload = self.search()
        handoff = orchestrator.memory.handoffs[payload["request_id"]]

        self.assertEqual(payload["status"], "degraded")
        self.assertEqual(payload["critic_decision"], "SAFE_UNAVAILABLE")
        self.assertEqual(payload["results"], [])
        self.assertIn("executor_exception", handoff["audit_events"])
        self.assertIn("잠시 후 다시 시도", payload["critic_findings"][0])
        self.assertNotIn("test executor exception", str(payload))

    def test_ft04_invalid_llm_schema_blocks_provider_lookup(self) -> None:
        self.activate("llm_invalid_schema")
        with patch.object(orchestrator.executor, "place_candidates") as place_candidates:
            response = self.client.post(
                "/api/v1/chat/plan",
                json={"message": "사당역 근처 두 키로 급속으로 찾아 줘"},
                headers=self.headers,
            )
        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()
        handoff = orchestrator.memory.handoffs[payload["request_id"]]

        self.assertEqual(payload["status"], "NEEDS_INPUT")
        self.assertIn("AI 자연어 해석", payload["message"])
        self.assertIn("llm_plan_error", handoff["audit_events"])
        place_candidates.assert_not_called()


if __name__ == "__main__":
    unittest.main()
