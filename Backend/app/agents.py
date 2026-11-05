"""Logical Planner, Executor, Critic and Orchestrator for ChargePin 1.0."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
import os
import re
from uuid import uuid4

from .models import (
    Availability, AvailabilityState, ChatPlanResponse, ChargerResult, ConfirmInput,
    ConnectorType, PlaceCandidate, Point, SearchInput, SearchOrigin, SearchRequest,
    SearchResponse,
)
from .providers import EnvironmentChargerAdapter, KakaoPlaceAdapter, ProviderError, kst_now
from .store import MemoryKeeper


GANGNAM_STATION = Point(lat=37.4980, lng=127.0270, source="initial_default")


@dataclass(frozen=True)
class PlanIntent:
    """Planner output: text conditions only, never provider-derived coordinates."""

    location_text: str
    radius_km: int
    connector_types: list[ConnectorType]


class Planner:
    """Natural language to request draft only.  It receives no provider adapters."""

    def draft(self, message: str, request_id: str) -> tuple[PlanIntent | None, str, bool]:
        compact = message.replace(" ", "")
        radius_match = re.findall(r"([135])\s*(?:km|킬로|키로)", compact, flags=re.IGNORECASE)
        radius = int(radius_match[-1]) if radius_match else 3
        has_fast, has_slow = "급속" in compact, "완속" in compact
        connector_types = [ConnectorType.FAST, ConnectorType.SLOW] if has_fast == has_slow else [ConnectorType.FAST if has_fast else ConnectorType.SLOW]

        # Only a bare broad phrase is intentionally ambiguous.  Planner does not choose coordinates.
        ambiguous = (
            ("서울" in compact and "서울역" not in compact and "시청" not in compact and "강남" not in compact)
            or ("강남" in compact and "강남역" not in compact and "강남구청" not in compact)
        )
        if ambiguous:
            return None, "location_ambiguous", True

        if not any(term in compact for term in ("서울역", "시청", "강남역")):
            return None, "location_missing", False
        return PlanIntent(location_text=message, radius_km=radius, connector_types=connector_types), "ready", False


class Executor:
    """Only component allowed to call provider adapters and normalize their output."""

    def __init__(self, places: KakaoPlaceAdapter, chargers: EnvironmentChargerAdapter) -> None:
        self._places = places
        self._chargers = chargers

    def place_candidates(self, location_text: str) -> list[PlaceCandidate]:
        return self._places.top_two(location_text)[:2]

    def execute(self, request: SearchRequest) -> list[ChargerResult]:
        results: list[ChargerResult] = []
        for station in self._chargers.nearby(request):
            chargers = station["chargers"]
            total = len(chargers)
            available = sum(1 for _, _, state, _ in chargers if state == "2")
            reported_values = [reported_at for _, _, _, reported_at in chargers]
            reported_at = min(reported_values) if reported_values and all(reported_values) else None
            state = AvailabilityState.AVAILABLE
            reason = None
            if total <= 0 or available > total:
                state = AvailabilityState.UNAVAILABLE
                available_value: int | None = None
                total_value: int | None = None
                label = "충전 상태 확인 불가"
                reason = "충전기 상태 집계가 유효하지 않습니다."
            else:
                available_value, total_value = available, total
                label = f"충전 가능 {available}/{total}"
            results.append(ChargerResult(
                facility_id=station["stat_id"], name=station["name"], address=station["address"],
                location=Point(lat=station["lat"], lng=station["lng"], source="environment"),
                distance_km=station["distance_km"], facility_type=station["kind"],
                connector_types=list(dict.fromkeys(charger[1] for charger in chargers)),
                availability=Availability(state=state, available_chargers=available_value, total_chargers=total_value, label=label, reason=reason),
                reported_at=reported_at, fetched_at=station["fetched_at"], use_time=station["use_time"],
                parking_free=station["parking_free"], restriction_detail=station["restriction_detail"],
            ))
        return results


class Critic:
    """Quality decision only; it never calls an adapter or changes provider values."""

    def review(self, results: list[ChargerResult]) -> tuple[str, list[str], str]:
        invalid_count = 0
        missing_time_count = 0
        delayed_count = 0
        freshness_limit = timedelta(minutes=int(os.environ.get("CHARGER_FRESHNESS_MINUTES", "30")))
        now = kst_now()
        for result in results:
            availability = result.availability
            if availability.state != AvailabilityState.AVAILABLE:
                invalid_count += 1
            elif result.reported_at is None:
                availability.state = AvailabilityState.UNAVAILABLE
                availability.available_chargers = None
                availability.total_chargers = None
                availability.label = "갱신 시각 확인 불가"
                missing_time_count += 1
            elif now - result.reported_at > freshness_limit:
                availability.state = AvailabilityState.DELAYED
                availability.available_chargers = None
                availability.total_chargers = None
                availability.label = "정보 지연"
                availability.reason = "환경공단 상태 갱신 시각이 최신성 한도를 넘었습니다."
                delayed_count += 1
        findings: list[str] = []
        if delayed_count:
            findings.append(f"환경공단 마지막 보고 시각이 최신성 기준을 넘은 충전소 {delayed_count}곳은 ‘정보 지연’으로 표시합니다.")
        if missing_time_count:
            findings.append(f"갱신 시각이 누락된 충전소 {missing_time_count}곳은 ‘갱신 시각 확인 불가’로 표시합니다.")
        if invalid_count:
            findings.append(f"상태 집계가 유효하지 않은 충전소 {invalid_count}곳은 ‘충전 상태 확인 불가’로 표시합니다.")
        if findings:
            return "SAFE_UNAVAILABLE", findings, "degraded"
        return "PASS", findings, "completed"


class SearchOrchestrator:
    def __init__(self) -> None:
        self.memory = MemoryKeeper()
        self.planner = Planner()
        self.executor = Executor(KakaoPlaceAdapter(), EnvironmentChargerAdapter())
        self.critic = Critic()

    @staticmethod
    def _request_id() -> str:
        return str(uuid4())

    def _build_request(self, request_id: str, data: SearchInput, origin: SearchOrigin, confirmed: bool) -> SearchRequest:
        return SearchRequest(request_id=request_id, origin=origin, requested_at=kst_now(), user_confirmed=confirmed, **data.model_dump())

    def _run(self, request: SearchRequest) -> SearchResponse:
        self.memory.update(request.request_id, execution_plan={"providers": ["KAKAO_PLACE", "KECO_EV"], "attempt_no": 1})
        try:
            results = self.executor.execute(request)
            decision, findings, status = self.critic.review(results)
        except ProviderError as error:
            results = []
            decision, findings, status = "SAFE_UNAVAILABLE", [error.user_message], "degraded"
        response = SearchResponse(request_id=request.request_id, status=status, applied_request=request, results=results, critic_decision=decision, critic_findings=findings)
        self.memory.save_result(request.request_id, response.model_dump(mode="json"))
        return response

    def default_search(self, user_role: str) -> SearchResponse:
        request_id = self._request_id()
        request = self._build_request(request_id, SearchInput(center=GANGNAM_STATION, radius_km=3, connector_types=[ConnectorType.FAST, ConnectorType.SLOW], region_filters=["zscode:11680"]), SearchOrigin.INITIAL_DEFAULT, True)
        self.memory.start(request_id, {"search_request": request.model_dump(mode="json"), "ui_role": user_role})
        return self._run(request)

    def direct_search(self, data: SearchInput, user_role: str) -> SearchResponse:
        request_id = self._request_id()
        request = self._build_request(request_id, data, SearchOrigin.SIDEBAR, True)
        self.memory.start(request_id, {"search_request": request.model_dump(mode="json"), "ui_role": user_role})
        return self._run(request)

    def suggest_places(self, query: str) -> list[PlaceCandidate]:
        """Executor-only Kakao lookup used by the sidebar place suggestions."""
        return self.executor.place_candidates(query)

    def plan_chat(self, message: str, user_role: str) -> ChatPlanResponse:
        request_id = self._request_id()
        draft, status, ambiguous = self.planner.draft(message, request_id)
        self.memory.start(request_id, {"raw_input": message, "ui_role": user_role, "planner_status": status})
        if status == "location_missing":
            return ChatPlanResponse(request_id=request_id, status="NEEDS_INPUT", message="검색할 서울 지역이나 장소를 알려 주세요. 예: 강남역, 서울역")
        if ambiguous:
            try:
                candidates = self.executor.place_candidates(message)
            except ProviderError as error:
                return ChatPlanResponse(request_id=request_id, status="NEEDS_INPUT", message=error.user_message)
            self.memory.update(request_id, candidates=[candidate.model_dump(mode="json") for candidate in candidates])
            first = candidates[0]
            return ChatPlanResponse(
                request_id=request_id, status="AWAITING_LOCATION_CONFIRMATION", candidates=candidates,
                suggested_candidate_id=first.candidate_id,
                message=f"장소 후보 2개를 찾았습니다. {first.name} 주변 3 km에서 급속·완속 충전소를 찾을까요?",
            )
        assert draft is not None
        # Executor performs this candidate-only lookup; Planner never gets provider tools.
        try:
            candidates = self.executor.place_candidates(draft.location_text)
        except ProviderError as error:
            return ChatPlanResponse(request_id=request_id, status="NEEDS_INPUT", message=error.user_message)
        if not candidates:
            return ChatPlanResponse(request_id=request_id, status="NEEDS_INPUT", message="장소 후보를 찾지 못했습니다. 다른 서울 장소를 알려 주세요.")
        selected = candidates[0]
        request = self._build_request(
            request_id,
            SearchInput(center=selected.location, radius_km=draft.radius_km, connector_types=draft.connector_types, region_filters=[]),
            SearchOrigin.CHAT,
            False,
        )
        self.memory.update(request_id, search_request=request.model_dump(mode="json"))
        return ChatPlanResponse(request_id=request_id, status="AWAITING_CONFIRMATION", search_request=request, message="조건을 확인했습니다. 이 조건으로 충전소를 검색할까요?")

    def confirm_chat(self, request_id: str, confirmation: ConfirmInput, user_role: str) -> SearchResponse | ChatPlanResponse:
        handoff = self.memory.handoffs.get(request_id)
        if handoff is None:
            raise KeyError(request_id)
        if not confirmation.confirmed:
            return ChatPlanResponse(request_id=request_id, status="NEEDS_INPUT", message="검색을 취소했습니다. 다른 장소를 입력해 주세요.")
        if "candidates" in handoff:
            candidates = [PlaceCandidate.model_validate(item) for item in handoff["candidates"]]
            selected = next((candidate for candidate in candidates if candidate.candidate_id == confirmation.candidate_id), candidates[0])
            region_filters = [f"zscode:{selected.district_code}"] if selected.district_code else []
            request = self._build_request(request_id, SearchInput(center=selected.location, radius_km=3, connector_types=[ConnectorType.FAST, ConnectorType.SLOW], region_filters=region_filters), SearchOrigin.CHAT, True)
        else:
            request = SearchRequest.model_validate(handoff["search_request"])
            request.user_confirmed = True
        self.memory.update(request_id, search_request=request.model_dump(mode="json"), ui_role=user_role, confirmation={"confirmed": True, "candidate_id": confirmation.candidate_id})
        return self._run(request)
