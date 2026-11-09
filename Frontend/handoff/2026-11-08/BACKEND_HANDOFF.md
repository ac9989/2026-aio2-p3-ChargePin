# 백엔드 전달: 운영 대시보드 개편(가드레일 · 컴플라이언스 · Docker Compose · Auto Healing)

- 작성일: 2026-11-08 (발표 2026-11-09)
- 작성: 프론트엔드(성관현)
- 받는 사람: 백엔드 · DevOps 담당 (박동준, 신영석, 조권식)
- 이 문서는 챗봇에 그대로 넣어 작업을 시작할 수 있도록 썼습니다. 각 작업에 **목표 · 계약 · 완료 조건**이 있습니다.

---

## 0. 한 줄 요약

프론트 대시보드는 6개 메뉴(운영 개요 · 에이전트 처리 · 가드레일 · 안정성·힐링 · 배포 파이프라인 · 컴플라이언스)로 바뀌었고, 서버 데이터가 필요한 화면은 **이미 만들어져 ‘연결 대기’로 표시 중**입니다. 백엔드가 아래 엔드포인트 3개를 제공하고 프론트 컨테이너에 `CHARGEPIN_DASHBOARD_SERVER_OPS=true`만 넣으면 화면이 채워집니다.

| 엔드포인트 | 상태 | 쓰는 메뉴 |
|---|---|---|
| `GET /api/v1/ops/summary` | **이미 있음** (`agents.py operations_summary`). 필드 1개 추가 요청 | 가드레일 · 안정성·힐링 |
| `GET /api/v1/ops/platform` | **신규** | 배포 파이프라인 · 컴플라이언스 · 운영 개요 |
| `GET /api/v1/ops/healing` | **신규** | 안정성·힐링 · 컴플라이언스 · 운영 개요 |

세 엔드포인트 모두 `require_operator`(관리자 전용, 비관리자 403)를 붙여 주세요.

---

## 1. 프론트에서 바뀐 것

### 1.1 파일

| 파일 | 변경 |
|---|---|
| `Frontend/dashboard_view.py` | 메뉴 6개로 재구성, 서버 화면 3종(정책 판정 서버 집계 · Docker Compose 서비스 상태 · Auto Healing) 추가 |
| `Frontend/dashboard_data.py` | 오류 분리(4xx/5xx/연결 실패), 가드레일 집계(차단·통과), 헬스 ok/degraded/down, 컴플라이언스 판정 계산 |
| `Frontend/ops_contract.py` | **신규.** 서버 응답 계약과 정규화(허용 필드만 통과, Secret 값 폐기), 자동 복구율 계산 |
| `Frontend/compliance_reference.json` | **신규.** 평가 기준 자가 점검 18개 항목 |
| `Frontend/api_client.py` | 검색 응답에서 `critic_decision` · 지적 수 · 충전 상태별 건수만 기록(문구 미기록). `ops_summary / ops_platform / ops_healing` 메서드 추가 |
| `Frontend/app.py` | `CHARGEPIN_DASHBOARD_SERVER_OPS=true`일 때만 서버 화면 로더 연결 |
| `Frontend/redesign_theme.py` | 상태 태그 · 단계 흐름 · 표 · 6개 메뉴 헤더 반응형 |
| `Frontend/tests/test_ops_contract.py` 외 | 테스트 24개 통과 |
| `Frontend/design/dashboard_compliance_design.md` | 설계 문서(목적 · 지표 · 권한 · 데이터 소스 · 성능 · 확장 구조) |
| `Frontend/backup_2026-11-08_before_compliance/` | 수정 전 백업. **커밋하지 말 것** (`.dockerignore`에 `backup_*/` 추가함, `.gitignore`는 루트라 손대지 않음) |

### 1.2 백엔드 API 호출 변화

- 사용자 화면의 호출은 **변화 없음**. 응답 형식도 그대로 사용합니다.
- 대시보드가 새로 읽는 기존 응답 필드: `SearchResponse.critic_decision`, `critic_findings`(개수만), `results[].availability.state`(개수만), `ChatPlanResponse.status`(BLOCKED 등).
- 이 필드 이름이나 값(`PASS` · `SAFE_UNAVAILABLE`, `AVAILABLE` · `DELAYED` · `UNAVAILABLE` · `CANDIDATE_ONLY`, `AWAITING_CONFIRMATION` · `AWAITING_LOCATION_CONFIRMATION` · `NEEDS_INPUT` · `BLOCKED`)을 바꾸면 대시보드 집계가 0이 됩니다. 바꿀 때는 프론트에 알려 주세요.

---

## 2. 백엔드 작업 (우선순위 순)

### T1. `/api/v1/ops/summary`에 범주별 차단 수 추가 — 30분

**목표:** 가드레일 메뉴 ‘입력 차단 정책’ 표의 ‘서버 차단’ 칸 채우기.

**변경:** `operations_summary()`의 `metrics`에 아래 키 추가. 값은 `memory.operation_events` 중 `event_type == "guardrail"`의 `category` 집계.

```json
"metrics": {
  "...기존 키 유지...": 0,
  "guardrail_category_counts": {"PROMPT_OVERRIDE": 0, "SECRET_REQUEST": 0, "OTHER_USER_DATA": 0, "PRIVILEGE_CHANGE": 0}
}
```

**완료 조건:** 네 범주 키가 항상 존재(0 포함). 차단 원문은 응답에 없음. 기존 키(`guardrail_block_count`, `completed_count`, `degraded_count`, `retry_count`)는 그대로.

### T2. `GET /api/v1/ops/platform` 신규 — Docker Compose 상태

**목표:** 배포 파이프라인 메뉴 ‘Docker Compose 서비스 상태’ 표와 컴플라이언스 R-2 실시간 근거.

**응답 계약** (`Frontend/ops_contract.py`와 동일):

```json
{
  "source": "compose",
  "observed_at": "2026-11-09T01:00:00Z",
  "namespace": "docker-compose",
  "workloads": [
    {"kind": "ComposeService", "name": "backend", "desired": 1, "ready": 1, "restarts": null,
     "image": "ghcr.io/ac9989/chargepin-backend:sha-<commit>", "liveness": "/healthz", "readiness": "/healthz"},
    {"kind": "ComposeService", "name": "frontend", "desired": 1, "ready": 1, "restarts": null,
     "image": "ghcr.io/ac9989/chargepin-frontend:sha-<commit>", "liveness": "/_stcore/health", "readiness": "/_stcore/health"}
  ],
  "services": [
    {"name": "backend", "type": "Compose network", "port": 8000, "endpoints": 1},
    {"name": "frontend", "type": "Compose network", "port": 8501, "endpoints": 1}
  ],
  "config": [
    {"kind": "RuntimeConfig", "name": "backend runtime configuration", "keys": 5}
  ]
}
```

**구현 힌트:**
- 백엔드는 자신의 `/healthz`와 Compose 네트워크의 Frontend `/_stcore/health`를 확인해 준비 상태를 보고합니다.
- Docker socket이나 컨테이너 제어 권한을 백엔드에 주지 않습니다. 재시작 횟수·이미지 태그처럼 관측할 수 없는 값은 `null`로 둡니다.
- 런타임 설정은 비밀값을 제외한 설정 수만 표시하고, 키·토큰·`.env` 값은 응답과 로그에 넣지 않습니다.

**완료 조건:** 비관리자 403 · Frontend 상태 변화 반영 · 비밀값 미포함 테스트.

### T3. `GET /api/v1/ops/healing` 신규 — 1~2시간

**목표:** 안정성·힐링 메뉴의 ‘Auto Healing 정책’ · ‘힐링 이벤트’ · ‘자동 복구율’(P3-2 ③) 카드.

**응답 계약:**

```json
{
  "policy": {"mode": "apply", "consecutive_unhealthy": 2, "cooldown_seconds": 120, "window_seconds": 600,
             "max_restarts": 3, "recovery_timeout_seconds": 120, "scope": ["chargepin-frontend"]},
  "events": [
    {"timestamp_utc": "2026-11-09T01:00:00+00:00", "event": "restart_attempt", "container": "chargepin-frontend"},
    {"timestamp_utc": "2026-11-09T01:00:09+00:00", "event": "recovered", "container": "chargepin-frontend", "duration_seconds": 8.48}
  ]
}
```

- `event`는 `ops/autoheal.py`가 이미 쓰는 이름 그대로: `restart_attempt` · `recovered` · `recovery_timeout` · `restart_failed` · `state_changed` · `recovery_interrupted`.
- **Compose/EC2:** `ops/logs/autoheal.jsonl`을 백엔드 컨테이너에 읽기 전용으로 마운트하고(`AUTOHEAL_LOG_PATH`), 최근 200줄을 그대로 돌려주면 됩니다. `policy`는 watcher 실행 인자와 같게.
- 프론트의 자동 복구율 = `recovered 수 / restart_attempt 수`. 이벤트가 없으면 ‘기록된 힐링 이벤트 없음’으로 표시하며, 예시 수치를 만들지 않습니다.

**완료 조건:** 비관리자 403 · 로그 없음이면 `events: []` · 잘못된 줄은 건너뜀 테스트.

### T4. Auto Healing 배포 환경 적용 — 1시간 (DevOps)

- Compose/EC2: `ops/autoheal.py --watch --apply`를 systemd 서비스로 상시 실행, 로그를 T3에 연결.
- 적용 후 `compliance_reference.json`의 **R-5 `status`를 `"구현"`으로.** 실제 복구 이벤트가 생기면 대시보드가 ‘충족’으로 올립니다.

### T6. 증빙 작업 (점검표 ‘미착수’)

| 점검 ID | 작업 | 완료 시 JSON 변경 |
|---|---|---|
| R-6 | 필수 장애시험 FT-01·FT-02·FT-04 각 3회, 결과를 관리표와 `/ops/healing` 이벤트로 | `status` → `"구현"` 또는 `"충족"`, `evidence`에 결과 |
| C-2 | 고의 실패 커밋으로 build · publish 생략 실행 기록 | `"충족"`, `evidence`에 run URL |
| C-4 | 실패 알림 채널 · 담당자 · 에스컬레이션 시간 | `"구현"` 이상 |

---

## 3. 문서에 반영할 변경

### 아키텍처 설계서

- **운영 관측 경로 추가:** 프론트 대시보드 → `GET /api/v1/ops/{summary, platform, healing}` (관리자 전용). 세 경로 모두 읽기 전용.
- **힐링 계층 명시:** L1 재시작(Docker Compose Health Check · Watchdog) → L2 재처리(일시 제공처 오류 자동 재시도 최대 2회 · 관리자 수동 재처리 별도 최대 2회) → L3 안전 응답(Critic SAFE_UNAVAILABLE · LLM 실패 시 검색 중단) → L4 사람(알림 · 에스컬레이션).
- **배포 토폴로지:** AWS EC2 + Docker Compose(수동 반영). Backend·Frontend는 각각 단일 Compose 서비스로 운영한다.
- **데이터 보호:** 운영 API에는 비밀값을 넣지 않고, 프론트 이벤트는 키 · 토큰 · 질의 원문 · 응답 문구를 기록하지 않는다.

### PRD

- 운영 대시보드 메뉴 6개와 각 메뉴의 질문(설계 문서 2절).
- 권한: 일반 이용자 진입 불가 · 하급 관리자 전체 조회 · 상급 관리자 조회 + 권한 안내 + **컴플라이언스 리포트 CSV 내보내기**.
- 모든 값에 기준(현재 세션 · 코드 기준 · 관리표 기록 · GitHub 실시간 · 서버 보고 · 연결 대기) 표시, 없는 수치 미생성.

### 테스트 시나리오 (추가 제안)

| ID | 시나리오 | 기대 결과 |
|---|---|---|
| OD-01 | 하급 관리자가 `/ops/platform` · `/ops/healing` 호출 | 200 (관리자) / 일반 이용자 403 |
| OD-02 | `/ops/platform` 응답에 비밀값 포함 여부 | 설정 수만, 값 없음 |
| OD-03 | Frontend Health Check 실패 상태의 `/ops/platform` | frontend `ready: 0`, 대시보드 ‘부분’ |
| OD-04 | autoheal 로그에 `restart_attempt` 2건 · `recovered` 1건 | 대시보드 자동 복구율 50.0% |
| OD-05 | 입력 가드레일 4범주 각 1회 차단 | `guardrail_category_counts` 각 1, 대시보드 ‘서버 차단’ 1 |
| OD-06 | 하급 관리자 컴플라이언스 CSV 내보내기 | 버튼 비활성 · 안내 |
| OD-07 | `CHARGEPIN_DASHBOARD_SERVER_OPS` 미설정 | 서버 화면 모두 ‘연결 대기’, 오류 없음 |
| OD-08 | `/ops/healing` 타임아웃(5초 초과) | 해당 패널만 ‘연결 대기’, 다른 메뉴 정상 |

---

## 4. 연결 확인 순서

1. 백엔드에서 T1~T3 구현 후 관리자 토큰으로 `curl -H "Authorization: Bearer <token>" http://localhost:8000/api/v1/ops/healing`.
2. 프론트 환경 변수 `CHARGEPIN_DASHBOARD_SERVER_OPS=true` (Compose는 `docker-compose.yml`의 frontend `environment`에 추가).
3. 대시보드 → 가드레일(서버 집계 · 서버 차단), 안정성·힐링(정책 ‘서버 보고’ · 이벤트 표), 배포 파이프라인(Docker Compose 서비스 표)이 ‘연결 대기’에서 값으로 바뀌는지 확인.
4. 프론트 테스트: `cd Frontend; py -m unittest tests.test_dashboard_data tests.test_chat_guidance tests.test_ops_contract -v`.

## 5. 하지 말아야 할 것

- 응답에 Secret 값 · API 키 · 토큰 · 사용자 원문 · 차단된 원문을 넣지 않기.
- 데이터가 없을 때 0이나 예시 값으로 채우지 않기. 503 또는 빈 배열로 보내면 프론트가 ‘연결 대기’로 표시합니다.
- 엔드포인트에서 대시보드용으로 Compose 컨테이너를 변경(재시작 등)하지 않기. 세 경로는 모두 읽기 전용입니다.
