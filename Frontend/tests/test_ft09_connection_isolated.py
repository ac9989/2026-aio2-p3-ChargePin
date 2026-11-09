"""FT-09 simulated Backend unavailability: safe Frontend API error, no live server."""
import unittest
from unittest.mock import patch

import requests

from api_client import ApiError, ChargePinApi


class BackendConnectionFailureTests(unittest.TestCase):
    def test_ft09_connection_refused_returns_safe_error(self):
        observed = []
        api = ChargePinApi(observer=observed.append)
        with patch("api_client.requests.request", side_effect=requests.ConnectionError("test-only connection refused")) as mock_request:
            with self.assertRaises(ApiError) as outcome:
                api.health()
        self.assertIn("백엔드에 연결하지 못했습니다", outcome.exception.message)
        self.assertNotIn("test-only connection refused", outcome.exception.message)
        self.assertIsNone(outcome.exception.status_code)
        self.assertEqual(mock_request.call_count, 1)
        self.assertEqual(observed[0]["outcome"], "error")

    def test_ft09_backend_recovery_next_request_succeeds(self):
        api = ChargePinApi()
        response = unittest.mock.Mock()
        response.ok = True
        response.json.return_value = {"status": "ok", "service": "chargepin-backend"}
        with patch("api_client.requests.request", side_effect=[
            requests.ConnectionError("offline"), response
        ]) as mock_request:
            with self.assertRaises(ApiError):
                api.health()
            result = api.health()
        self.assertEqual(mock_request.call_count, 2)
        self.assertEqual(result["status"], "ok")


if __name__ == "__main__":
    unittest.main()
