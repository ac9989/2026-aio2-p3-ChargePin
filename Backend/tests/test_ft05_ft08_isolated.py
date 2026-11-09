"""Isolated regression tests for FT-05 through FT-08.

Mocks only: no external calls, deployed services, or paid LLM requests.
"""
from __future__ import annotations

import unittest
from urllib.error import HTTPError
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.agents import Critic
from app.main import app, authenticator, orchestrator
from app.models import ConnectorType, Point, SearchOrigin, SearchRequest
from app.providers import EnvironmentChargerAdapter, KakaoPlaceAdapter, ProviderError, kst_now
from app.store import MemoryKeeper


SEARCH_BODY = {
    "center": {"lat": 37.498, "lng": 127.027},
    "radius_km": 0.5,
    "connector_types": ["FAST", "SLOW"],
    "region_filters": [],
}


def http_error(status: int) -> HTTPError:
    return HTTPError("https://example.invalid/provider", status, "mocked", {}, None)


class ExtendedFaultTests(unittest.TestCase):
    def setUp(self):
        authenticator._sessions.clear()
        orchestrator.memory = MemoryKeeper()
        orchestrator.test_scenarios.clear()
        self.client = TestClient(app)
        with patch.dict("os.environ", {"HIGH_MANAGER_SERVICE_KEY": "ft-isolated-manager"}):
            resp = self.client.post("/api/v1/auth/login", json={"service_key": "ft-isolated-manager"})
        self.assertEqual(resp.status_code, 200, resp.text)
        self.headers = {"Authorization": "Bearer " + resp.json()["access_token"]}

    def tearDown(self):
        orchestrator.test_scenarios.clear()
        authenticator._sessions.clear()

    def search(self):
        response = self.client.post("/api/v1/search", headers=self.headers, json=SEARCH_BODY)
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    def test_ft05_kakao_and_keco_429_classified_retryable(self):
        with patch.dict("os.environ", {"KAKAO_REST_API_KEY": "dummy"}):
            kakao = KakaoPlaceAdapter()
        with patch("app.providers.urlopen", side_effect=http_error(429)):
            with self.assertRaises(ProviderError) as caught:
                kakao.top_two("사당역")
        self.assertTrue(caught.exception.retryable)
        self.assertEqual(caught.exception.provider, "KAKAO")
        with patch.dict("os.environ", {"KECO_SERVICE_KEY": "dummy"}):
            keco = EnvironmentChargerAdapter()
        with patch("app.providers.urlopen", side_effect=http_error(429)):
            with self.assertRaises(ProviderError) as caught:
                keco._get_page("getChargerInfo", page_no=1, num_rows=1, extra={})
        self.assertTrue(caught.exception.retryable)
        self.assertEqual(caught.exception.provider, "KECO")

    def test_ft05_429_stops_after_two_automatic_retries(self):
        rate_limit = ProviderError("KECO", "환경공단 API 요청이 제한되었습니다.", retryable=True)
        with patch.object(orchestrator.executor, "execute", side_effect=rate_limit) as execute, patch("app.agents.sleep"):
            payload = self.search()
        self.assertEqual(execute.call_count, 3)
        self.assertEqual(payload["status"], "degraded")
        self.assertEqual(payload["critic_decision"], "SAFE_UNAVAILABLE")
        self.assertEqual(len(orchestrator.memory.handoffs[payload["request_id"]]["retry_history"]), 2)
        self.assertNotIn("dummy", str(payload))

    def test_ft05_429_then_recovery(self):
        rate_limit = ProviderError("KECO", "요청 제한", retryable=True)
        with patch.object(orchestrator.executor, "execute", side_effect=[rate_limit, rate_limit, []]) as execute, patch("app.agents.sleep"):
            payload = self.search()
        self.assertEqual(execute.call_count, 3)
        self.assertEqual(payload["status"], "completed")
        self.assertEqual(len(orchestrator.memory.handoffs[payload["request_id"]]["retry_history"]), 2)

    def test_ft06_information_cache_hit_expiry_and_clear(self):
        adapter = EnvironmentChargerAdapter()
        with patch.object(adapter, "_all_pages", side_effect=[[{"version": 1}], [{"version": 2}], [{"version": 3}]]) as load:
            self.assertEqual(adapter._info(None)[0]["version"], 1)
            self.assertEqual(adapter._info(None)[0]["version"], 1)
            self.assertEqual(load.call_count, 1)
            adapter._cache_ttl_seconds = -1
            self.assertEqual(adapter._info(None)[0]["version"], 2)
            self.assertEqual(load.call_count, 2)
            adapter.clear_cache()
            self.assertEqual(adapter.cache_snapshot()["info_cache_entries"], 0)
            self.assertEqual(adapter._info(None)[0]["version"], 3)
            self.assertEqual(load.call_count, 3)

    def test_ft06_status_cache_hit_expiry_and_clear(self):
        adapter = EnvironmentChargerAdapter()
        first = [{"statId": "station", "chgerId": "1", "stat": "2"}]
        second = [{"statId": "station", "chgerId": "1", "stat": "3"}]
        with patch.object(adapter, "_all_pages", side_effect=[first, second, first]) as load:
            self.assertEqual(adapter._recent_statuses()[("station", "1")]["stat"], "2")
            self.assertEqual(adapter._recent_statuses()[("station", "1")]["stat"], "2")
            self.assertEqual(load.call_count, 1)
            adapter._status_cache_ttl_seconds = -1
            self.assertEqual(adapter._recent_statuses()[("station", "1")]["stat"], "3")
            adapter.clear_cache()
            self.assertFalse(adapter.cache_snapshot()["status_cache_ready"])
            self.assertEqual(adapter._recent_statuses()[("station", "1")]["stat"], "2")
            self.assertEqual(load.call_count, 3)

    def test_ft07_401_403_nonretryable_and_masked(self):
        with patch.dict("os.environ", {"KECO_SERVICE_KEY": "secret-ft07-never-print"}):
            adapter = EnvironmentChargerAdapter()
        for status in (401, 403):
            with self.subTest(status=status), patch("app.providers.urlopen", side_effect=http_error(status)):
                with self.assertRaises(ProviderError) as caught:
                    adapter._get_page("getChargerInfo", page_no=1, num_rows=1, extra={})
                self.assertFalse(caught.exception.retryable)
                self.assertNotIn("secret-ft07-never-print", str(caught.exception))
                self.assertIn("인증", caught.exception.user_message)

    def test_ft07_unauthorized_provider_no_auto_retry(self):
        with patch.object(orchestrator.executor, "execute", side_effect=ProviderError("KECO", "인증을 확인해 주세요.", retryable=False)) as execute:
            payload = self.search()
        self.assertEqual(execute.call_count, 1)
        self.assertEqual(payload["status"], "degraded")
        self.assertEqual(len(orchestrator.memory.handoffs[payload["request_id"]]["retry_history"]), 0)
        self.assertEqual(payload["critic_decision"], "SAFE_UNAVAILABLE")

    def test_ft08_stale_invalid_count_and_missing_timestamp(self):
        request = SearchRequest(
            request_id="ft08-fixture", origin=SearchOrigin.SIDEBAR, requested_at=kst_now(),
            user_confirmed=True, center=Point(lat=37.498, lng=127.027),
            radius_km=0.5, connector_types=[ConnectorType.FAST], region_filters=[]
        )
        for scenario, expected in (("stale", "DELAYED"), ("invalid_count", "UNAVAILABLE")):
            with self.subTest(scenario=scenario):
                orchestrator.test_scenarios.activate(scenario)
                results = orchestrator.test_scenarios.execute_fixture(request)
                decision, findings, status = Critic().review(results)
                self.assertEqual((decision, status), ("SAFE_UNAVAILABLE", "degraded"))
                self.assertEqual(results[0].availability.state.value, expected)
                self.assertIsNone(results[0].availability.available_chargers)
                self.assertTrue(findings)
        orchestrator.test_scenarios.activate("normal")
        results = orchestrator.test_scenarios.execute_fixture(request)
        results[0].reported_at = None
        decision, findings, status = Critic().review(results)
        self.assertEqual((decision, status), ("SAFE_UNAVAILABLE", "degraded"))
        self.assertEqual(results[0].availability.state.value, "UNAVAILABLE")
        self.assertIsNone(results[0].availability.total_chargers)
        self.assertTrue(any("갱신 시각" in finding for finding in findings))


if __name__ == "__main__":
    unittest.main()
