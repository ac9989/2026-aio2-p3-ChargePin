"""Isolated extensions FT-05 through FT-08: no live provider calls or credentials."""
import unittest
from datetime import datetime, timedelta, timezone
from urllib.error import HTTPError
from unittest.mock import patch

from app.agents import SearchOrchestrator
from app.models import AvailabilityState, ConnectorType, Point, SearchInput
from app.providers import EnvironmentChargerAdapter, ProviderError, kst_now


class ExtendedFaultIsolationTests(unittest.TestCase):
    def setUp(self):
        self.service = SearchOrchestrator()
        self.request = SearchInput(center=Point(lat=37.498, lng=127.027),
                                   radius_km=0.5, connector_types=[ConnectorType.FAST])
        # Never reach external KECO or Kakao services.
        self.service.executor._chargers.nearby = lambda _request: []

    def test_ft05_http_429_maps_to_retryable_provider_error(self):
        adapter = EnvironmentChargerAdapter()
        adapter._service_key = "dummy-local-only"
        error = HTTPError("https://example.invalid", 429, "Too Many Requests", {}, None)
        with patch("app.providers.urlopen", side_effect=error):
            with self.assertRaises(ProviderError) as outcome:
                adapter._get_page("getChargerInfo", page_no=1, num_rows=1, extra={})
        self.assertEqual(outcome.exception.provider, "KECO")
        self.assertTrue(outcome.exception.retryable)
        self.assertIn("제한", outcome.exception.user_message)

    def test_ft05_persistent_rate_limit_stops_after_two_retries(self):
        calls = [0]
        def rejected(_request):
            calls[0] += 1
            raise ProviderError("KECO", "API 요청 제한", retryable=True)
        self.service.executor.execute = rejected
        with patch("app.agents.sleep"):
            response = self.service.direct_search(self.request, "GUEST")
        self.assertEqual(calls[0], 3)  # initial + at most two retries
        self.assertEqual(response.status, "degraded")
        self.assertEqual(response.critic_decision, "SAFE_UNAVAILABLE")
        self.assertEqual(len(self.service.memory.handoffs[response.request_id]["retry_history"]), 2)

    def test_ft06_info_cache_hit_expiry_and_manual_clear(self):
        adapter = EnvironmentChargerAdapter()
        calls = []
        def fake_pages(operation, filters):
            calls.append((operation, dict(filters)))
            return [{"test_record": len(calls)}]
        adapter._all_pages = fake_pages
        base = datetime(2026, 11, 9, tzinfo=timezone.utc)
        with patch("app.providers.kst_now", return_value=base):
            first = adapter._info(None)
            second = adapter._info(None)
        self.assertEqual(first, second)
        self.assertEqual(len(calls), 1)
        self.assertEqual(adapter.cache_snapshot()["info_cache_entries"], 1)
        with patch("app.providers.kst_now", return_value=base + timedelta(seconds=601)):
            refreshed = adapter._info(None)
        self.assertEqual(len(calls), 2)
        self.assertNotEqual(first, refreshed)
        adapter.clear_cache()
        self.assertEqual(adapter.cache_snapshot()["info_cache_entries"], 0)
        with patch("app.providers.kst_now", return_value=base + timedelta(seconds=602)):
            adapter._info(None)
        self.assertEqual(len(calls), 3)

    def test_ft07_401_and_403_are_nonretryable_sanitized(self):
        adapter = EnvironmentChargerAdapter()
        adapter._service_key = "very-secret-placeholder"
        for code in (401, 403):
            with self.subTest(http_code=code):
                error = HTTPError("https://example.invalid", code, "Denied", {}, None)
                with patch("app.providers.urlopen", side_effect=error):
                    with self.assertRaises(ProviderError) as outcome:
                        adapter._get_page("getChargerInfo", page_no=1, num_rows=1, extra={})
                self.assertEqual(outcome.exception.provider, "KECO")
                self.assertFalse(outcome.exception.retryable)
                self.assertIn("인증", outcome.exception.user_message)
                self.assertNotIn("very-secret-placeholder", str(outcome.exception))

    def test_ft07_nonretryable_auth_error_has_no_automatic_retry(self):
        calls = [0]
        def denied(_request):
            calls[0] += 1
            raise ProviderError("KECO", "인증 또는 활용 신청 상태를 확인해 주세요.", retryable=False)
        self.service.executor.execute = denied
        with patch("app.agents.sleep"):
            response = self.service.direct_search(self.request, "GUEST")
        self.assertEqual(calls[0], 1)
        self.assertEqual(response.status, "degraded")
        self.assertEqual(len(self.service.memory.handoffs[response.request_id]["retry_history"]), 0)

    def test_ft08_missing_charger_update_timestamp_is_marked_unknown(self):
        now = kst_now()
        self.service.executor._chargers.nearby = lambda _request: [{
            "stat_id": "ft08", "name": "테스트 충전소", "address": "서울특별시 강남구 테스트로 1",
            "lat": 37.498, "lng": 127.027, "kind": "시설 유형 확인 필요",
            "use_time": None, "parking_free": None, "restriction_detail": None,
            "distance_km": 0.1, "fetched_at": now,
            "chargers": [("01", ConnectorType.FAST, "2", None)],
        }]
        response = self.service.direct_search(self.request, "GUEST")
        self.assertEqual(response.status, "degraded")
        self.assertEqual(response.critic_decision, "SAFE_UNAVAILABLE")
        self.assertEqual(response.results[0].availability.state, AvailabilityState.UNAVAILABLE)
        self.assertIn("갱신 시각", response.results[0].availability.label)

    def test_ft08_no_charger_entries_cannot_be_reported_available(self):
        now = kst_now()
        self.service.executor._chargers.nearby = lambda _request: [{
            "stat_id": "ft08-empty", "name": "테스트 충전소", "address": "서울특별시 강남구 테스트로 1",
            "lat": 37.498, "lng": 127.027, "kind": "시설 유형 확인 필요",
            "use_time": None, "parking_free": None, "restriction_detail": None,
            "distance_km": 0.1, "fetched_at": now, "chargers": [],
        }]
        response = self.service.direct_search(self.request, "GUEST")
        self.assertEqual(response.status, "degraded")
        self.assertEqual(response.critic_decision, "SAFE_UNAVAILABLE")
        self.assertEqual(response.results[0].availability.state, AvailabilityState.UNAVAILABLE)


if __name__ == "__main__":
    unittest.main()
