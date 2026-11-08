# 백엔드 전달: 운영 대시보드 개편(가드레일 · 컴플라이언스 · Kubernetes · Auto Healing)

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
| `Frontend/dashboard_view.py` | 메뉴 6개로 재구성, 서버 화면 3종(정책 판정 서버 집계 · Kubernetes 매니페스트 · Auto Healing) 추가 |
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

### T2. `GET /api/v1/ops/platform` 신규 — 2~3시간

**목표:** 배포 파이프라인 메뉴 ‘Kubernetes 매니페스트’ 표와 컴플라이언스 R-2 실시간 근거.

**응답 계약** (`Frontend/ops_contract.py`와 동일):

```json
{
  "source": "kubernetes",
  "observed_at": "2026-11-09T01:00:00Z",
  "namespace": "chargepin",
  "workloads": [
    {"kind": "Deployment", "name": "chargepin-backend", "desired": 1, "ready": 1, "restarts": 0,
     "image": "ghcr.io/ac9989/chargepin-backend:sha-<commit>", "liveness": "/healthz", "readiness": "/healthz"},
    {"kind": "Deployment", "name": "chargepin-frontend", "desired": 2, "ready": 2, "restarts": 0,
     "image": "ghcr.io/ac9989/chargepin-frontend:sha-<commit>", "liveness": "/_stcore/health", "readiness": "/_stcore/health"}
  ],
  "services": [
    {"name": "chargepin-backend", "type": "ClusterIP", "port": 8000, "endpoints": 1},
    {"name": "chargepin-frontend", "type": "LoadBalancer", "port": 80, "endpoints": 2}
  ],
  "config": [
    {"kind": "Secret", "name": "chargepin-secrets", "keys": 7},
    {"kind": "ConfigMap", "name": "chargepin-config", "keys": 5}
  ]
}
```

**구현 힌트:**
- 클러스터 안에서는 `kubernetes` 파이썬 클라이언트 `config.load_incluster_config()`로 같은 namespace의 Deployment · Service · Endpoints · ConfigMap · Secret을 조회.
- `restarts` = 해당 Deployment 파드들의 `containerStatuses[].restartCount` 합.
- **Secret은 `metadata`와 키 개수만.** `data` 값은 응답 · 로그 어디에도 넣지 않습니다. 프론트도 값이 오면 버리지만, 서버에서 먼저 막아야 합니다.
- RBAC는 최소 권한: ServiceAccount `chargepin-ops` + Role(`get`,`list` on deployments, pods, services, endpoints, configmaps; secrets는 `get`을 이름 `chargepin-secrets` 하나로 제한).
- 클러스터 밖(현재 EC2 · Compose)에서는 **503**을 돌려주세요. 프론트는 ‘연결 대기’로 표시합니다. 숫자를 만들어 넣지 마세요.

**완료 조건:** 비관리자 403 · 클러스터 밖 503 · Secret 값 미포함 테스트 3개.

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
- **Kubernetes:** 생존 프로브 실패로 인한 재시작 이벤트(`kubectl get events` 의 `Killing`/`Started`, 또는 `restartCount` 증가)를 같은 형식으로 변환. `policy`에는 프로브 설정(`failureThreshold` → `consecutive_unhealthy`, `periodSeconds` 등)을 넣고 `mode`는 `"apply"`.
- 프론트의 자동 복구율 = `recovered 수 / restart_attempt 수`. 이벤트가 없으면 카드가 관리표 기록(8.48초 1회)으로 돌아갑니다.

**완료 조건:** 비관리자 403 · 로그 없음이면 `events: []` · 잘못된 줄은 건너뜀 테스트.

### T4. Kubernetes 매니페스트 — 2~3시간 (DevOps)

`k8s/` 폴더에 아래를 작성해 주세요. 대시보드 표의 기대 리소스 이름과 같아야 화면이 맞습니다.

| 리소스 | 이름 | 필수 설정 |
|---|---|---|
| Namespace | `chargepin` | |
| ConfigMap | `chargepin-config` | `OPENAI_PLANNER_MODEL`, `KECO_INFO_CACHE_TTL_SECONDS`, `KECO_STATUS_CACHE_TTL_SECONDS`, `CHARGER_FRESHNESS_MINUTES`, `CHARGEPIN_ENABLE_TEST_SCENARIOS=false` |
| Secret | `chargepin-secrets` | `KECO_SERVICE_KEY`, `KAKAO_REST_API_KEY`, `OPENAI_API_KEY`, `CUSTOMER_SERVICE_KEY`, `LOW_MANAGER_SERVICE_KEY`, `HIGH_MANAGER_SERVICE_KEY`, `KAKAO_JAVASCRIPT_KEY`. **저장소에는 `secret.example.yaml`(빈 값)만 커밋** |
| Deployment | `chargepin-backend` | image `ghcr.io/ac9989/chargepin-backend:sha-…`, port 8000, liveness · readiness `GET /healthz`, **replicas 1** (아래 제약 참고) |
| Service | `chargepin-backend` | ClusterIP 8000 |
| Deployment | `chargepin-frontend` | image `ghcr.io/ac9989/chargepin-frontend:sha-…`, port 8501, liveness · readiness `GET /_stcore/health`, env `CHARGEPIN_API_BASE_URL=http://chargepin-backend:8000/api/v1`, `KAKAO_JAVASCRIPT_KEY`(Secret에서), `CHARGEPIN_DASHBOARD_SERVER_OPS=true` |
| Service | `chargepin-frontend` | LoadBalancer(또는 NodePort) 80 → 8501, **`sessionAffinity: ClientIP`** |
| ServiceAccount · Role · RoleBinding | `chargepin-ops` | T2의 최소 권한 |

**제약 (현재 구조상 불가능한 것):**
- 백엔드 레플리카 2개 이상은 **지금 구조로는 안 됩니다.** 로그인 세션 · 핸드오프 · 대화 조건이 `store.py` 프로세스 메모리에 있어서, 요청이 다른 파드로 가면 확인 단계가 404가 됩니다. 늘리려면 Redis 같은 공유 저장소가 먼저 필요합니다.
- 프론트 레플리카 2개는 가능하지만 Streamlit 세션이 웹소켓에 묶여 있어 **고정 세션(sessionAffinity)이 필수**입니다.

**완료 조건:** `kubectl apply --dry-run=server -f k8s/` 통과(또는 kubeconform), 적용 후 `/ops/platform`이 두 Deployment 모두 ready를 보고. 그 다음 `Frontend/compliance_reference.json`의 **R-2 `status`를 `"구현"`으로** 바꾸면 대시보드가 실시간 근거로 ‘충족’을 표시합니다.

### T5. Auto Healing 배포 환경 적용 — 1시간 (DevOps)

- Compose/EC2: `ops/autoheal.py --watch --apply`를 systemd 서비스로 상시 실행, 로그를 T3에 연결.
- Kubernetes: 생존 프로브가 L1을 대신하므로 watcher는 필요 없음. 이벤트 수집만 T3에 연결.
- 적용 후 `compliance_reference.json`의 **R-5 `status`를 `"구현"`으로.** 실제 복구 이벤트가 생기면 대시보드가 ‘충족’으로 올립니다.

### T6. 증빙 작업 (점검표 ‘미착수’)

| 점검 ID | 작업 | 완료 시 JSON 변경 |
|---|---|---|
| R-6 | 필수 장애시험 FT-01~04 각 3회, 결과를 관리표와 `/ops/healing` 이벤트로 | `status` → `"구현"` 또는 `"충족"`, `evidence`에 결과 |
| C-2 | 고의 실패 커밋으로 build · publish 생략 실행 기록 | `"충족"`, `evidence`에 run URL |
| C-4 | 실패 알림 채널 · 담당자 · 에스컬레이션 시간 | `"구현"` 이상 |

---

## 3. 문서에 반영할 변경

### 아키텍처 설계서

- **운영 관측 경로 추가:** 프론트 대시보드 → `GET /api/v1/ops/{summary, platform, healing}` (관리자 전용). 세 경로 모두 읽기 전용.
- **힐링 계층 명시:** L1 재시작(Watchdog / K8s 생존 프로브) → L2 재처리(503 안내 · 관리자 재처리 최대 2회) → L3 안전 응답(Critic SAFE_UNAVAILABLE · LLM 실패 시 검색 중단) → L4 사람(알림 · 에스컬레이션).
- **배포 토폴로지:** 현재 EC2 + Compose(수동 반영), 목표 Kubernetes(위 T4 리소스). 백엔드 단일 레플리카 제약과 이유.
- **데이터 보호:** Secret은 키 개수만 노출, 프론트 이벤트는 키 · 토큰 · 질의 원문 · 응답 문구 미기록.

### PRD

- 운영 대시보드 메뉴 6개와 각 메뉴의 질문(설계 문서 2절).
- 권한: 일반 이용자 진입 불가 · 하급 관리자 전체 조회 · 상급 관리자 조회 + 권한 안내 + **컴플라이언스 리포트 CSV 내보내기**.
- 모든 값에 기준(현재 세션 · 코드 기준 · 관리표 기록 · GitHub 실시간 · 서버 보고 · 연결 대기) 표시, 없는 수치 미생성.

### 테스트 시나리오 (추가 제안)

| ID | 시나리오 | 기대 결과 |
|---|---|---|
| DB-01 | 하급 관리자가 `/ops/platform` · `/ops/healing` 호출 | 200 (관리자) / 일반 이용자 403 |
| DB-02 | `/ops/platform` 응답에 Secret `data` 포함 여부 | 키 개수만, 값 없음 |
| DB-03 | 클러스터 밖에서 `/ops/platform` | 503, 대시보드 ‘연결 대기’ |
| DB-04 | autoheal 로그에 `restart_attempt` 2건 · `recovered` 1건 | 대시보드 자동 복구율 50.0% |
| DB-05 | 입력 가드레일 4범주 각 1회 차단 | `guardrail_category_counts` 각 1, 대시보드 ‘서버 차단’ 1 |
| DB-06 | 하급 관리자 컴플라이언스 CSV 내보내기 | 버튼 비활성 · 안내 |
| DB-07 | `CHARGEPIN_DASHBOARD_SERVER_OPS` 미설정 | 서버 화면 모두 ‘연결 대기’, 오류 없음 |
| DB-08 | `/ops/healing` 타임아웃(5초 초과) | 해당 패널만 ‘연결 대기’, 다른 메뉴 정상 |

---

## 4. 연결 확인 순서

1. 백엔드에서 T1~T3 구현 후 관리자 토큰으로 `curl -H "Authorization: Bearer <token>" http://localhost:8000/api/v1/ops/healing`.
2. 프론트 환경 변수 `CHARGEPIN_DASHBOARD_SERVER_OPS=true` (Compose는 `docker-compose.yml`의 frontend `environment`에 추가).
3. 대시보드 → 가드레일(서버 집계 · 서버 차단), 안정성·힐링(정책 ‘서버 보고’ · 이벤트 표), 배포 파이프라인(매니페스트 표)이 ‘연결 대기’에서 값으로 바뀌는지 확인.
4. 프론트 테스트: `cd Frontend; py -m unittest tests.test_dashboard_data tests.test_chat_guidance tests.test_ops_contract -v`.

## 5. 하지 말아야 할 것

- 응답에 Secret 값 · API 키 · 토큰 · 사용자 원문 · 차단된 원문을 넣지 않기.
- 데이터가 없을 때 0이나 예시 값으로 채우지 않기. 503 또는 빈 배열로 보내면 프론트가 ‘연결 대기’로 표시합니다.
- 엔드포인트에서 대시보드용으로 클러스터를 변경(재시작 · 스케일)하지 않기. 세 경로는 모두 읽기 전용입니다.
