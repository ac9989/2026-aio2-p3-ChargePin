#!/usr/bin/env python3
"""Separate response-aware ChargePin retry gateway; no Backend code changes."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import logging
import re
from time import monotonic, sleep
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

EXECUTOR_ERROR = "검색 처리 중 오류가 발생했습니다. 잠시 후 다시 시도해 주세요."
PLANNER_ERROR = "AI 자연어 해석 연결이 일시적으로 원활하지 않습니다. 잠시 후 다시 입력해 주세요."
HOP = {"connection", "keep-alive", "proxy-authenticate", "proxy-authorization", "te", "trailers", "transfer-encoding", "upgrade"}


def recovery_kind(path: str, status: int, raw: bytes) -> str | None:
    if status != 200:
        return None
    is_search = bool(path in ("/api/v1/search", "/api/v1/search/default")
                     or re.fullmatch(r"/api/v1/search/[0-9a-fA-F-]{36}/confirm", path))
    if not is_search and path != "/api/v1/chat/plan":
        return None
    try:
        data = json.loads(raw)
    except (ValueError, UnicodeDecodeError):
        return None
    if not isinstance(data, dict):
        return None
    if is_search:
        if (data.get("status") == "degraded" and data.get("critic_decision") == "SAFE_UNAVAILABLE"
                and isinstance(data.get("critic_findings"), list)
                and EXECUTOR_ERROR in data["critic_findings"]):
            return "FT-02"
    if path == "/api/v1/chat/plan":
        if data.get("status") == "NEEDS_INPUT" and data.get("message") == PLANNER_ERROR:
            return "FT-04-like"
    return None


class ProxyServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, address, handler, *, upstream: str, retries: int, delay: float):
        super().__init__(address, handler)
        self.upstream = upstream.rstrip("/")
        self.retries = retries
        self.delay = delay


class ProxyHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt: str, *args):
        return  # Never write credentials, user input or request paths to access logs.

    def do_GET(self):
        self._proxy()

    def do_POST(self):
        self._proxy()

    def _emit(self, code: int, headers: dict, body: bytes):
        self.send_response(code)
        for key, value in headers.items():
            if key.lower() not in HOP | {"content-length", "server", "date", "content-encoding"}:
                self.send_header(key, value)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Connection", "close")
        self.end_headers()
        try:
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            pass
        self.close_connection = True

    def _proxy(self):
        path = urlsplit(self.path).path
        if path == "/healthz":
            self._emit(200, {"Content-Type": "application/json"}, b'{"status":"ok","service":"chargepin-recovery-proxy"}')
            return
        if not path.startswith("/api/v1/"):
            self._emit(404, {"Content-Type": "application/json"}, b'{"detail":"Not Found"}')
            return
        if self.headers.get("Transfer-Encoding"):
            self._emit(400, {}, b"")
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length < 0 or length > 65536:
                raise ValueError
        except ValueError:
            self._emit(413, {}, b"")
            return
        body = self.rfile.read(length) if length else None
        headers = {key: self.headers[key] for key in ("Authorization", "Content-Type", "Accept") if self.headers.get(key)}
        started = monotonic()
        previous_kind = None
        for attempt in range(self.server.retries + 1):
            request = Request(self.server.upstream + self.path, data=body, headers=headers, method=self.command)
            try:
                with urlopen(request, timeout=35) as upstream:
                    status, raw, response_headers = upstream.status, upstream.read(2_000_001), dict(upstream.headers.items())
            except HTTPError as exc:
                status, raw, response_headers = exc.code, exc.read(2_000_001), dict(exc.headers.items())
            except (URLError, TimeoutError, OSError):
                self._emit(502, {"Content-Type": "application/json"}, b'{"detail":"Upstream unavailable"}')
                return
            if len(raw) > 2_000_000:
                self._emit(502, {}, b"")
                return
            kind = recovery_kind(path, status, raw) if self.command == "POST" else None
            if kind is None:
                break
            previous_kind = kind
            if attempt >= self.server.retries:
                break
            sleep(self.server.delay * (attempt + 1))
        if previous_kind:
            logging.info(json.dumps({
                "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                "event": "external_recovery_attempt",
                "type": previous_kind, "attempts": attempt + 1,
                "recovered": kind is None, "elapsed_seconds": round(monotonic() - started, 3),
            }, ensure_ascii=False))
        self._emit(status, response_headers, raw)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--listen", default="127.0.0.1")
    p.add_argument("--port", type=int, default=18002)
    p.add_argument("--upstream", default="http://127.0.0.1:8000")
    p.add_argument("--max-retries", type=int, default=2)
    p.add_argument("--retry-delay", type=float, default=0.3)
    a = p.parse_args()
    if not a.upstream.startswith("http://") or a.max_retries not in (0, 1, 2) or a.retry_delay < 0:
        p.error("HTTP upstream and max-retries 0..2 are required")
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    server = ProxyServer((a.listen, a.port), ProxyHandler, upstream=a.upstream, retries=a.max_retries, delay=a.retry_delay)
    print(f"ChargePin recovery gateway ready on {a.listen}:{a.port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
