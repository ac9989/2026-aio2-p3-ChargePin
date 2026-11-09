"""Real Chromium/Streamlit browser smoke against a local fake API.

No cloud requests, no real provider credentials, no deployment changes.
This checks Streamlit interactions, not an end-to-end production Backend.
"""
from __future__ import annotations

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread, Lock
import json
import os
import re
import socket
import subprocess
import sys
import time

from playwright.sync_api import sync_playwright, expect


ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = Path(os.environ.get("BROWSER_ARTIFACT_DIR", "/tmp/chargepin-browser"))
ARTIFACTS.mkdir(parents=True, exist_ok=True)
calls: list[dict] = []
calls_lock = Lock()
CANDIDATES = [
    {"candidate_id": "station-one", "name": "첫 번째 장소", "category": "지하철역",
     "address": "서울 강남구", "location": {"lat": 37.498, "lng": 127.027}, "district_code": "11680"},
    {"candidate_id": "station-two", "name": "두 번째 장소", "category": "공공기관",
     "address": "서울 중구", "location": {"lat": 37.5665, "lng": 126.978}, "district_code": "11140"},
]


def response_payload(candidate=None, origin="initial_default"):
    place = candidate or CANDIDATES[0]
    return {
        "request_id": "smoke-request", "status": "completed",
        "critic_decision": "PASS", "critic_findings": [],
        "results": [],
        "applied_request": {
            "request_id": "smoke-request", "origin": origin,
            "requested_at": "2026-11-09T09:00:00+09:00", "user_confirmed": True,
            "center": place["location"], "radius_km": 0.5,
            "connector_types": ["FAST", "SLOW"], "region_filters": [],
        },
    }


class Handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def send_json(self, status, data):
        encoded = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def do_GET(self):
        if self.path == "/healthz":
            return self.send_json(200, {"status": "ok", "service": "chargepin-backend"})
        if self.path == "/api/v1/ops/summary":
            return self.send_json(200, {"scope": "backend_process", "metrics": {},
                "recent_events": [{"event_type": "search", "status": "degraded",
                                   "request_id": "recover-me"}], "providers": []})
        if self.path == "/api/v1/ops/platform":
            return self.send_json(200, {})
        if self.path == "/api/v1/ops/healing":
            return self.send_json(200, {})
        return self.send_json(404, {"detail": "local mock only"})

    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0"))
        payload = json.loads(self.rfile.read(length) or b"{}")
        with calls_lock:
            calls.append({"path": self.path, "body": payload,
                          "authorization": bool(self.headers.get("Authorization"))})
        if self.path == "/api/v1/auth/login":
            role = "SENIOR_ADMIN" if payload.get("service_key") == "admin-local" else "GUEST"
            return self.send_json(200, {"access_token": "mock-access-token",
                "token_type": "bearer", "role": role, "expires_at": "2099-01-01T00:00:00+00:00"})
        if self.path == "/api/v1/search/default":
            return self.send_json(200, response_payload())
        if self.path == "/api/v1/chat/plan":
            return self.send_json(200, {"request_id": "pending-one",
                "status": "AWAITING_LOCATION_CONFIRMATION", "candidates": CANDIDATES,
                "suggested_candidate_id": "station-one",
                "message": "검색할 장소를 확인해 주세요."})
        if self.path == "/api/v1/search/pending-one/confirm":
            chosen = next((c for c in CANDIDATES if c["candidate_id"] == payload.get("candidate_id")), None)
            return self.send_json(200, response_payload(chosen, origin="chat"))
        if self.path == "/api/v1/ops/requests/recover-me/retry":
            return self.send_json(200, response_payload())
        if self.path == "/api/v1/ops/cache/refresh":
            return self.send_json(200, {"ok": True})
        return self.send_json(404, {"detail": self.path})


def get_calls(path):
    with calls_lock:
        return [event for event in calls if event["path"] == path]


def wait_port(port, timeout=35):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with socket.create_connection(("127.0.0.1", port), 1):
                return
        except OSError:
            time.sleep(0.2)
    raise RuntimeError(f"Streamlit failed to open port {port}")


def login(page, key):
    page.goto("http://127.0.0.1:8508", wait_until="domcontentloaded")
    field = page.locator('input[type="password"]')
    expect(field).to_be_visible(timeout=35000)
    field.fill(key)
    page.get_by_role("button", name="접속하기").click()
    expect(page.get_by_role("button", name="로그아웃")).to_be_visible(timeout=35000)


def run_checks():
    server = ThreadingHTTPServer(("127.0.0.1", 8768), Handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    env = os.environ.copy()
    env.update(CHARGEPIN_API_BASE_URL="http://127.0.0.1:8768/api/v1",
               CHARGEPIN_DASHBOARD_SERVER_OPS="true", CHARGEPIN_ENABLE_FAULT_INJECTION="false",
               STREAMLIT_BROWSER_GATHER_USAGE_STATS="false")
    stdout_file = (ARTIFACTS / "streamlit.log").open("w")
    proc = subprocess.Popen([sys.executable, "-m", "streamlit", "run", "app.py",
                             "--server.address", "127.0.0.1", "--server.port", "8508",
                             "--server.headless", "true", "--browser.gatherUsageStats", "false"],
                            cwd=ROOT, env=env, stdout=stdout_file, stderr=subprocess.STDOUT)
    try:
        wait_port(8508)
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True, args=["--no-sandbox"])
            context = browser.new_context(viewport={"width": 1440, "height": 1000})
            page = context.new_page()
            page.set_default_timeout(25000)
            try:
                login(page, "guest-local")
                expect(page.get_by_text("주변 충전소", exact=False).first).to_be_visible()
                assert len(get_calls("/api/v1/search/default")) == 1, "DP-02-01: default search not called once"
                print("DP-02-01 PASS: login triggered exactly one default search", flush=True)

                # Chat plan must only create a pending selection, not execute a search.
                chat = page.get_by_placeholder("강남역처럼 장소만 입력해도 가능해요")
                expect(chat).to_be_visible()
                chat.fill("서울")
                chat.press("Enter")
                expect(page.get_by_text("두 번째 장소", exact=False).first).to_be_visible()
                assert not get_calls("/api/v1/search/pending-one/confirm"), (
                    "LLM-05: search started before confirmation")
                page.get_by_text("두 번째 장소", exact=False).first.click()
                page.get_by_role("button", name="선택한 장소로 검색").click()
                deadline = time.monotonic() + 15
                while time.monotonic() < deadline and not get_calls("/api/v1/search/pending-one/confirm"):
                    time.sleep(0.2)
                confirmed = get_calls("/api/v1/search/pending-one/confirm")
                assert len(confirmed) == 1 and confirmed[0]["body"]["candidate_id"] == "station-two", (
                    f"LLM-05: expected second chosen candidate: {confirmed}")
                print("DP-02-03/LLM-05-01~03 PASS: manual second-candidate confirmation", flush=True)
                page.screenshot(path=str(ARTIFACTS / "guest-after-chat.png"), full_page=True)
                context.close()

                admin_context = browser.new_context(viewport={"width": 1440, "height": 1000})
                admin = admin_context.new_page()
                admin.set_default_timeout(25000)
                login(admin, "admin-local")
                admin.get_by_role("button", name="운영 대시보드").click()
                expect(admin.get_by_text("재처리할 불완전 검색 요청")).to_be_visible(timeout=30000)
                admin.get_by_role("button", name="선택 요청 재처리").click()
                deadline = time.monotonic() + 15
                while time.monotonic() < deadline and not get_calls("/api/v1/ops/requests/recover-me/retry"):
                    time.sleep(0.2)
                calls_retry = get_calls("/api/v1/ops/requests/recover-me/retry")
                assert len(calls_retry) == 1 and calls_retry[0]["authorization"], "OP-02: missing authorization"
                print("OP-02-01~03 PASS: admin retry called with session access token", flush=True)
                admin.screenshot(path=str(ARTIFACTS / "admin-after-retry.png"), full_page=True)
                admin_context.close()
            except Exception:
                page.screenshot(path=str(ARTIFACTS / "browser-failure.png"), full_page=True)
                raise
            finally:
                browser.close()
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
        stdout_file.close()
        server.shutdown()
        server.server_close()
        (ARTIFACTS / "mock-api-calls.json").write_text(
            json.dumps(calls, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    run_checks()
