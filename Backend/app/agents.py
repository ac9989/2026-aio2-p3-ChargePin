"""Logical Planner, Executor, Critic and Orchestrator for ChargePin 1.0."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
import os
import re
import unicodedata
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
    radius_km: float
    connector_types: list[ConnectorType]


@dataclass(frozen=True)
class GuardrailDecision:
    blocked: bool
    category: str | None = None


class InputGuardrail:
    """Classify unsafe capability requests before Planner can reach Executor tools."""

    _rules = (
        ("PROMPT_OVERRIDE", re.compile(
            r"(?:(?:이전|시스템|숨겨진|개발자|상위).{0,18}(?:지침|프롬프트|명령)|"
            r"(?:system|developer|hidden).{0,18}(?:instruction|prompt|command)).{0,24}"
            r"(?:무시|따르|출력|공개|덧붙|ignore|follow|reveal|append)"
        )),
        ("SECRET_REQUEST", re.compile(
            r"(?:환경변수|env|environment|api키|apikey|서비스키|비밀번호|토큰|"
            r"secret|canary|dummysecret|시스템지침|숨겨진지침|systemprompt|hiddenprompt)"
        )),
        ("OTHER_USER_DATA", re.compile(
            r"(?:(?:다른|타인|모든).{0,14}(?:사용자|사람).{0,18}(?:대화|기록|정보|데이터)|"
            r"(?:other|another|all).{0,14}(?:user|users).{0,18}(?:chat|history|data|record))"
        )),
        ("PRIVILEGE_CHANGE", re.compile(
            r"(?:(?:권한|등급|역할|관리자|admin).{0,14}(?:변경|수정|바꾸|바꿈|조정|조작|전환|설정|"
            r"승급|강등|올리|내리|부여|삭제|해줘|만들어|되게)|(?:나를|내).{0,14}"
            r"(?:상급|하급)?(?:관리자|admin).{0,12}(?:해줘|만들어|되게)|"
            r"(?:role|privilege|permission|admin).{0,14}(?:change|modify|update|switch|grant|promote|demote|delete)|"
            r"(?:make|set).{0,14}(?:admin|role|privilege|permission))"
        )),
    )

    @staticmethod
    def _normalize(message: str) -> str:
        value = unicodedata.normalize("NFKC", message).casefold()
        return re.sub(r"[^0-9a-z가-힣]+", "", value)

    def inspect(self, message: str) -> GuardrailDecision:
        normalized = self._normalize(message)
        for category, rule in self._rules:
            if rule.search(normalized):
                return GuardrailDecision(blocked=True, category=category)
        return GuardrailDecision(blocked=False)


class Planner:
    """Natural language to request draft only.  It receives no provider adapters."""

    @staticmethod
    def range_label(radius_km: float) -> str:
        return f"검색 범위 {radius_km * 2:g} km (반경 {radius_km:g} km)"

    @staticmethod
    def _location_query(message: str) -> str:
        """Remove search conditions, leaving the phrase to be looked up by Executor.

        This is deliberately a lightweight parser: deciding whether the resulting
        name exists is the Executor's Kakao-place responsibility, not Planner's.
        """
        value = message.strip()
        value = re.sub(r"[123]\s*(?:km|킬로미터|킬로|키로)", " ", value, flags=re.IGNORECASE)
        value = re.sub(
            r"(?:급속|완속|전기차|충전소|충전기|주변|근처|주위|반경|이내|"
            r"찾아주세요|찾아줘|찾아|알려주세요|알려줘|알려|보여주세요|보여줘|보여|"
            r"검색해주세요|검색해줘|검색|해주세요|해줘|좀)",
            " ",
            value,
        )
        value = re.sub(r"^(?:그럼|그냥|아니|혹시)\s*", "", value)
        value = re.sub(r"[?!,.]+", " ", value)
        value = re.sub(r"\s+", " ", value).strip()
        value = re.sub(r"(?:에서|으로|로|에)$", "", value).strip()
        return value

    def draft(self, message: str, request_id: str) -> tuple[PlanIntent | None, str, bool]:
        compact = message.replace(" ", "")
        diameter_match = re.findall(r"([123])\s*(?:km|킬로미터|킬로|키로)", compact, flags=re.IGNORECASE)
        radius = int(diameter_match[-1]) / 2 if diameter_match else 0.5
        has_fast, has_slow = "급속" in compact, "완속" in compact
        connector_types = [ConnectorType.FAST, ConnectorType.SLOW] if has_fast == has_slow else [ConnectorType.FAST if has_fast else ConnectorType.SLOW]
        location_text = self._location_query(message)
        if len(location_text) < 2:
            return None, "location_missing", False

        # Broad area names require an explicit user choice after Kakao ranking.
        ambiguous = location_text in {"서울", "강남"}
        if ambiguous:
            return PlanIntent(location_text=location_text, radius_km=radius, connector_types=connector_types), "location_ambiguous", True
        return PlanIntent(location_text=location_text, radius_km=radius, connector_types=connector_types), "ready", False


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
            # A station can have independently updated chargers.  Present the most
            # recent provider status for the station, while retaining the source time.
            reported_at = max((value for value in reported_values if value is not None), default=None)
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
        missing_all_count = 0
        delayed_all_count = 0
        # The provider can retain a charger state until it changes.  Treat the newest
        # station status received within seven days as displayable information.
        freshness_limit = timedelta(minutes=int(os.environ.get("CHARGER_FRESHNESS_MINUTES", "10080")))
        now = kst_now()
        for result in results:
            availability = result.availability
            if availability.state != AvailabilityState.AVAILABLE:
                invalid_count += 1
                continue

            if result.reported_at is None:
                availability.state = AvailabilityState.UNAVAILABLE
                availability.available_chargers = None
                availability.total_chargers = None
                availability.label = "갱신 시각 확인 불가"
                missing_all_count += 1
            elif now - result.reported_at > freshness_limit:
                availability.state = AvailabilityState.DELAYED
                availability.available_chargers = None
                availability.total_chargers = None
                availability.label = "정보 지연"
                availability.reason = "환경공단 상태 갱신 시각이 최신성 한도를 넘었습니다."
                delayed_all_count += 1
        findings: list[str] = []
        if delayed_all_count:
            findings.append(f"충전소의 가장 최근 보고 시각이 최신성 기준을 넘은 충전소 {delayed_all_count}곳은 ‘정보 지연’으로 표시합니다.")
        if missing_all_count:
            findings.append(f"모든 충전기의 갱신 시각이 누락된 충전소 {missing_all_count}곳은 ‘갱신 시각 확인 불가’로 표시합니다.")
        if invalid_count:
            findings.append(f"상태 집계가 유효하지 않은 충전소 {invalid_count}곳은 ‘충전 상태 확인 불가’로 표시합니다.")
        if findings:
            return "SAFE_UNAVAILABLE", findings, "degraded"
        return "PASS", findings, "completed"


class SearchOrchestrator:
    def __init__(self) -> None:
        self.memory = MemoryKeeper()
        self.input_guardrail = InputGuardrail()
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
        request = self._build_request(request_id, SearchInput(center=GANGNAM_STATION, radius_km=0.5, connector_types=[ConnectorType.FAST, ConnectorType.SLOW], region_filters=["zscode:11680"]), SearchOrigin.INITIAL_DEFAULT, True)
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
        guardrail = self.input_guardrail.inspect(message)
        if guardrail.blocked:
            # Never retain the blocked source text; it may itself contain sensitive data.
            self.memory.start(request_id, {
                "ui_role": user_role,
                "planner_status": "BLOCKED",
                "guardrail": {"decision": "BLOCKED", "category": guardrail.category},
            })
            self.memory.record_audit(request_id, "guardrail_blocked")
            return ChatPlanResponse(
                request_id=request_id,
                status="BLOCKED",
                message="안전 정책상 시스템 지침·비밀 정보·권한 변경 요청은 처리할 수 없습니다. 충전소 검색 조건을 입력해 주세요.",
            )
        draft, status, ambiguous = self.planner.draft(message, request_id)
        self.memory.start(request_id, {"raw_input": message, "ui_role": user_role, "planner_status": status})
        if status == "location_missing":
            return ChatPlanResponse(request_id=request_id, status="NEEDS_INPUT", message="검색할 장소명을 알려 주세요. 예: 사당역, 강남역, 서울시청")
        assert draft is not None
        if ambiguous:
            try:
                candidates = self.executor.place_candidates(draft.location_text)
            except ProviderError as error:
                return ChatPlanResponse(request_id=request_id, status="NEEDS_INPUT", message=error.user_message)
            if not candidates:
                return ChatPlanResponse(request_id=request_id, status="NEEDS_INPUT", message="장소 후보를 찾지 못했습니다. 다른 서울 장소를 알려 주세요.")
            self.memory.update(
                request_id,
                candidates=[candidate.model_dump(mode="json") for candidate in candidates],
                planner_conditions={"radius_km": draft.radius_km, "connector_types": [item.value for item in draft.connector_types]},
            )
            first = candidates[0]
            types = "·".join("급속" if item == ConnectorType.FAST else "완속" for item in draft.connector_types)
            return ChatPlanResponse(
                request_id=request_id, status="AWAITING_LOCATION_CONFIRMATION", candidates=candidates,
                suggested_candidate_id=first.candidate_id,
                message=f"장소 후보 {len(candidates)}개를 찾았습니다. {first.name} 주변 {self.planner.range_label(draft.radius_km)}에서 {types} 충전소를 찾을까요?",
            )
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
            SearchInput(
                center=selected.location,
                radius_km=draft.radius_km,
                connector_types=draft.connector_types,
                region_filters=[f"zscode:{selected.district_code}"] if selected.district_code else [],
            ),
            SearchOrigin.CHAT,
            False,
        )
        self.memory.update(request_id, search_request=request.model_dump(mode="json"))
        types = "·".join("급속" if item == ConnectorType.FAST else "완속" for item in draft.connector_types)
        return ChatPlanResponse(
            request_id=request_id,
            status="AWAITING_CONFIRMATION",
            search_request=request,
            candidates=candidates,
            suggested_candidate_id=selected.candidate_id,
            message=f"{selected.name} 주변 {self.planner.range_label(draft.radius_km)}에서 {types} 충전소를 찾을까요?",
        )

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
            conditions = handoff.get("planner_conditions", {})
            radius_km = conditions.get("radius_km", 0.5)
            connector_values = conditions.get("connector_types", [ConnectorType.FAST.value, ConnectorType.SLOW.value])
            request = self._build_request(
                request_id,
                SearchInput(
                    center=selected.location,
                    radius_km=radius_km,
                    connector_types=[ConnectorType(value) for value in connector_values],
                    region_filters=region_filters,
                ),
                SearchOrigin.CHAT,
                True,
            )
        else:
            request = SearchRequest.model_validate(handoff["search_request"])
            request.user_confirmed = True
        self.memory.update(request_id, search_request=request.model_dump(mode="json"), ui_role=user_role, confirmation={"confirmed": True, "candidate_id": confirmation.candidate_id})
        return self._run(request)
