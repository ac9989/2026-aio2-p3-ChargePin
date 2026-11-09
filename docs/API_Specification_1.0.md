# ChargePin API 명세서 1.0

> 서울 전기차 충전소 안내 멀티 에이전트 서비스 API

- 기준 버전: FastAPI `1.0.0-preview`
- 작성일: 2026-11-09
- 형식: JSON / UTF-8

---

## 1. 기본 정보

| 항목 | 값 |
| --- | --- |
| 로컬 백엔드 주소 | `http://localhost:8000` |
| Docker 프론트 기준 API 주소 | `http://backend:8000/api/v1` |
| API 공통 Prefix | `/api/v1` |
| Swagger 문서 | `http://localhost:8000/docs` |
| 인증 방식 | `Authorization: Bearer <access_token>` |
| 데이터 형식 | `application/json` |
| 세션 유효 시간 | 로그인 시점부터 4시간 |

`/healthz`와 `/boom/{scenario}`을 제외한 일반 API는 `/api/v1` Prefix를 사용한다.

## 2. 인증·권한

### 2.1 로그인 방식

사용자는 서비스 키를 `/auth/login`에 전송한다. 백엔드는 키 원문을 반환하지 않고, 역할과 짧은 유효 기간의 access token만 반환한다.

| 역할 | 코드 | 접근 범위 |
| --- | --- | --- |
| 손님 | `GUEST` | 검색·채팅·결과 조회 |
| 하급 관리자 | `JUNIOR_ADMIN` | 손님 기능 + 운영 API 조회·재처리·캐시 갱신 |
| 상급 관리자 | `SENIOR_ADMIN` | 하급 관리자 기능 + 테스트 장애 주입 API |

### 2.2 공통 오류 응답

```json
{
  "detail": "관리자 전용 기능입니다."
}
```

| HTTP 상태 | 의미 | 대표 상황 |
| --- | --- | --- |
| `200` | 성공 | 정상 조회·검색·처리 완료 |
| `401` | 인증 실패 | 로그인 키 오류, 토큰 누락·만료 |
| `403` | 권한 부족 | 손님의 운영 API 접근, 하급 관리자의 Test API 접근 |
| `404` | 찾을 수 없음·테스트 비활성 | 없는 요청 ID, 비활성 Test API |
| `409` | 상태 충돌 | 수동 재처리 최대 2회 초과 |
| `422` | 입력 검증·Provider 비재시도 오류 | 잘못된 요청 스키마, 지원하지 않는 테스트 시나리오 |
| `503` | 일시적 제공자 오류 | 카카오 장소 후보 또는 외부 Provider 일시 장애 |

## 3. 공통 데이터 모델

### 3.1 좌표 `Point`

```json
{
  "lat": 37.4765,
  "lng": 126.9816,
  "source": "kakao_candidate"
}
```

| 필드 | 형식 | 제약 | 설명 |
| --- | --- | --- | --- |
| `lat` | number | 37.0 이상, 38.0 이하 | 위도 |
| `lng` | number | 126.5 이상, 127.5 이하 | 경도 |
| `source` | string | 선택 | 좌표 출처. 기본값 `map` |

### 3.2 충전기 타입·상태

| 필드 | 허용 값 | 설명 |
| --- | --- | --- |
| `connector_types` | `FAST`, `SLOW` | 급속, 완속. 최소 1개 필요 |
| `availability.state` | `AVAILABLE`, `DELAYED`, `UNAVAILABLE`, `CANDIDATE_ONLY` | Critic 검증 결과 |
| `critic_decision` | `PASS`, `SAFE_UNAVAILABLE` | 검색 결과 전체의 품질 판정 |
| `status` | `completed`, `degraded` | 검색 완료 또는 안전한 제한 결과 |

### 3.3 SearchRequest

```json
{
  "request_id": "req-8f2...",
  "origin": "chat",
  "center": {"lat": 37.4765, "lng": 126.9816, "source": "kakao_candidate"},
  "radius_km": 1.0,
  "connector_types": ["FAST"],
  "region_filters": ["zscode:11650"],
  "requested_at": "2026-11-09T10:00:00+09:00",
  "user_confirmed": true,
  "intent": "find_charger",
  "policy_version": "1.0-preview"
}
```

| 필드 | 설명 |
| --- | --- |
| `origin` | `chat`, `sidebar`, `initial_default` 중 하나 |
| `radius_km` | 실제 검색 반경. UI 표시 1·2·3 km는 각각 `0.5`, `1.0`, `1.5` km로 변환 |
| `region_filters` | 서울 행정구역 필터. 선택 값 |
| `user_confirmed` | 채팅 후보·조건 확인 여부 |

## 4. 상태 확인·인증 API

### 4.1 백엔드 상태 확인

`GET /healthz`

**인증:** 없음

**성공 응답 — 200**

```json
{
  "status": "ok",
  "service": "chargepin-backend"
}
```

Docker Compose healthcheck와 배포 스크립트가 사용하는 기본 상태 확인 API다.

### 4.2 로그인

`POST /api/v1/auth/login`

**인증:** 없음

**요청 본문**

```json
{
  "service_key": "사용자가 입력한 서비스 키"
}
```

| 필드 | 형식 | 제약 |
| --- | --- | --- |
| `service_key` | string | 1~200자 |

**성공 응답 — 200**

```json
{
  "access_token": "발급된_토큰",
  "token_type": "bearer",
  "role": "GUEST",
  "expires_at": "2026-11-09T14:00:00+09:00"
}
```

이후 요청은 아래 헤더를 사용한다.

```http
Authorization: Bearer <access_token>
```

## 5. 검색·장소 API

### 5.1 첫 진입 기본 검색

`POST /api/v1/search/default`

**인증:** 로그인 사용자

**요청 본문:** 없음

강남역 중심, 표시 범위 1 km(실제 반경 0.5 km), 급속·완속 전체 조건으로 검색한다.

**성공 응답 — 200:** [5.3 검색 실행](#53-사이드바-직접-검색)의 `SearchResponse` 형식

### 5.2 카카오 장소 후보 검색

`POST /api/v1/places/suggest`

**인증:** 로그인 사용자

**요청 본문**

```json
{
  "query": "사당역"
}
```

| 필드 | 형식 | 제약 | 설명 |
| --- | --- | --- | --- |
| `query` | string | 2~100자 | 사용자 장소 입력 |

**성공 응답 — 200**

```json
[
  {
    "candidate_id": "kakao-place-id",
    "name": "사당역",
    "category": "지하철역",
    "address": "서울특별시 동작구 동작대로",
    "location": {"lat": 37.4765, "lng": 126.9816, "source": "kakao_candidate"},
    "district_code": "11620"
  }
]
```

- Executor가 카카오 응답을 정규화하고 서울 주소 후보만 반환한다.
- 결과가 비어 있으면 빈 배열 `[]`을 반환한다.
- 일시적 Provider 오류는 `503`, 인증·형식 오류는 `422`로 반환한다.

### 5.3 사이드바 직접 검색

`POST /api/v1/search`

**인증:** 로그인 사용자

**요청 본문**

```json
{
  "center": {"lat": 37.4765, "lng": 126.9816, "source": "kakao_candidate"},
  "radius_km": 1.0,
  "connector_types": ["FAST", "SLOW"],
  "region_filters": ["zscode:11620"]
}
```

| 필드 | 형식 | 필수 | 제약 |
| --- | --- | --- | --- |
| `center` | `Point` | 예 | 서울 좌표 범위 |
| `radius_km` | number | 아니오 | `0.5`, `1.0`, `1.5`; 기본 `0.5` |
| `connector_types` | string[] | 아니오 | `FAST`, `SLOW`, 중복 제거; 빈 배열 불가 |
| `region_filters` | string[] | 아니오 | 서울 행정구역 필터 |

**성공 응답 — 200**

```json
{
  "request_id": "req-8f2...",
  "status": "completed",
  "applied_request": {"...": "SearchRequest"},
  "results": [
    {
      "facility_id": "KECO-001",
      "name": "예시 충전소",
      "address": "서울특별시 동작구 예시로 1",
      "location": {"lat": 37.4765, "lng": 126.9816, "source": "KECO_EV"},
      "distance_km": 0.3,
      "facility_type": "공공시설",
      "connector_types": ["FAST"],
      "availability": {
        "state": "AVAILABLE",
        "available_chargers": 1,
        "total_chargers": 2,
        "label": "충전 가능 1/2",
        "reason": null
      },
      "source": "KECO_EV",
      "reported_at": "2026-11-09T09:55:00+09:00",
      "fetched_at": "2026-11-09T10:00:00+09:00",
      "use_time": "24시간",
      "parking_free": null,
      "restriction_detail": null
    }
  ],
  "critic_decision": "PASS",
  "critic_findings": []
}
```

`DELAYED` 또는 `UNAVAILABLE` 결과에서는 `available_chargers`, `total_chargers`가 `null`일 수 있다. 프론트는 이를 빈자리 `0`으로 해석하면 안 된다.

### 5.4 검색 결과 조회

`GET /api/v1/search/{request_id}`

**인증:** 로그인 사용자

| 경로 변수 | 설명 |
| --- | --- |
| `request_id` | 검색 처리 ID |

**성공 응답 — 200:** `SearchResponse`와 동일

**오류 — 404:** 결과가 없거나 백엔드 재기동으로 프로세스 메모리가 초기화된 경우

## 6. AI 채팅 계획·확정 API

### 6.1 자연어 계획 생성

`POST /api/v1/chat/plan`

**인증:** 로그인 사용자

**요청 본문**

```json
{
  "message": "사당역 근처 두 키로 급속 충전소 찾아줘"
}
```

| 필드 | 형식 | 제약 |
| --- | --- | --- |
| `message` | string | 1~500자 |

**성공 응답 — 200: 후보·조건 확인 필요**

```json
{
  "request_id": "req-8f2...",
  "status": "AWAITING_CONFIRMATION",
  "message": "사당역 주변 검색 범위 2 km (반경 1 km)에서 급속 충전소를 찾을까요?",
  "search_request": {"...": "user_confirmed=false인 SearchRequest"},
  "candidates": [{"...": "PlaceCandidate"}],
  "suggested_candidate_id": "kakao-place-id"
}
```

**상태 값**

| `status` | 의미 | 프론트 동작 |
| --- | --- | --- |
| `AWAITING_CONFIRMATION` | 구체적 장소의 조건 확인 대기 | 확인 후 `/confirm` 호출 |
| `AWAITING_LOCATION_CONFIRMATION` | 서울·강남처럼 모호한 장소의 후보 선택 대기 | 후보 2개 표시, 하나 선택 후 `/confirm` 호출 |
| `NEEDS_INPUT` | 장소 누락, 범위 초과, LLM 처리 실패 등 | 안내 문구와 함께 재입력 유도 |
| `BLOCKED` | 가드레일 차단 | 안전 안내만 표시, 검색 API 미호출 |

Planner는 명확한 장소·숫자 조건을 규칙으로 빠르게 처리한다. 문맥형 조건 변경·한글 수량 해석에만 LLM을 사용하며, LLM은 외부 장소·충전기 API를 호출하지 않는다.

### 6.2 채팅 검색 확정

`POST /api/v1/search/{request_id}/confirm`

**인증:** 로그인 사용자. 계획을 만든 동일 세션이어야 한다.

**요청 본문**

```json
{
  "confirmed": true,
  "candidate_id": "kakao-place-id"
}
```

| 필드 | 형식 | 기본값 | 설명 |
| --- | --- | --- | --- |
| `confirmed` | boolean | `true` | `false`면 검색 취소 |
| `candidate_id` | string/null | `null` | 후보 선택 값. 생략 시 1순위 후보 사용 |

**성공 응답 — 200**

- `confirmed=true`: `SearchResponse`
- `confirmed=false`: `ChatPlanResponse` (`NEEDS_INPUT`, 검색 취소 안내)

**오류 — 404:** request_id가 없거나 다른 세션의 계획을 확정하려는 경우

## 7. 운영 대시보드 API

모든 운영 API는 `JUNIOR_ADMIN` 또는 `SENIOR_ADMIN` 역할이 필요하다. 화면의 팝업과 별개로 백엔드도 `403`으로 권한을 다시 확인한다.

### 7.1 운영 요약

`GET /api/v1/ops/summary`

**성공 응답 — 200**

```json
{
  "scope": "backend_process",
  "metrics": {
    "search_count": 10,
    "completed_count": 8,
    "degraded_count": 2,
    "guardrail_block_count": 1,
    "guardrail_category_counts": {
      "PROMPT_OVERRIDE": 0,
      "SECRET_REQUEST": 1,
      "OTHER_USER_DATA": 0,
      "PRIVILEGE_CHANGE": 0
    },
    "retry_count": 2,
    "quality_issue_count": 1
  },
  "providers": [{"name": "환경공단 충전기", "status": "설정됨"}],
  "recent_events": [],
  "recent_provider_errors": [],
  "cache": {"...": "캐시 snapshot"}
}
```

값의 범위는 현재 백엔드 프로세스다. 컨테이너를 재기동하면 메모리 기반 요청·운영 이력은 초기화된다.

### 7.2 Compose 플랫폼 상태

`GET /api/v1/ops/platform`

**성공 응답 — 200**

```json
{
  "source": "compose",
  "observed_at": "2026-11-09T01:00:00+00:00",
  "namespace": "docker-compose",
  "workloads": [
    {"kind": "ComposeService", "name": "backend", "desired": 1, "ready": 1, "liveness": "/healthz"},
    {"kind": "ComposeService", "name": "frontend", "desired": 1, "ready": 1, "liveness": "/_stcore/health"}
  ],
  "services": [],
  "config": []
}
```

Docker socket을 직접 노출하지 않고, backend에서 관측 가능한 health endpoint 상태만 반환한다.

### 7.3 Auto Healing 상태

`GET /api/v1/ops/healing`

**성공 응답 — 200**

```json
{
  "policy": {
    "mode": "dry-run",
    "consecutive_unhealthy": 2,
    "cooldown_seconds": 120,
    "window_seconds": 600,
    "max_restarts": 3,
    "recovery_timeout_seconds": 120,
    "scope": []
  },
  "events": [
    {
      "timestamp_utc": "2026-11-09T01:00:00+00:00",
      "event": "recovered",
      "container": "aio2_p3_chargepin-frontend-1",
      "duration_seconds": 8.48
    }
  ]
}
```

`events`는 읽기 전용 Auto Healing JSONL 로그에서 검증 가능한 항목만 최대 200개 반환한다.

### 7.4 요청 재처리

`POST /api/v1/ops/requests/{request_id}/retry`

**인증:** 운영자

**요청 본문:** 없음

**성공 응답 — 200:** 재실행된 `SearchResponse`

| 오류 | 의미 |
| --- | --- |
| `404` | 재처리 대상 요청이 없음 |
| `409` | 요청별 수동 재처리 한도 2회를 모두 사용 |

자동 재시도와 수동 재처리 횟수는 별도로 Handoff에 기록한다.

### 7.5 캐시 갱신

`POST /api/v1/ops/cache/refresh`

**인증:** 운영자

**요청 본문:** 없음

**성공 응답 — 200**

```json
{
  "status": "completed",
  "...": "현재 캐시 snapshot"
}
```

캐시 무효화 사실과 실행 역할은 운영 이벤트에 기록한다.

## 8. 테스트·시연 API

테스트 API는 일반 사용자 흐름과 분리돼 있다. 운영 환경에서는 반드시 비활성화한다.

### 8.1 Test API 공통 조건

| 조건 | 값 |
| --- | --- |
| 환경 변수 | `CHARGEPIN_ENABLE_FAULT_INJECTION=true` |
| 역할 | `SENIOR_ADMIN` |
| 비활성 상태 | `404` |

### 8.2 활성 시나리오 조회

`GET /api/v1/test/faults`

**성공 응답 — 200**

```json
{
  "test_only": true,
  "active": "timeout",
  "scenarios": ["executor_exception", "invalid_count", "llm_invalid_schema", "normal", "stale", "timeout"]
}
```

### 8.3 시나리오 활성화

`POST /api/v1/test/faults/{scenario}`

| 경로 변수 | 허용 값 |
| --- | --- |
| `scenario` | `normal`, `stale`, `invalid_count`, `timeout`, `executor_exception`, `llm_invalid_schema` |

**성공 응답 — 200**

```json
{
  "test_only": true,
  "active": "timeout"
}
```

지원하지 않는 시나리오는 `422`다.

### 8.4 시나리오 초기화

`POST /api/v1/test/faults/reset`

**성공 응답 — 200**

```json
{
  "test_only": true,
  "active": null
}
```

### 8.5 화면 상태 시연

`GET /boom/{scenario}`

**인증:** 로그인 사용자

**환경 조건:** `CHARGEPIN_ENABLE_TEST_SCENARIOS=true`

| scenario | HTTP 상태 | `code` | 화면 목적 |
| ---: | ---: | --- | --- |
| `1` | 200 | `NO_RESULTS` | 결과 없음 |
| `2` | 200 | `DATA_DELAYED` | 정보 지연 |
| `3` | 429 | `RATE_LIMITED` | 요청 제한 |
| `4` | 401 | `PROVIDER_AUTH_EXPIRED` | 제공자 인증 만료 시연 |
| `5` | 503 | `AI_CHAT_UNAVAILABLE` | AI 챗 연결 실패 |

**응답 예시**

```json
{
  "test_only": true,
  "scenario": 3,
  "code": "RATE_LIMITED",
  "message": "현재 요청이 많아 잠시 후 다시 시도해 주세요."
}
```

`/boom/4`의 401은 사용자 세션이 틀렸다는 뜻이 아니라, **제공자 인증 만료 화면을 보여 주기 위한 시연 응답**이다.

## 9. 보안·클라이언트 구현 규칙

1. 프론트엔드는 `service_key`를 로그인 요청에만 보내고 저장·출력하지 않는다.
2. API 응답·대시보드·Handoff에 환경 변수, API 키, access token, 차단 원문을 넣지 않는다.
3. `BLOCKED` 응답은 재검색·Provider 호출을 유발하지 않는다.
4. `available_chargers` 또는 `total_chargers`가 `null`이면 값이 없거나 신뢰할 수 없다는 뜻이다.
5. 검색 결과·운영 이력은 프로세스 메모리 기반이므로 request_id는 컨테이너 재기동 이후 유지되지 않는다.
6. Test API는 테스트 후 반드시 reset하고 환경 변수도 다시 비활성화한다.

## 10. 프론트엔드 호출 순서

### 지도·사이드바

`로그인 → /places/suggest → 후보 선택 → /search`

### AI 채팅

`로그인 → /chat/plan → 후보·조건 확인 → /search/{request_id}/confirm`

### 운영 대시보드

`로그인(관리자) → /ops/summary + /ops/platform + /ops/healing → 필요 시 /retry 또는 /cache/refresh`

