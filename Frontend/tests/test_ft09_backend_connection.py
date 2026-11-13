"""FT-09 isolated Frontend -> Backend connection failure and recovery."""
from __future__ import annotations

import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread
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

    def test_ft09_real_loopback_connection_down_then_up(self):
        """Use a real localhost TCP connection; never contact EC2 or provider APIs."""
        class HealthHandler(BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(b'{"status":"ok","service":"chargepin-backend"}')

            def log_message(self, format, *args):
                pass

        # Reserve a localhost port, release it to force a true connection refusal,
        # then start the isolated mock health service on that same port.
        reservation = HTTPServer(("127.0.0.1", 0), HealthHandler)
        port = reservation.server_address[1]
        reservation.server_close()
        client = ChargePinApi()
        client.service_url = f"http://127.0.0.1:{port}"
        client.base_url = client.service_url + "/api/v1"
        with self.assertRaises(ApiError) as context:
            client.health()
        self.assertIn("백엔드에 연결하지 못했습니다", context.exception.message)

        server = HTTPServer(("127.0.0.1", port), HealthHandler)
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            self.assertEqual(client.health()["status"], "ok")
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=3)

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
