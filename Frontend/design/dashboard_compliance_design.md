# ChargePin 운영 대시보드 설계: 가드레일 · 컴플라이언스 리포트 기준

- 작성일: 2026-11-08
- 적용 범위: `Frontend/dashboard_view.py`, `dashboard_data.py`, `api_client.py`, `compliance_reference.json`
- 이전 버전: GitHub 브랜치(origin/Sgh 등)와 `Frontend/backup_2026-11-08_before_compliance/`

## 1. 비즈니스 목적

운영 대시보드는 "서비스가 살아 있는가"가 아니라 아래 세 질문에 답합니다.

1. **에이전트가 정해진 경계 안에서 일했는가** — Planner는 해석만, Executor만 외부 API 호출, Critic이 확인되지 않은 정보를 막았는가.
2. **문제가 생겼을 때 감지하고 복구할 수 있는가** — 요청 측 오류와 서버 측 오류를 나누고, 장애 유형마다 대응이 정해져 있는가.
3. **위 내용을 증빙으로 보여줄 수 있는가** — 평가 기준(P3-1 · P3-2 · P3-3)마다 구현 여부와 실행 증빙을 구분해 리포트로 내보낼 수 있는가.

이용자 편의(자연어 → 검색 조건 → 확인된 충전소)는 사용자 화면이 담당하고, 대시보드는 그 과정이 안전하고 재현 가능하게 운영되는지를 보여줍니다.

## 2. 메뉴 구조 (변경 전 → 변경 후)

| 변경 전 | 변경 후 | 운영자의 질문 |
|---|---|---|
| 운영 개요 | **운영 개요** | 지금 상태는? 무엇부터 조치해야 하나? |
| 요청 정보 | **에이전트 처리** | 요청이 Planner → Executor → Critic을 어떻게 지나갔나? |
| (없음) | **가드레일** | 무엇이 막혔고 무엇이 통과했나? 오류는 요청 측인가 서버 측인가? |
| 서비스 안정성 | **안정성·힐링** | 의존성 상태는? 장애 유형별로 어떻게 대응하나? |
| 빌드·배포 | **배포 파이프라인** | 어느 게이트에서 멈췄나? 무엇이 수동인가? |
| (없음) | **컴플라이언스** | 평가 기준별로 무엇이 증빙되었고 무엇이 비어 있나? |

명칭 원칙: 화면 이름은 운영자의 질문, 내부 용어는 에이전트 역할명(Planner · Executor · Critic · Memory Keeper)과 판정값(PASS · SAFE_UNAVAILABLE)을 그대로 씁니다.

## 3. 메뉴별 핵심 지표

| 메뉴 | 지표 카드 | 패널 |
|---|---|---|
| 운영 개요 | 서비스 상태(/healthz) · 서버 측 오류율 · 가드레일 판정 건수 · 증빙 확보(충족/전체) | 검색 요청 추이(선) · 조치 필요 항목(실시간 이상 → 미착수 → 부분) · 최근 요청 · 외부 연결 · 파이프라인 |
| 에이전트 처리 | 챗 해석 · 충전소 검색 · Critic 판정(PASS/SAFE_UNAVAILABLE) · 검색 응답 시간 | 처리 단계 6단(요청 → Planner → 입력 가드레일 → Executor → Critic → 응답) · Planner 판정 분포(막대) · 충전 상태 판정 구성(도넛) · 요청 ID 추적표 |
| 가드레일 | 입력 검사(차단/통과) · 출력 검증(안전 응답/PASS) · 접근 거부(401·403) · 품질 경고 수 | 계층별 정책 판정(입력·행동·출력·접근 × 현재 세션 · 서버 집계 · 판정) · 오류 분리(4xx/5xx/연결 실패) · 입력 차단 정책 목록(Policy as Code) |
| 안정성·힐링 | 헬스 체크(ok·degraded·down) · 응답 시간 · 서버 측 오류율 · 자동 복구율(힐링 이벤트) | Auto Healing 정책 · 힐링 이벤트 · 힐링 계층 L1~L4 · 응답 시간 추이 · 의존성 상태 · 장애 유형별 대응 |
| 배포 파이프라인 | 최근 실행 · 테스트 게이트 · 이미지 게시 · EC2 배포 | 단계별 정책 게이트 5단 · Docker Compose 서비스 상태·Health Check · 최근 실행 · 실패 처리 · 증빙 |
| 컴플라이언스 | 충족 · 구현 · 부분 · 미착수 건수 | 영역 필터 · 리포트 표(ID · 점검 항목 · 통제 · 판정 · 근거 · 출처) · CSV 내보내기 · 판정 기준 |

판정 기준: **충족**(구현 + 실행 증빙) · **구현**(코드·문서만) · **부분** · **미착수**. 실시간 신호는 '구현'만 '충족'으로 올리고, 부분 · 미착수는 바꾸지 않습니다.

## 4. 사용자 권한

| 역할 | 사용자 화면 | 대시보드 조회 | 권한 안내 | 리포트 내보내기 |
|---|---|---|---|---|
| 일반 이용자 | O | X | X | X |
| 하급 관리자 | O | 전체 메뉴 | 안내만 | X (버튼 비활성 + 안내) |
| 상급 관리자 | O | 전체 메뉴 | O | O |

화면 권한은 표시 제어일 뿐이고, 운영 API(`/api/v1/ops/*`)는 서버에서 403으로 다시 검증합니다.

## 5. 데이터 소스와 수집 주기

| 소스 | 범위 | 갱신 | 사용 메뉴 |
|---|---|---|---|
| 프론트 세션 이벤트 (`st.session_state.api_events`) | 현재 브라우저 세션 · 최근 100건 | 요청마다 | 개요 · 에이전트 처리 · 가드레일 · 안정성 |
| `/healthz` | 백엔드 프로세스 | 화면 렌더마다 (timeout 5초) | 개요 · 안정성 · 컴플라이언스 |
| GitHub Actions 공개 API | 최근 20개 실행 · 작업 | 120초 캐시, 갱신 버튼으로 즉시 | 개요 · 배포 · 컴플라이언스 |
| `deployment_reference.json` | 배포·운영 관리표 사본(2026-11-05) | 수동 갱신 | 안정성 · 배포 |
| `compliance_reference.json` | 자가 점검 항목 18개 | 수동 갱신 | 개요 · 컴플라이언스 |
| `GET /api/v1/ops/summary` (기존 API) | 백엔드 프로세스 전체 | 메뉴 진입 시 (timeout 5초) | 가드레일 · 안정성·힐링 |
| `GET /api/v1/ops/platform` (백엔드 신규) | Docker Compose 서비스 · 네트워크 · 런타임 설정 수 | 메뉴 진입 시 | 배포 파이프라인 · 컴플라이언스 |
| `GET /api/v1/ops/healing` (백엔드 신규) | Auto Healing 정책 · 이벤트 | 메뉴 진입 시 | 안정성·힐링 · 컴플라이언스 |

세션 이벤트에는 키 · 토큰 · 질의 원문 · 응답 본문 · Critic 지적 문구를 저장하지 않습니다. 저장하는 값은 경로, 시각, 결과, 상태 코드, 요청 ID, 판정값, 건수뿐입니다.

## 6. 조회 성능

- 계산은 `dashboard_data.py`의 순수 함수에서 100건 이하로만 수행합니다(O(n), 화면 렌더당 1회).
- GitHub 조회는 선택한 메뉴가 필요할 때만(개요 · 배포 · 컴플라이언스) 호출하고 120초 캐시합니다.
- 서버 집계를 연결할 때는 렌더마다 호출하지 말고 `st.cache_data(ttl=30)` 이상으로 감싸고, 실패하면 '연결 대기'로 표시합니다.
- 서버 범위 이력이 커지면 백엔드에서 기간 · 건수를 잘라 반환합니다(예: 최근 20건, 최근 24시간).

## 7. 컴포넌트와 확장 구조

```
api_client.py         관측 이벤트 생성 (값 검증, 민감 정보 제외)
dashboard_data.py     계산 전용: summarize_events · guardrail_summary · health_label
                      · evaluate_compliance · compliance_score · action_items
compliance_reference.json   점검 항목 데이터 (코드 수정 없이 항목 추가)
dashboard_view.py     화면 전용: 공통 컴포넌트 + 메뉴별 view 함수
redesign_theme.py     공통 스타일 (cp-status · cp-stage-flow · cp-table · cp-action-list)
```

- 공통 컴포넌트: `metric_card` · `metric_row` · `line_chart` · `bar_chart` · `donut_chart` · `stage_flow` · `policy_table` · `action_list` · `status_tag`.
- 메뉴 추가: `MENUS` · `MENU_SCOPES`에 이름을 넣고 view 함수를 하나 추가합니다.
- 점검 항목 추가: `compliance_reference.json`의 `items`에 한 줄 추가합니다. 실시간 근거가 있으면 `live` 키(health · guardrail_session · critic_session · trace_session · ci_tests)를 붙입니다.
- 서버 집계 연결: `render_operations_dashboard(..., server_summary_loader=...)` 인자 하나로 연결합니다. 백엔드 전달 문서 `handoff/2026-11-08/BACKEND_HANDOFF.md` 참고.

## 8. 서버 연결 방법 (백엔드 작업 후 한 줄로 켜기)

- 프론트는 세 서버 화면을 이미 갖추고 있습니다. 응답 형식은 `Frontend/ops_contract.py` 상단 주석이 계약입니다.
- 백엔드가 세 엔드포인트를 제공하면 프론트 컨테이너에 `CHARGEPIN_DASHBOARD_SERVER_OPS=true`만 넣으면 됩니다. 값이 없거나 호출이 실패하면 각 패널은 ‘연결 대기’로 남습니다.
- 정규화 함수가 정해진 필드만 받고, Secret 값 · 자유 문구는 버립니다. 자동 복구율은 `recovered / restart_attempt` 이벤트로만 계산합니다.

## 9. 현재 구조에서 프론트만으로는 불가능한 것

| 항목 | 이유 | 담당 |
|---|---|---|
| Compose 서비스 상태 표시 | 브라우저 · 프론트 컨테이너는 Docker 호스트 상태를 직접 읽지 않음 | 백엔드 `/ops/platform` |
| 힐링 이벤트 · 자동 복구율 | `ops/autoheal.py` 로그는 호스트에만 있음 | 백엔드 `/ops/healing` |
| 범주별 입력 차단 · 재처리 이력 | 서버 감사 이벤트에만 있음 | 기존 `/ops/summary` 확장 |
| 백엔드 레플리카 2개 이상 | 핸드오프 · 로그인 세션이 프로세스 메모리에 있음 | 공유 저장소 도입 후 가능 |
| 프론트 다중 인스턴스 | Streamlit 세션이 웹소켓 연결에 묶임 | 현재 단일 Compose 서비스 유지 |

## 10. 남은 공백 (화면에서 '연결 대기'로 표시)

- 범주별 입력 차단 건수(서버 감사 이벤트의 category)
- Memory Keeper 단계별 Handoff 기록과 재시도 이력
- 의존성별 심층 헬스(ok · degraded · down)
- 필수 장애시험 12회, CI 실패 차단 실증, 실패 알림 수신
