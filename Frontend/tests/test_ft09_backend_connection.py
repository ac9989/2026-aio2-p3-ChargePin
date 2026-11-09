"""FT-09 isolated Frontend -> Backend connection failure and recovery."""
from __future__ import annotations

import unittest
from unittest.mock import Mock, patch

import requests

from api_client import ApiError, ChargePinApi


class BackendConnectionRecoveryTests(unittest.TestCase):
    def test_ft09_connection_refused_then_health_recovers(self):
        events = []
        client = ChargePinApi(observer=events.append)
        good = Mock()
        good.ok = True
        good.status_code = 200
        good.json.return_value = {"status": "ok", "service": "chargepin-backend"}

        with patch("api_client.requests.request", side_effect=[
            requests.ConnectionError("internal_secret_never_expose"),
            good,
        ]) as request:
            with self.assertRaises(ApiError) as context:
                client.health()
            self.assertIn("백엔드에 연결하지 못했습니다", context.exception.message)
            self.assertNotIn("internal_secret_never_expose", context.exception.message)
            result = client.health()
        self.assertEqual(result["status"], "ok")
        self.assertEqual(request.call_count, 2)
        self.assertEqual(events[0]["outcome"], "error")
        self.assertEqual(events[1]["outcome"], "success")
        self.assertNotIn("internal_secret_never_expose", str(events))

    def test_ft09_timeout_then_health_recovers(self):
        client = ChargePinApi()
        good = Mock(ok=True, status_code=200)
        good.json.return_value = {"status": "ok"}
        with patch("api_client.requests.request", side_effect=[
            requests.Timeout("timeout secret_not_for_users"),
            good,
        ]) as request:
            with self.assertRaises(ApiError) as context:
                client.health()
            self.assertIn("백엔드에 연결하지 못했습니다", context.exception.message)
            self.assertNotIn("secret_not_for_users", context.exception.message)
            self.assertEqual(client.health()["status"], "ok")
        self.assertEqual(request.call_count, 2)


if __name__ == "__main__":
    unittest.main()
