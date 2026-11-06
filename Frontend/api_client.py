"""Small HTTP client for the ChargePin preview backend."""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Callable
from datetime import datetime, timezone
from time import perf_counter

import requests


@dataclass
class ApiError(Exception):
    message: str
    status_code: int | None = None
    payload: dict[str, Any] | None = None


class ChargePinApi:
    def __init__(self, observer: Callable[[dict[str, Any]], None] | None = None) -> None:
        self.observer = observer
        self.base_url = os.environ.get("CHARGEPIN_API_BASE_URL", "http://localhost:8000/api/v1").rstrip("/")
        self.service_url = self.base_url.rsplit("/api/v1", 1)[0]

    def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        started = perf_counter()
        event = {"method": method, "path": path, "observed_at": datetime.now(timezone.utc).isoformat()}
        try:
            payload = self._perform_request(method, path, **kwargs)
        except ApiError as error:
            event.update(outcome="error", status_code=error.status_code)
            self._observe(event, started)
            raise
        event.update(outcome="success")
        if isinstance(payload, dict) and (path in ("/search", "/chat/plan") or
                                          (path.startswith("/search/") and path.endswith("/confirm"))):
            request_id = payload.get("request_id")
            if (isinstance(request_id, str) and 0 < len(request_id) <= 80 and request_id.isascii()
                    and all(char.isalnum() or char in "-_" for char in request_id)):
                event["request_id"] = request_id
        if path == "/places/suggest" and isinstance(payload, list):
            event["place_lookup"] = "success"
            event["result_count"] = len(payload)
        elif path == "/chat/plan" and isinstance(payload, dict):
            if payload.get("status") == "BLOCKED":
                event["guardrail_blocked"] = True
            elif payload.get("candidates") or payload.get("search_request"):
                event["place_lookup"] = "success"
            event["plan_status"] = payload.get("status")
        if isinstance(payload, dict) and "results" in payload and "applied_request" in payload:
            event["search_status"] = payload.get("status")
            event["result_count"] = len(payload.get("results", []))
        self._observe(event, started)
        return payload

    def _observe(self, event: dict[str, Any], started: float) -> None:
        event["elapsed_ms"] = round((perf_counter() - started) * 1000)
        if self.observer is not None:
            # Telemetry cannot change the API result; never record keys, tokens, queries or response bodies.
            try:
                self.observer(event)
            except Exception:
                pass

    def _perform_request(self, method: str, path: str, *, access_token: str | None = None, root_url: bool = False, **kwargs: Any) -> dict[str, Any]:
        headers = dict(kwargs.pop("headers", {}))
        if access_token:
            headers["Authorization"] = f"Bearer {access_token}"
        base_url = self.service_url if root_url else self.base_url
        try:
            # The first live KECO request may populate provider caches and take longer than
            # an ordinary UI API call. Subsequent requests use the short in-process cache.
            timeout = kwargs.pop("timeout", 45)
            response = requests.request(method, f"{base_url}{path}", timeout=timeout, headers=headers, **kwargs)
        except requests.RequestException as error:
            raise ApiError("백엔드에 연결하지 못했습니다. Backend 서버가 실행 중인지 확인해 주세요.") from error
        try:
            payload = response.json()
        except ValueError:
            payload = {"message": "응답 형식을 해석하지 못했습니다."}
        if not response.ok:
            message = payload.get("message") or payload.get("detail") or "요청을 처리하지 못했습니다."
            if not isinstance(message, str):
                message = "입력 내용을 확인한 뒤 다시 시도해주세요."
            raise ApiError(message, response.status_code, payload)
        return payload

    def health(self) -> dict[str, Any]:
        return self._request("GET", "/healthz", root_url=True, timeout=5)

    def login(self, service_key: str) -> dict[str, Any]:
        return self._request("POST", "/auth/login", json={"service_key": service_key})

    def default_search(self, access_token: str) -> dict[str, Any]:
        return self._request("POST", "/search/default", access_token=access_token)

    def search(self, body: dict[str, Any], access_token: str) -> dict[str, Any]:
        return self._request("POST", "/search", json=body, access_token=access_token)

    def suggest_places(self, query: str, access_token: str) -> list[dict[str, Any]]:
        payload = self._request("POST", "/places/suggest", json={"query": query}, access_token=access_token)
        return payload if isinstance(payload, list) else []

    def plan(self, message: str, access_token: str) -> dict[str, Any]:
        return self._request("POST", "/chat/plan", json={"message": message}, access_token=access_token)

    def confirm(self, request_id: str, access_token: str, candidate_id: str | None = None) -> dict[str, Any]:
        return self._request("POST", f"/search/{request_id}/confirm", json={"confirmed": True, "candidate_id": candidate_id}, access_token=access_token)

    def boom(self, scenario: int, access_token: str) -> dict[str, Any]:
        return self._request("GET", f"/boom/{scenario}", access_token=access_token, root_url=True)
