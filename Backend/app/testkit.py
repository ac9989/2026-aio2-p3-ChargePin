"""Test-only, deterministic fault fixtures for the ChargePin recovery checker.

This module never reads credentials or real provider responses.  It is exposed
through an API only when ``CHARGEPIN_ENABLE_FAULT_INJECTION=true``.
"""
from __future__ import annotations

from datetime import timedelta
from threading import Lock
from typing import Final

from .models import Availability, AvailabilityState, ChargerResult, ConnectorType, Point, SearchRequest
from .providers import ProviderError, kst_now


TEST_SCENARIOS: Final = frozenset({
    "normal",
    "stale",
    "invalid_count",
    "timeout",
    "executor_exception",
    "llm_invalid_schema",
    "timeout_once",
    "executor_exception_once",
    "llm_invalid_schema_once",
})
_EXECUTOR_SCENARIOS: Final = frozenset(TEST_SCENARIOS - {"llm_invalid_schema", "llm_invalid_schema_once"})


class TestScenarioController:
    """Stores one active test scenario for a single backend process.

    The controller is intentionally process-local: it is a testing aid, not a
    production feature or a substitute for provider configuration.
    """

    def __init__(self) -> None:
        self._active: str | None = None
        self._consumed = False
        self._lock = Lock()

    def active(self) -> str | None:
        with self._lock:
            return self._active

    def activate(self, scenario: str) -> bool:
        if scenario not in TEST_SCENARIOS:
            return False
        with self._lock:
            self._active = scenario
            self._consumed = False
        return True

    def clear(self) -> None:
        with self._lock:
            self._active = None
            self._consumed = False

    def executor_scenario(self) -> str | None:
        scenario = self.active()
        return scenario if scenario in _EXECUTOR_SCENARIOS else None

    def has_invalid_llm_schema(self) -> bool:
        with self._lock:
            if self._active == "llm_invalid_schema":
                return True
            if self._active == "llm_invalid_schema_once" and not self._consumed:
                self._consumed = True
                return True
            return False

    @staticmethod
    def invalid_llm_payload() -> dict[str, str]:
        """A deliberate schema violation that contains no prompt or secret data."""
        return {"unexpected_field": "not-a-search-request"}

    def execute_fixture(self, request: SearchRequest) -> list[ChargerResult] | None:
        """Return a safe fixture or raise the exact fault selected for a test."""
        with self._lock:
            scenario = self._active
            if scenario in {"timeout_once", "executor_exception_once"}:
                if self._consumed:
                    scenario = "normal"
                else:
                    self._consumed = True
            if scenario not in _EXECUTOR_SCENARIOS:
                return None
        if scenario in {"timeout", "timeout_once"}:
            raise ProviderError("KECO", "환경공단 응답이 지연되고 있습니다.", retryable=True)
        if scenario in {"executor_exception", "executor_exception_once"}:
            raise RuntimeError("test executor exception")

        now = kst_now()
        reported_at = now - timedelta(days=8) if scenario == "stale" else now
        if scenario == "invalid_count":
            available, total = 2, 1
            name = "테스트 비정상 집계 충전소"
        elif scenario == "stale":
            available, total = 1, 2
            name = "테스트 정보 지연 충전소"
        else:
            available, total = 1, 2
            name = "테스트 정상 충전소"
        return [ChargerResult(
            facility_id=f"test-{scenario}",
            name=name,
            address="서울특별시 강남구 테스트로 1",
            location=Point(lat=request.center.lat, lng=request.center.lng, source="test_api"),
            distance_km=0.1,
            facility_type="테스트 시설",
            connector_types=[ConnectorType.FAST, ConnectorType.SLOW],
            availability=Availability(
                state=AvailabilityState.AVAILABLE,
                available_chargers=available,
                total_chargers=total,
                label=f"충전 가능 {available}/{total}",
            ),
            reported_at=reported_at,
            fetched_at=now,
            use_time="24시간",
        )]
