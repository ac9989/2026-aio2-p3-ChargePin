"""Offline isolated tests for the external recovery gateway; no live providers."""
import importlib.util
import json
from pathlib import Path
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.request import Request, urlopen

FILE = Path(__file__).resolve().parents[2] / "ops" / "external_recovery_gateway.py"
spec = importlib.util.spec_from_file_location("recovery_gateway", FILE)
gateway = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gateway)


class FakeBackend(BaseHTTPRequestHandler):
    counts = {}
    persistent = False
    def log_message(self, *args): pass
    def do_POST(self):
        key = self.path.split("/")[-1]
        self.__class__.counts[key] = self.__class__.counts.get(key, 0) + 1
        n = self.__class__.counts[key]
        if key == "search":
            data = ({"status": "degraded", "critic_decision": "SAFE_UNAVAILABLE",
                     "critic_findings": [gateway.EXECUTOR_ERROR]} if n == 1
                    else {"status": "completed", "critic_decision": "PASS", "results": [1]})
        elif key == "plan":
            data = ({"status": "NEEDS_INPUT", "message": gateway.PLANNER_ERROR}
                    if n == 1 or self.__class__.persistent else
                    {"status": "AWAITING_CONFIRMATION", "message": "ok"})
        elif key == "missing":
            data = {"status": "NEEDS_INPUT", "message": "검색할 장소명을 알려 주세요."}
        else:
            data = {"status": "degraded", "critic_decision": "SAFE_UNAVAILABLE",
                    "critic_findings": ["정보 지연"]}
        raw = json.dumps(data, ensure_ascii=False).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)


class GatewayTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.backend = ThreadingHTTPServer(("127.0.0.1", 0), FakeBackend)
        cls.backend_thread = threading.Thread(target=cls.backend.serve_forever, daemon=True)
        cls.backend_thread.start()
        cls.proxy = gateway.ProxyServer(("127.0.0.1", 0), gateway.ProxyHandler,
                                         upstream=f"http://127.0.0.1:{cls.backend.server_port}",
                                         retries=2, delay=0)
        cls.proxy_thread = threading.Thread(target=cls.proxy.serve_forever, daemon=True)
        cls.proxy_thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.proxy.shutdown()
        cls.proxy.server_close()
        cls.backend.shutdown()
        cls.backend.server_close()

    def setUp(self):
        FakeBackend.counts.clear()
        FakeBackend.persistent = False

    def post(self, endpoint):
        request = Request(f"http://127.0.0.1:{self.proxy.server_port}/api/v1/{endpoint}",
                          data=b"{}", method="POST",
                          headers={"Authorization": "Bearer test", "Content-Type": "application/json"})
        with urlopen(request, timeout=5) as res:
            return json.load(res)

    def test_ft02_transient_recovers(self):
        self.assertEqual("completed", self.post("search")["status"])
        self.assertEqual(2, FakeBackend.counts["search"])

    def test_ft04_transient_recovers(self):
        self.assertEqual("AWAITING_CONFIRMATION", self.post("chat/plan")["status"])
        self.assertEqual(2, FakeBackend.counts["plan"])

    def test_real_need_input_not_retried(self):
        self.assertEqual("NEEDS_INPUT", self.post("missing")["status"])
        self.assertEqual(1, FakeBackend.counts["missing"])

    def test_quality_downgrade_not_retried(self):
        self.assertEqual("degraded", self.post("quality")["status"])
        self.assertEqual(1, FakeBackend.counts["quality"])

    def test_persistent_failure_is_bounded(self):
        FakeBackend.persistent = True
        self.assertEqual("NEEDS_INPUT", self.post("chat/plan")["status"])
        self.assertEqual(3, FakeBackend.counts["plan"])


if __name__ == "__main__":
    unittest.main()
