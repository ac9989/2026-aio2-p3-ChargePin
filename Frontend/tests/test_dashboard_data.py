"""Tests for trustworthy dashboard data and map presentation."""
from datetime import datetime, timezone
import os
import unittest
from unittest.mock import patch
from api_client import ChargePinApi

from dashboard_data import (action_items, allowed_demo_role_transitions, can_export_report, can_manage_roles,
                            can_view_dashboard, compliance_score, error_class, evaluate_compliance, event_kind,
                            guardrail_summary, health_label, load_compliance_reference, summarize_events)
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


class GuardrailComplianceTests(unittest.TestCase):
    def test_errors_are_split_into_request_server_and_transport(self):
        self.assertEqual(error_class({"outcome": "error", "status_code": 403}), "요청 측 4xx")
        self.assertEqual(error_class({"outcome": "error", "status_code": 503}), "서버 측 5xx")
        self.assertEqual(error_class({"outcome": "error", "status_code": None}), "연결 실패")
        self.assertIsNone(error_class({"outcome": "success", "status_code": 500}))

    def test_guardrail_counts_passes_as_well_as_blocks(self):
        events = [
            {"path": "/chat/plan", "outcome": "success", "plan_status": "BLOCKED", "observed_at": "2026-11-08T00:00:00Z"},
            {"path": "/chat/plan", "outcome": "success", "plan_status": "AWAITING_CONFIRMATION", "observed_at": "2026-11-08T00:00:01Z"},
            {"path": "/search/a/confirm", "outcome": "success", "search_status": "degraded",
             "critic_decision": "SAFE_UNAVAILABLE", "critic_finding_count": 2,
             "availability_counts": {"DELAYED": 2, "AVAILABLE": 1, "FAKE": 9}, "observed_at": "2026-11-08T00:00:02Z"},
            {"path": "/search", "outcome": "error", "status_code": 403, "observed_at": "2026-11-08T00:00:03Z"},
        ]
        data = summarize_events(events)
        guard = guardrail_summary(data)
        self.assertEqual((guard["input_checked"], guard["input_blocked"], guard["input_passed"]), (2, 1, 1))
        self.assertEqual((guard["output_checked"], guard["output_safe"], guard["output_pass"]), (1, 1, 0))
        self.assertEqual(guard["access_denied"], 1)
        self.assertEqual(guard["finding_count"], 2)
        self.assertEqual({row["kind"]: row["count"] for row in data["availability_counts"]},
                         {"충전 가능": 1, "정보 지연": 2})
        self.assertEqual(data["server_error_count"], 0)
        self.assertEqual(data["observed"][0]["state"], "차단")

    def test_health_mapping_never_upgrades_unknown_replies(self):
        self.assertEqual(health_label({"status": "ok"}, True), "정상")
        self.assertEqual(health_label({"status": "degraded"}, True), "저하")
        self.assertEqual(health_label({"status": "maybe"}, True), "확인 필요")
        self.assertEqual(health_label(None, False), "중단")

    def test_live_signals_only_promote_implemented_controls(self):
        reference = {"items": [
            {"id": "X-1", "status": "구현", "live": "health"},
            {"id": "X-2", "status": "부분", "live": "health"},
            {"id": "X-3", "status": "미착수", "live": "ci_tests"},
            {"id": "X-4", "status": "구현", "live": "guardrail_session"},
        ]}
        items = {item["id"]: item for item in evaluate_compliance(reference, {"health": "정상", "ci_tests": "성공"})}
        self.assertEqual(items["X-1"]["status"], "충족")
        self.assertEqual(items["X-2"]["status"], "부분")
        self.assertTrue(items["X-2"]["live_note"])
        self.assertEqual(items["X-3"]["status"], "미착수")
        self.assertEqual(items["X-4"]["status"], "구현")

    def test_bundled_report_is_valid_and_actions_put_live_failures_first(self):
        reference = load_compliance_reference()
        ids = [item["id"] for item in reference["items"]]
        self.assertEqual(len(ids), len(set(ids)))
        items = evaluate_compliance(reference, {})
        self.assertEqual(compliance_score(items)["total"], len(ids))
        data = summarize_events([{"path": "/search", "outcome": "error", "status_code": 502,
                                  "observed_at": "2026-11-08T00:00:00Z"}])
        actions = action_items(items, data, "중단")
        self.assertEqual([item["ref"] for item in actions[:2]], ["R-3", "R-4"])
        self.assertTrue(can_export_report("상급 관리자"))
        self.assertFalse(can_export_report("하급 관리자"))

    def test_search_verdicts_are_counted_without_copying_text(self):
        events = []
        api = ChargePinApi(observer=events.append)
        response = {"request_id": "req-9", "status": "degraded", "applied_request": {},
                    "critic_decision": "SAFE_UNAVAILABLE", "critic_findings": ["private finding text"],
                    "results": [{"availability": {"state": "DELAYED"}}, {"availability": {"state": "AVAILABLE"}}]}
        with patch.object(api, "_perform_request", return_value=response):
            api._request("POST", "/search", access_token="token")
        self.assertEqual(events[0]["critic_decision"], "SAFE_UNAVAILABLE")
        self.assertEqual(events[0]["critic_finding_count"], 1)
        self.assertEqual(events[0]["availability_counts"], {"DELAYED": 1, "AVAILABLE": 1})
        self.assertNotIn("private finding text", str(events))


if __name__ == "__main__":
    unittest.main()
