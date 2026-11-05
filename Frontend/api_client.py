"""Small HTTP client for the ChargePin preview backend."""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

import requests


@dataclass
class ApiError(Exception):
    message: str
    status_code: int | None = None
    payload: dict[str, Any] | None = None


class ChargePinApi:
    def __init__(self) -> None:
        self.base_url = os.environ.get("CHARGEPIN_API_BASE_URL", "http://localhost:8000/api/v1").rstrip("/")
        self.service_url = self.base_url.rsplit("/api/v1", 1)[0]

    def _request(self, method: str, path: str, *, access_token: str | None = None, root_url: bool = False, **kwargs: Any) -> dict[str, Any]:
        headers = dict(kwargs.pop("headers", {}))
        if access_token:
            headers["Authorization"] = f"Bearer {access_token}"
        base_url = self.service_url if root_url else self.base_url
        try:
            # The first live KECO request may populate provider caches and take longer than
            # an ordinary UI API call. Subsequent requests use the short in-process cache.
            response = requests.request(method, f"{base_url}{path}", timeout=45, headers=headers, **kwargs)
        except requests.RequestException as error:
            raise ApiError("백엔드에 연결하지 못했습니다. Backend 서버가 실행 중인지 확인해 주세요.") from error
        try:
            payload = response.json()
        except ValueError:
            payload = {"message": "응답 형식을 해석하지 못했습니다."}
        if not response.ok:
            message = payload.get("message") or payload.get("detail") or "요청을 처리하지 못했습니다."
            raise ApiError(str(message), response.status_code, payload)
        return payload

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
