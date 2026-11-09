# ChargePin API 시험 결과 보고서 1.0

> 서울 전기차 충전소 안내 멀티 에이전트 서비스

- 작성일: 2026-11-09
- 시험 대상: FastAPI `/healthz`, `/api/v1/*`, Test API, 검색·복구·운영 API 계약
- 시험 방식: pytest, FastAPI TestClient, 가짜 Provider·Test API fixture

---

## 1. 시험 목적

본 시험은 ChargePin의 프론트엔드와 FastAPI 백엔드 간 API 경로·요청·응답 계약이 일치하는지, 그리고 외부 API·Executor·LLM 오류가 발생했을 때 안전한 상태로 종료되는지 확인하기 위해 수행했다.

실제 카카오·환경공단·OpenAI API를 호출하지 않고, Test API와 가짜 Provider를 사용했다. 따라서 키 노출·호출 비용·외부 데이터 변동 없이 재현 가능한 시험 결과를 확보한다.

## 2. 시험 환경

| 항목 | 내용 |
| --- | --- |
| 백엔드 | FastAPI `1.0.0-preview` |
| 실행 도구 | `uv run` + `pytest` |
| Python 의존성 | `Backend/requirements.txt` |
| HTTP 시험 도구 | FastAPI `TestClient` |
| 외부 연동 대체 | `TestScenarioController`, 가짜 Provider, mock |
| 테스트 API 설정 | 테스트 코드 안에서 `CHARGEPIN_ENABLE_FAULT_INJECTION=true`로 제한 |

## 3. 시험 범위

### 3.1 API 계약 시험

대상 파일: `Backend/tests/test_ci04_contract.py`

| ID | 시험 항목 | 검증 내용 | 결과 |
| --- | --- | --- | --- |
| API-C01 | 프론트·백엔드 경로 일치 | 프론트 `api_client.py`가 호출하는 health, login, 기본 검색, 직접 검색, 후보, 채팅, 확인, 운영 API, `/boom` 경로가 FastAPI에 존재하는지 확인 | 통과 |
| API-C02 | 검색 요청 Payload | `center`, `radius_km`, `connector_types`, `region_filters`가 SearchInput 계약과 맞는지 확인 | 통과 |
| API-C03 | 검색 범위 계약 | UI 표시 1·2·3 km가 API 실제 반경 `0.5`·`1.0`·`1.5` km만 허용하는지 확인 | 통과 |
| API-C04 | 검색 응답 계약 | `request_id`, 결과 목록, Critic 판정, 출처·보고 시각 관련 응답 구조 확인 | 통과 |

### 3.2 Test API·복구 시험

대상 파일: `Backend/tests/test_fault_recovery.py`

| ID | 시험 항목 | 주입·확인 내용 | 결과 |
| --- | --- | --- | --- |
| API-R01 | Test API 비활성 보호 | `CHARGEPIN_ENABLE_FAULT_INJECTION=false`이면 Test API가 `404`인지 확인 | 통과 |
| API-R02 | 정상 fixture | `normal`에서 `completed`, Critic `PASS`, `AVAILABLE` 상태인지 확인 | 통과 |
| API-R03 | 데이터 품질 오류 | `stale`, `invalid_count`에서 `degraded`, 안전 상태, 빈자리 수 미표시인지 확인 | 통과 |
| API-R04 | FT-01 timeout | 최초 호출 뒤 자동 재시도 2회, 총 3회 시도, retry 이벤트·안전 응답인지 확인 | 통과 |
| API-R05 | FT-02 Executor 예외 | 내부 예외 원문·HTTP 500을 사용자에게 노출하지 않고 감사 이벤트를 남기는지 확인 | 통과 |
| API-R06 | FT-04 LLM 스키마 오류 | `NEEDS_INPUT`, `llm_plan_error`, 카카오 장소 Provider 미호출인지 확인 | 통과 |

### 3.3 관련 백엔드 시험

아래 항목은 API 시험과 연결되는 도메인·보안 검증이다.

| 영역 | 검증 내용 |
| --- | --- |
| Planner | 명확한 장소의 규칙 빠른 경로, 문맥형 조건 변경의 LLM 경로, 범위 초과 거부 |
| 가드레일 | 지침 무시, 비밀값 요청, 타인 정보, 권한 변경 요청이 Provider 호출 전에 차단되는지 확인 |
| Executor·Critic | 서울 외 결과 제외, 최신성 7일 기준, 빈자리 수가 총 충전기 수를 초과할 때 안전 처리 |
| 재시도 | 재시도 가능 오류는 자동 최대 2회, 인증 오류는 자동 재시도하지 않는지 확인 |
| 운영 API 데이터 | 검색·수동 재처리·가드레일·품질 이벤트가 운영 요약에 집계되는지 확인 |

## 4. 시험 실행 명령과 결과

### 4.1 API 핵심 시험

```powershell
cd C:\study\Project\2026-aio2-guide-main\aio2_p3_ChargePin\Backend
uv run --with-requirements requirements.txt pytest -q tests/test_ci04_contract.py tests/test_fault_recovery.py
```

**실행 결과**

```text
10 passed, 1 warning in 0.68s
```

경고 1건은 Starlette TestClient 의존성의 deprecation warning이며, 시험 실패·API 오류는 아니다.

### 4.2 백엔드 전체 시험

```powershell
cd C:\study\Project\2026-aio2-guide-main\aio2_p3_ChargePin\Backend
uv run --with-requirements requirements.txt pytest -q
```

**실행 결과**

```text
39 passed, 1 warning in 0.95s
```

| 구분 | 수집 테스트 수 | 통과 | 실패 |
| --- | ---: | ---: | ---: |
| Agent·가드레일·재시도 | 24 | 24 | 0 |
| API 계약 | 4 | 4 | 0 |
| Test API·복구 | 6 | 6 | 0 |
| 운영 Snapshot | 3 | 3 | 0 |
| 서울 범위 | 2 | 2 | 0 |
| 합계 | **39** | **39** | **0** |

## 5. 주요 API 시험 결과

### 5.1 인증·권한

| 확인 항목 | 결과 |
| --- | --- |
| Test API의 상급 관리자 전용 경계 | TestClient가 상급 관리자 로그인 토큰을 발급받아 시험하며, 기능 비활성 시에는 404를 반환하는 것을 확인 |
| 운영 API의 관리자 전용 경계 | FastAPI의 `require_operator` 의존성이 `JUNIOR_ADMIN`, `SENIOR_ADMIN`만 통과하도록 구현됨 |
| 서비스 키·토큰 원문 비노출 | 응답·Handoff·운영 이벤트에 원문을 저장하지 않는 구조 확인 |

`GUEST`의 운영 API 403 응답과 만료 토큰 401 응답은 서버 의존성으로 구현돼 있으며, 제출 전 브라우저 또는 TestClient로 추가 캡처하면 권한 시연 증빙을 강화할 수 있다.

### 5.2 검색·채팅 API

| 확인 항목 | 결과 |
| --- | --- |
| 장소 후보 조회 | 프론트 호출 경로와 FastAPI `/places/suggest` 경로 일치 확인 |
| 직접 검색 | SearchInput의 좌표·반경·타입 검증 계약 확인 |
| 자연어 계획 | 채팅이 SearchRequest 초안만 만들고, 확인 전 환경공단 검색을 시작하지 않는 흐름 확인 |
| 채팅 확정 | 후보·조건 확인 후 동일 SearchRequest 기반 검색으로 진행하도록 구현 |
| 범위 제한 | 1·2·3 km 외의 명시 요청을 검색 전에 거절하도록 검증 |

### 5.3 오류·복구 API

| 확인 항목 | 결과 |
| --- | --- |
| 재시도 가능 timeout | 자동 2회 재시도 뒤 안전한 실패로 종료 |
| 인증·형식 오류 | 자동 재시도하지 않고 안전한 안내로 종료하는 정책 존재 |
| LLM 오류 | Provider 호출 전에 `NEEDS_INPUT`으로 종료 |
| stale·invalid_count | 빈자리·총 충전기 수를 숨기고 `SAFE_UNAVAILABLE` 반환 |
| 운영 이력 | retry·오류·가드레일 이벤트가 운영 요약용 메모리에 기록 |

## 6. API 시험 한계와 실제 실행 증빙

pytest는 API 계약과 실패 처리의 코드 동작을 검증한다. 다음 항목은 별도의 통합·시연 증빙이 필요하다.

| 항목 | 현재 상태 | 필요한 증빙 |
| --- | --- | --- |
| 실제 카카오 장소 API | 실 API 화면 확인 별도 | 카카오 지도·후보 검색 화면 캡처 |
| 실제 환경공단 API | 실 API 화면 확인 별도 | 충전 상태·출처·보고 시각 화면 캡처 |
| Test API 장애 주입 | 코드 시험 통과, 실제 반복 증빙 전 | FT-01·02·04 각 3회, 총 9회 JSON·대시보드 캡처 |
| Docker API 연결 | Compose 통합 확인 별도 | backend·frontend `healthy`, 실제 화면 캡처 |
| 권한 오류 화면 | 서버 구현 완료, 별도 시연 가능 | 손님 운영 대시보드 접근 팝업·403 캡처 |

### 6.1 필수 장애시험 실행 방법

```powershell
# .env에서 CHARGEPIN_ENABLE_FAULT_INJECTION=true 설정 후 Compose 재기동
$env:CHARGEPIN_TEST_OPERATOR_KEY = "상급 관리자 서비스 키"
py Backend/scripts/run_fault_evidence.py --repeat 3
```

- FT-01 timeout, FT-02 Executor 예외, FT-04 LLM 스키마 오류를 각 3회 수행한다.
- `artifacts/fault-recovery-evidence.json`에 실행 결과가 남는다.
- 시연 종료 후 Test API를 reset하고 환경 변수를 다시 `false`로 바꾼다.

## 7. 결론

API 계약 시험 4건과 Test API·복구 시험 6건, 총 10건이 모두 통과했다. 또한 관련 백엔드 전체 시험 39건이 통과해 검색·채팅·가드레일·재시도·품질 판정·운영 이벤트 계약이 현재 코드에서 일관되게 동작함을 확인했다.

다만 이는 가짜 Provider·TestClient 기반의 재현 가능한 코드 시험 결과다. 최종 시연에는 실제 외부 API 연동 화면, Docker Compose `healthy` 상태, Test API 장애 주입 9회 및 운영 대시보드 이력을 추가 증빙으로 남긴다.
