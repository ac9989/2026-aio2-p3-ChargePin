"""Tests for trustworthy dashboard data and map presentation."""
from datetime import datetime, timezone
import os
import unittest
from unittest.mock import patch
from api_client import ChargePinApi

from dashboard_data import allowed_demo_role_transitions, can_manage_roles, can_view_dashboard, event_kind, summarize_events
from map_view import build_map_html


class RoleTests(unittest.TestCase):
    def test_role_access_is_explicit_and_unknown_roles_are_rejected(self):
        for role in ("일반 이용자", "손님", None, "알 수 없는 역할"):
            self.assertFalse(can_view_dashboard(role))
            self.assertFalse(can_manage_roles(role))
        self.assertTrue(can_view_dashboard("하급 관리자"))
        self.assertFalse(can_manage_roles("하급 관리자"))
        self.assertTrue(can_view_dashboard("상급 관리자"))
        self.assertTrue(can_manage_roles("상급 관리자"))

    def test_demo_transitions_enforce_prd_and_cannot_change_self(self):
        self.assertEqual(allowed_demo_role_transitions("상급 관리자", "일반 이용자"),
                         ["하급 관리자", "상급 관리자"])
        self.assertEqual(allowed_demo_role_transitions("상급 관리자", "하급 관리자"), ["일반 이용자"])
        self.assertEqual(allowed_demo_role_transitions("상급 관리자", "상급 관리자"), [])
        self.assertEqual(allowed_demo_role_transitions("상급 관리자", "하급 관리자", is_self=True), [])
        self.assertEqual(allowed_demo_role_transitions("하급 관리자", "일반 이용자"), [])


class DashboardDataTests(unittest.TestCase):
    def test_searches_are_not_double_counted_with_chat_planning(self):
        events = [
            {"path": "/chat/plan", "outcome": "success", "observed_at": "2026-11-06T00:01:10Z", "elapsed_ms": 20},
            {"path": "/search/abc/confirm", "outcome": "success", "search_status": "degraded",
             "observed_at": "2026-11-06T00:01:20Z", "elapsed_ms": 120},
            {"path": "/search", "outcome": "error", "observed_at": "2026-11-06T00:02:00Z", "elapsed_ms": 80},
            {"path": "/healthz", "outcome": "success", "observed_at": "2026-11-06T00:02:10Z"},
        ]
        result = summarize_events(events)
        self.assertEqual(result["search_count"], 2)
        self.assertEqual(result["partial_count"], 1)
        self.assertEqual(result["failure_count"], 1)
        self.assertEqual(result["average_ms"], 100)
        self.assertEqual(sum(row["count"] for row in result["minute_counts"]), 2)
        self.assertEqual({row["kind"] for row in result["kind_counts"]}, {"챗 해석", "챗 검색", "직접 검색"})

    def test_missing_times_and_unrelated_paths_do_not_generate_metrics(self):
        result = summarize_events([
            {"path": "/search", "outcome": "success", "observed_at": "invalid"},
            {"path": "/auth/login", "outcome": "success", "observed_at": "2026-11-06T00:00:00Z"},
        ])
        self.assertEqual(result["search_count"], 0)
        self.assertIsNone(result["average_ms"])
        self.assertEqual(result["minute_counts"], [])
        self.assertIsNone(event_kind("/search/abc/not-confirm"))

    def test_history_is_limited_to_last_hundred_events(self):
        events = [{"path": "/search", "outcome": "success", "observed_at": "2026-11-06T00:00:00Z"}
                  for _ in range(105)]
        self.assertEqual(summarize_events(events)["search_count"], 100)

    def test_guardrail_block_is_separately_counted(self):
        result = summarize_events([
            {"path": "/chat/plan", "outcome": "success", "guardrail_blocked": True,
             "observed_at": "2026-11-06T00:00:00Z", "elapsed_ms": 8},
        ])
        self.assertEqual(result["guardrail_block_count"], 1)
        self.assertEqual(result["search_count"], 0)
        self.assertEqual(result["observed"][0]["state"], "차단")


class RequestTelemetryTests(unittest.TestCase):
    def test_search_request_id_is_recorded_without_credentials_or_input(self):
        events = []
        api = ChargePinApi(observer=events.append)
        response = {"request_id": "req-123", "status": "completed", "results": [], "applied_request": {}}
        with patch.object(api, "_perform_request", return_value=response):
            api._request("POST", "/search", access_token="private-token", json={"query": "private query"})
        self.assertEqual(events[0]["request_id"], "req-123")
        self.assertNotIn("private-token", str(events))
        self.assertNotIn("private query", str(events))
        summarized = summarize_events(events)
        self.assertEqual(summarized["observed"][0]["request_id"], "req-123")

    def test_untrusted_request_id_is_ignored(self):
        events = []
        api = ChargePinApi(observer=events.append)
        with patch.object(api, "_perform_request", return_value={"request_id": "<script>"}):
            api._request("POST", "/chat/plan", access_token="secret")
        self.assertNotIn("request_id", events[0])

    def test_blocked_chat_plan_is_recorded_without_place_lookup(self):
        events = []
        api = ChargePinApi(observer=events.append)
        with patch.object(api, "_perform_request", return_value={"request_id": "req-guard", "status": "BLOCKED"}):
            api._request("POST", "/chat/plan", access_token="secret")
        self.assertTrue(events[0]["guardrail_blocked"])
        self.assertNotIn("place_lookup", events[0])


class MapViewTests(unittest.TestCase):
    def test_no_key_shows_connection_state_without_fake_markers(self):
        with patch.dict(os.environ, {"KAKAO_JAVASCRIPT_KEY": ""}):
            html = build_map_html([{"name": "test", "location": {"lat": 37.5, "lng": 127.0}}],
                                  None, None, lambda station: "확인 필요")
        self.assertIn("지도 연결", html)
        self.assertNotIn('stations=', html)

    def test_result_text_is_escaped_and_script_context_is_safe(self):
        station = {"name": "</script><script>alert(1)</script>", "facility_id": "1",
                   "location": {"lat": 37.5, "lng": 127.0}, "connector_types": ["FAST"],
                   "address": "<b>address</b>"}
        with patch.dict(os.environ, {"KAKAO_JAVASCRIPT_KEY": "example-key"}):
            html = build_map_html([station], {"center": {"lat": 37.5, "lng": 127.0},
                                              "radius_km": 0.5, "connector_types": ["FAST"]},
                                  "1", lambda item: "충전 가능")
        self.assertNotIn("</script><script>alert", html)
        self.assertIn("&lt;b&gt;address&lt;/b&gt;", html)
        self.assertIn("반경 0.5 km", html)
        self.assertIn('"selected": true', html)


if __name__ == "__main__":
    unittest.main()
