"""FastAPI entry point for ChargePin 1.0 preview."""
from __future__ import annotations

import os

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .agents import SearchOrchestrator
from .auth import AuthSession, SessionAuthenticator
from .models import AuthLoginInput, AuthLoginResponse, ChatPlanInput, ConfirmInput, PlaceCandidate, PlaceSuggestInput, SearchInput
from .providers import ProviderError

app = FastAPI(title="ChargePin API", version="1.0.0-preview")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8501", "http://127.0.0.1:8501"],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)
orchestrator = SearchOrchestrator()
authenticator = SessionAuthenticator()
TEST_SCENARIOS_ENABLED = os.environ.get("CHARGEPIN_ENABLE_TEST_SCENARIOS", "true").casefold() == "true"


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok", "service": "chargepin-backend"}


def require_session(authorization: str | None = Header(default=None)) -> AuthSession:
    return authenticator.require(authorization)


@app.post("/api/v1/auth/login", response_model=AuthLoginResponse)
def login(body: AuthLoginInput) -> AuthLoginResponse:
    token, session = authenticator.login(body.service_key)
    return AuthLoginResponse(access_token=token, role=session.role, expires_at=session.expires_at)


@app.post("/api/v1/search/default")
def default_search(session: AuthSession = Depends(require_session)):
    return orchestrator.default_search(session.role)


@app.post("/api/v1/search")
def direct_search(body: SearchInput, session: AuthSession = Depends(require_session)):
    return orchestrator.direct_search(body, session.role)


@app.post("/api/v1/places/suggest", response_model=list[PlaceCandidate])
def suggest_places(body: PlaceSuggestInput, _session: AuthSession = Depends(require_session)):
    try:
        return orchestrator.suggest_places(body.query)
    except ProviderError as error:
        raise HTTPException(status_code=503 if error.retryable else 422, detail=error.user_message) from error


@app.post("/api/v1/chat/plan")
def chat_plan(body: ChatPlanInput, session: AuthSession = Depends(require_session)):
    return orchestrator.plan_chat(body.message, session.role, session.session_ref)


@app.post("/api/v1/search/{request_id}/confirm")
def confirm_search(request_id: str, body: ConfirmInput, session: AuthSession = Depends(require_session)):
    try:
        return orchestrator.confirm_chat(request_id, body, session.role, session.session_ref)
    except KeyError as error:
        raise HTTPException(status_code=404, detail="확인 대기 중인 요청을 찾지 못했습니다.") from error


@app.get("/api/v1/search/{request_id}")
def get_search(request_id: str, _session: AuthSession = Depends(require_session)):
    result = orchestrator.memory.get_result(request_id)
    if result is None:
        raise HTTPException(status_code=404, detail="검색 결과를 찾지 못했습니다.")
    return result


_BOOM_SCENARIOS = {
    1: (200, "NO_RESULTS", "조건에 맞는 충전소를 찾지 못했습니다."),
    2: (200, "DATA_DELAYED", "충전 상태 정보가 지연되고 있습니다."),
    3: (429, "RATE_LIMITED", "현재 요청이 많아 잠시 후 다시 시도해 주세요."),
    4: (401, "PROVIDER_AUTH_EXPIRED", "데이터 제공 인증이 만료되었습니다."),
    5: (503, "AI_CHAT_UNAVAILABLE", "AI 챗 연결이 일시적으로 원활하지 않습니다."),
}


@app.get("/boom/{scenario}")
def boom(scenario: int, _session: AuthSession = Depends(require_session)):
    if not TEST_SCENARIOS_ENABLED:
        raise HTTPException(status_code=404, detail="테스트 시나리오는 이 환경에서 비활성화되어 있습니다.")
    if scenario not in _BOOM_SCENARIOS:
        raise HTTPException(status_code=404, detail="시나리오는 1~5만 지원합니다.")
    status_code, code, message = _BOOM_SCENARIOS[scenario]
    return JSONResponse(status_code=status_code, content={"test_only": True, "scenario": scenario, "code": code, "message": message})
