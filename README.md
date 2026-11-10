<p align="center">
  <img src="Frontend/docs/images/hero.png" alt="ChargePin — 묻는 대로, 확인된 만큼" width="100%">
</p>

<h1 align="center">ChargePin</h1>

<p align="center">
  <b>말로 찾고, 근거로 확인하는 서울 전기차 충전소 안내</b><br>
  엔코아 AI캠퍼스 AI 어플리케이션 2기 · 교과목 3 「멀티 에이전트 협업 및 서비스 운영」
</p>

<p align="center">
  <img alt="Frontend: Streamlit" src="https://img.shields.io/badge/Frontend-Streamlit-FF4B4B?logo=streamlit&logoColor=white">
  <img alt="Backend: FastAPI" src="https://img.shields.io/badge/Backend-FastAPI-009688?logo=fastapi&logoColor=white">
  <img alt="Deploy: Docker Compose" src="https://img.shields.io/badge/Deploy-Docker_Compose-2496ED?logo=docker&logoColor=white">
  <img alt="CI/CD: GitHub Actions" src="https://img.shields.io/badge/CI%2FCD-GitHub_Actions-2088FF?logo=githubactions&logoColor=white">
</p>

<p align="center">
  <a href="#overview"><b>프로젝트 소개</b></a> &nbsp;·&nbsp;
  <a href="#architecture"><b>아키텍처</b></a> &nbsp;·&nbsp;
  <a href="#dashboard"><b>운영 대시보드</b></a> &nbsp;·&nbsp;
  <a href="#deployment"><b>배포와 복구</b></a> &nbsp;·&nbsp;
  <a href="#quick-start"><b>시작하기</b></a> &nbsp;·&nbsp;
  <a href="#verification"><b>테스트</b></a>
</p>

---

<a id="overview"></a>

## ⚡ 말로 찾고, 근거로 확인합니다

충전소 위치를 찾은 뒤에도 확인할 것은 남습니다. 급속인지 완속인지, 어디까지 탐색할지, 표시된 상태는 언제 갱신됐는지까지 살펴야 합니다.

**ChargePin은 검색 조건을 말로 입력받고, 결과의 근거와 확인 범위를 함께 전달하기 위해 만들었습니다.** 사용자는 장소와 조건을 입력하고, 서비스는 서로 다른 출처의 정보를 조회·검증해 보여 줍니다.

<table>
  <tr>
    <td align="center" width="33%" valign="top">
      <h3 align="center">💬<br>말로 찾기</h3>
      <p align="center">장소와 조건을<br>대화로 입력합니다.</p>
    </td>
    <td align="center" width="33%" valign="top">
      <h3 align="center">🧭<br>이어 찾기</h3>
      <p align="center">직전 장소에서<br>범위만 바꿉니다.</p>
    </td>
    <td align="center" width="33%" valign="top">
      <h3 align="center">🛡️<br>상태 검증</h3>
      <p align="center">불확실한 상태를<br>따로 표시합니다.</p>
    </td>
  </tr>
</table>

<p align="center"><img src="Frontend/docs/images/highlights.png" alt="직전 장소를 이용한 범위 변경과 입력 가드레일 설명" width="100%"></p>

<sub>기능 설명용 도식입니다. 실제 운영 화면 캡처나 측정 수치를 나타내지 않습니다.</sub>

<details>
<summary><b>현재 제공하는 기능과 검색 범위</b></summary>

| 기능 | 현재 구현 |
|---|---|
| 기본 검색 | 로그인 후 강남역 주변 표시 범위 1 km, 급속·완속 전체로 첫 검색 |
| 자연어 검색 | 장소명·충전 방식·표시 범위 해석. 단순한 입력은 규칙, 필요한 입력은 Planner LLM 사용 |
| 직전 장소 기억 | 같은 로그인 세션에서 “3km” 등 조건만 바꾸는 후속 검색 지원. 문맥 해석에는 OpenAI 키 필요 |
| 장소 후보 | 백엔드가 카카오 후보를 최대 2개 조회. 현재 챗은 추천 후보로 자동 진행하고, 사이드바는 사용자가 후보 선택 |
| 상태 검증 | 비정상 수량·시각 누락·오래된 정보를 구분하고, 검증하지 못한 가용 수량은 숨김 |
| 운영 대시보드 | 관리자에게 요청 흐름·가드레일·안정성·배포·자가 점검 근거 제공 |

**화면의 1·2·3 km는 검색 범위의 지름입니다.** 외부 조회에 적용하는 반경은 각각 0.5·1.0·1.5 km입니다. 충전 상태는 제공처의 갱신 정보이며 현장의 즉시 이용 가능성을 보장하지 않습니다.

</details>

---

<a id="architecture"></a>

## 🧩 아키텍처 — 해석·조회·검증의 역할을 나누다

Streamlit 사용자 화면과 운영 대시보드가 FastAPI 백엔드에 연결되고, 백엔드가 카카오 장소·환경공단 충전기 데이터를 조회합니다. **해석·조회·검증·기록을 분리하고, 실행 순서와 재시도는 Orchestrator 코드가 제어합니다.**

<p align="center"><img src="Frontend/docs/images/architecture.png" alt="챗 검색과 기본·사이드바 검색이 공통 조회·검증으로 합류하는 검색 처리 흐름도" width="100%"></p>

| 설계 원칙 | 이 구조를 선택한 이유 |
|---|---|
| 해석과 조회의 분리 | Planner는 검색 조건만 만들고, Executor만 제공처를 조회해 모델이 충전 상태를 만들어 내는 경로를 줄입니다. |
| 출처별 의미의 분리 | 카카오는 장소·좌표, 환경공단은 충전기 상태·갱신 시각의 근거로 사용해 장소 후보와 실제 상태를 혼동하지 않습니다. |
| 조회 성공과 품질 검증의 분리 | API 응답이 성공해도 Critic이 수량·시각을 따로 검사합니다. 검증하지 못한 값은 추정하지 않고 표시를 제한합니다. |

시스템 구성·API·Handoff·정책의 상세 배경은 [아키텍처 설계서 1.2](docs/P3-1_Architecture_Design_1.2.md)에, 기능 범위는 [PRD 1.2](docs/PRD_1.2.md)에 정리되어 있습니다. 두 문서는 PostgreSQL 운영 이력, 구조화 파일 로그, Discord 실패 알림까지 포함한 현재 구현 기준입니다.

<details>
<summary><b>현재 구현의 역할·검색 경로·제약</b></summary>

| 역할 | 담당 작업 | 경계 |
|---|---|---|
| Planner | 장소명·표시 범위·충전 방식 구조화. 단순 입력은 규칙, 필요한 입력은 LLM 사용 | 제공처 API 도구 없음. LLM 오류·스키마 불일치 시 조회 중단 |
| Executor | 카카오 장소 후보, 환경공단 충전기 조회·정규화 | 근거 없는 장소·충전 상태 생성 금지 |
| Critic | 수량·갱신 시각 검증, `PASS` / `SAFE_UNAVAILABLE` 판정 | 외부 API 호출 없음. 실패 시 표시 상태 변경·가용 수량 숨김 |
| Memory Keeper | Handoff·재시도·감사 이벤트·직전 검색 조건 보관 | 프로세스 메모리에 보관하며 서버 재시작 후 유지되지 않음 |

- **챗:** 입력 가드레일 → Planner → 장소 후보 조회 → 프론트의 추천 후보 자동 확인 → 충전기 조회 → Critic.
- **첫 진입:** 강남역 기본 조건으로 충전기 조회·검증을 실행합니다.
- **사이드바:** 사용자가 장소 후보를 고르고 검색 버튼으로 직접 조회합니다. 챗 Planner는 거치지 않습니다.

백엔드에 `/search/{request_id}/confirm` 단계가 있지만 **현재 챗 UI는 이를 자동 호출합니다.** 별도 사용자 확인이나 챗 후보 선택 화면은 현재 제공하지 않으며, 장소 후보 조회는 확인 단계 이전에 수행합니다.

계획·실행·검증은 `request_id`로 연결합니다. Handoff와 채팅 문맥은 현재 백엔드 프로세스 범위이지만, 안전한 운영 이벤트는 PostgreSQL과 `logs/service.log`에 함께 남아 재기동 뒤에도 확인할 수 있습니다. DB가 잠시 꺼져도 검색 요청은 멈추지 않고 파일 로그와 메모리 폴백으로 처리합니다. 설계의 Circuit Breaker·중복 요청 제어·심층 헬스체크를 모두 구현한 상태는 아닙니다.

</details>

<details>
<summary><b>가드레일과 데이터 품질 정책</b></summary>

| 계층 | 구현 |
|---|---|
| 입력 | 시스템 지침 무시·비밀 요청·타인 데이터·권한 변경의 4개 범주를 규칙으로 검사. 챗 Planner 호출 전 차단 |
| 행동 | Planner에 제공처 어댑터를 주입하지 않고, 장소·충전기 제공처 호출을 Executor에 모음 |
| 출력 | 비정상 집계·시각 누락·최신성 기준 초과 시 `SAFE_UNAVAILABLE`로 판정하고 불확실한 수량을 숨김 |
| 접근 | 운영 API는 관리자만 허용하고, 테스트 장애 주입 API는 상급 관리자와 활성화 설정을 함께 요구 |

차단된 원문은 **서버 Handoff와 감사 이벤트에 저장하지 않습니다.** 사용자가 입력한 문장이 현재 화면의 대화 이력에서 사라진다는 뜻은 아닙니다.

최신성 기준은 `CHARGER_FRESHNESS_MINUTES`로 설정하며 기본값은 10,080분(7일)입니다. 현재 검증은 충전소 내 가장 최근 보고 시각을 사용합니다. 개별 충전기의 모든 상태가 실시간이라는 의미는 아닙니다.

구현: [에이전트·가드레일](Backend/app/agents.py) · [역할 인증](Backend/app/auth.py) · [API 접근 통제](Backend/app/main.py)

</details>

---

<a id="dashboard"></a>

## 📊 검색 화면 뒤의 운영도 살펴봅니다

이용자의 검색 흐름이 어디까지 진행됐는지, 무엇이 차단됐는지, 장애와 배포는 어떻게 대응하는지 확인합니다. 운영 개요부터 컴플라이언스까지 **운영자의 질문에 맞춘 여섯 메뉴**로 구성했습니다.

<p align="center"><img src="Frontend/docs/images/dashboard.png" alt="관리자 대시보드의 여섯 메뉴와 근거를 구분하는 자가 점검 구성도" width="100%"></p>

**운영 상태에도 근거를 붙입니다.** 현재 세션 관측·서버 조회·GitHub 조회·관리표 기록을 구분하고, 아직 연결하지 않은 항목은 연결 대기로 표시합니다.

검색·가드레일·재시도·Critic 판정·에이전트 오류는 PostgreSQL `operation_events`와 `logs/service.log`에 동일한 안전 메타데이터로 기록합니다. 오류 수준 기록만 `logs/errors.log`에 따로 남기며, 채팅 원문·서비스 키·토큰·API 키·제공처 원문 응답은 어느 저장소에도 기록하지 않습니다. 운영 개요는 DB 이력과 파일 로그 이력을 분리해 표시하고, DB 연결 실패 시 파일 로그를 계속 사용합니다.

<details>
<summary><b>관리자 권한·연결 범위·자가 점검 기준</b></summary>

| 역할 | 대시보드 | 요청 재처리·캐시 갱신 | 테스트 장애 주입 API | CSV 내보내기 |
|---|---|---|---|---|
| 손님 | 불가 | 불가 | 불가 | 불가 |
| 하급 관리자 | 조회 | 가능 | 불가 | 불가 |
| 상급 관리자 | 조회 | 가능 | 시험 환경에서 가능 | 가능 |

서버 운영 패널은 프론트의 `CHARGEPIN_DASHBOARD_SERVER_OPS=true` 설정과 백엔드 API 연결이 필요합니다. 개발·운영 Compose 모두 이 설정을 켜며, 운영 개요에서 PostgreSQL 누적 이력과 파일 로그 이력을 함께 확인할 수 있습니다. Watchdog 이력은 로그 연결 여부에 따라 표시합니다.

**컴플라이언스는 팀의 자가 점검입니다.** 18개 항목을 충족·구현·부분·미착수로 구분하고, 관측 근거가 생겼을 때 ‘구현’ 항목만 ‘충족’으로 올립니다. 관리표에는 과거 시점의 기록도 포함되므로 자동화 코드의 현재 상태와 구분해 읽어야 합니다.

항목 원본: [compliance_reference.json](Frontend/compliance_reference.json) · [자가 점검 설계](Frontend/design/dashboard_compliance_design.md)

</details>

---

<a id="deployment"></a>

## 🚀 테스트를 지나, 배포와 복구까지

**실패한 테스트가 배포로 이어지지 않도록 연결했습니다.** 테스트·이미지 빌드·GHCR 게시를 순서대로 묶고, `main`의 성공한 CI에서 SHA가 고정된 이미지로 배포를 진행합니다.

<p align="center"><img src="Frontend/docs/images/cicd.png" alt="테스트·빌드·GHCR 게시·AWS 자동 배포·헬스 검사와 실패 시 롤백 흐름" width="100%"></p>

신규 배포는 헬스체크를 통과해야 성공으로 기록합니다. 통과하지 못하면 이전 성공 SHA로 복구를 시도하며, 최초 배포에는 이전 버전이 없다는 조건을 함께 둡니다.

자동화 코드의 구현과 실제 서버 검증 범위는 [CD 설정·증빙](ops/CD_SETUP.md)에 구분해 정리했습니다.

<details>
<summary><b>파이프라인 조건과 장애 유형별 대응</b></summary>

개발은 [docker-compose.yml](docker-compose.yml), 운영은 [compose.prod.yml](compose.prod.yml)을 사용합니다. 운영 Compose는 SHA 이미지 고정, 헬스체크, `restart: unless-stopped`, 백엔드 준비 후 프론트 기동을 선언합니다.

1. 백엔드·프론트·운영 테스트와 Docker 롤백 통합검증을 수행합니다.
2. 선행 테스트가 모두 통과해야 Compose 검증과 두 이미지 빌드를 실행합니다.
3. `main` push의 성공한 CI에서 GHCR에 `latest`와 `sha-<commit>` 이미지를 게시합니다.
4. CD가 해당 CI 성공을 확인하고 AWS OIDC·SSM으로 EC2에 SHA 고정 이미지를 배포합니다.
5. 헬스체크를 최대 180초 기다린 뒤 성공 SHA를 기록합니다. 실패하면 이전 성공 SHA로 복구를 시도합니다.

**자동화 코드 구현과 실제 운영 검증은 구분합니다.** 기존 배포·검증 기록과 남은 검증 범위는 [CD 설정·증빙](ops/CD_SETUP.md)에 정리되어 있습니다. 최초 배포에는 이전 성공 SHA가 없어 자동 롤백 대상이 없으며, 복구 시도 자체가 실패하면 수동 조치가 필요합니다.

운영 Compose는 `CHARGEPIN_ENABLE_TEST_SCENARIOS=false`로 `/boom` 시연을 끕니다. 별도 Test API는 운영 `.env`에서도 `CHARGEPIN_ENABLE_FAULT_INJECTION=false`를 유지해야 합니다.

### 장애 유형별 대응

| 상황 | 대응과 범위 |
|---|---|
| 제공처의 일시 오류·429·5xx·응답 지연 | 충전기 조회 실행 중 자동 재시도 최대 2회, 대기 0.25·0.5초. 인증·형식 오류는 재시도하지 않음 |
| 운영자의 요청 재처리 | 요청별 수동 재처리 최대 2회 |
| LLM 해석 실패·스키마 오류 | `NEEDS_INPUT`으로 재입력 안내, 장소·충전기 조회 중단 |
| 제공처 인증 오류·검증 불가 데이터 | 안전 응답·정보 지연·확인 불가 표시 |
| 실행 중인 프론트가 연속 unhealthy | 별도 실행한 로컬 Watchdog가 감시·재시작 |
| 운영 컨테이너 프로세스 종료 | 운영 Compose의 `restart` 정책 적용. Watchdog는 정지한 컨테이너를 재시작하지 않음 |
| 신규 배포 헬스체크 실패 | 이전 성공 SHA가 있으면 자동 롤백 시도 |

</details>

<details>
<summary><b>로컬 Watchdog 실행</b></summary>

Watchdog는 Compose와 별도로 실행합니다. Python 환경을 준비하고 프론트 컨테이너가 실행 중인 상태에서 실제 컨테이너 ID를 확인합니다.

```powershell
$frontendContainer = docker compose ps -q frontend
py ops/autoheal.py --container $frontendContainer --once
py ops/autoheal.py --container $frontendContainer --watch
```

위 감시는 기본적으로 dry-run입니다. Ctrl+C로 종료한 뒤, 재시작을 적용할 때 같은 창에서 실행합니다.

```powershell
py ops/autoheal.py --container $frontendContainer --watch --apply
```

정책은 **실행 중인 unhealthy 2회 연속 관측**, 120초 쿨다운, 10분간 재시작 최대 3회입니다. 기본 감시 주기는 15초이며, healthy·starting·정지한 컨테이너는 재시작하지 않습니다. 현재 범위는 로컬 프론트이며 서버 상시 감시 서비스는 별도 구성 대상입니다.

자세한 동작과 로그 위치: [Watchdog 안내](ops/README.md)

</details>

---

<a id="quick-start"></a>

## 🛠️ 로컬에서 시작하기

Docker Desktop과 Docker Compose를 준비하고 저장소 최상위에서 실행합니다.

**① 환경 파일을 복사합니다.**

```powershell
Copy-Item .env.example .env
```

**② `.env`에 로그인 키와 제공처 키를 채웁니다.** 사용할 역할의 서비스 키, 카카오 REST 키, 환경공단 키가 필요합니다. 지도는 카카오 JavaScript 키와 등록 도메인을 사용하며, 문맥을 잇는 후속 검색에는 OpenAI 키가 필요합니다.

<details>
<summary><b>환경 변수와 지도 설정 자세히 보기</b></summary>

| 환경 변수 | 용도와 필요 범위 |
|---|---|
| `CUSTOMER_SERVICE_KEY` | 손님 로그인. 사용할 역할의 키는 반드시 설정 |
| `LOW_MANAGER_SERVICE_KEY` | 하급 관리자 로그인 |
| `HIGH_MANAGER_SERVICE_KEY` | 상급 관리자 로그인 |
| `KAKAO_REST_API_KEY` | 장소 후보 검색 |
| `KECO_SERVICE_KEY` | 공공데이터포털 데이터셋 `15076352`의 충전소·충전기 조회 |
| `KAKAO_JAVASCRIPT_KEY` | 브라우저 카카오 지도 표시 |
| `OPENAI_API_KEY` | 문맥을 잇는 후속 검색과 자연어 해석. 미설정 시 규칙 기반 장소 검색만 사용 |
| `OPENAI_PLANNER_MODEL` | Planner 모델. 기본값 `gpt-4o-mini` |
| `POSTGRES_DB` / `POSTGRES_USER` / `POSTGRES_PASSWORD` | 운영 이력을 저장하는 Compose PostgreSQL 계정. 운영 환경에서는 강한 비밀번호 필수 |

역할별 로그인 키는 서로 다르게 정합니다. 카카오 지도는 접속할 주소를 개발자 콘솔 Web 플랫폼에 등록해야 합니다. 로컬에서는 `http://localhost:8501`과 `http://127.0.0.1:8501`을 사용하는 주소에 맞게 등록합니다.

`CHARGEPIN_ENABLE_FAULT_INJECTION=false`를 유지합니다. 로컬 장애시험을 진행할 때만 별도로 켭니다. 실제 `.env`와 서비스 키는 Git에 올리지 않습니다.

</details>

**③ 서비스를 실행하고 설정한 역할의 키로 로그인합니다.**

```powershell
docker compose up --build
```

첫 화면에서 설정한 역할의 서비스 키로 로그인합니다. Compose는 `postgres` 컨테이너도 함께 실행하며 첫 API 요청 시 `operation_events` 테이블을 자동 생성합니다. 지도 키나 등록 도메인이 없으면 실제 지도를 표시할 수 없습니다. `/healthz`의 정상 응답은 백엔드 생존 확인이며 외부 API와 LLM의 정상 동작까지 증명하지 않습니다.

---

<a id="verification"></a>

## ✅ 동작을 확인하는 기준

코드에 정의된 테스트는 총 **85개**입니다. 세 묶음과 별도의 Docker 헬스체크·롤백 통합검증이 이미지 빌드의 선행 조건입니다.

| Backend | Frontend | Operations | 합계 |
|:---:|:---:|:---:|:---:|
| **48** | **24** | **13** | **85** |

필수 장애시험의 현재 대상은 **외부 API 지연·Executor 예외·LLM 스키마 오류 각 3회, 총 9회**입니다. 실행 도구는 [run_fault_evidence.py](Backend/scripts/run_fault_evidence.py)이며, 활성화·상급 관리자 인증·결과 수집 절차는 [Test API·Test Checker 안내](docs/Fault_Test_Guide.md)를 따릅니다.

`/boom/1~5`는 화면 문구 시연용이며, 실제 검색 흐름에 장애를 주입하는 Test API 검증을 대신하지 않습니다. 기존 로컬 Watchdog 1회·8.48초 기록도 필수 9회 장애시험 및 운영 서버의 복구 성능과 구분합니다.

<details>
<summary><b>로컬 테스트 실행 명령</b></summary>

Python 3.12 환경을 준비한 뒤 저장소 최상위에서 의존성을 설치합니다.

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r Backend/requirements.txt -r Frontend/requirements.txt

Push-Location Backend
..\.venv\Scripts\python.exe -m pytest -q
Pop-Location

Push-Location Frontend
..\.venv\Scripts\python.exe -m pytest -q
Pop-Location

.\.venv\Scripts\python.exe -m pytest -q tests/ops
```

</details>

---

## 📁 저장소 둘러보기

<details>
<summary><b>폴더별 역할과 주요 문서</b></summary>

```text
.
├── Backend/
│   ├── app/              # FastAPI · 역할별 처리 · 인증 · 제공처 어댑터
│   ├── tests/            # 검색·권한·복구·계약 검증
│   └── scripts/          # 장애시험 증빙 수집
├── Frontend/
│   ├── app.py            # Streamlit 사용자 화면·운영 화면 연결
│   ├── dashboard_view.py # 운영 대시보드
│   ├── tests/
│   ├── docs/images/      # 이 README의 이미지 5개
│   ├── compliance_reference.json
│   └── design/           # 화면·대시보드 설계
├── docs/
│   ├── PRD_1.2.md
│   ├── P3-1_Architecture_Design_1.2.md
│   └── Fault_Test_Guide.md
├── logs/                 # 구조화 운영 로그 (Git 미추적)
├── ops/                  # 배포·롤백 · 로컬 Watchdog
├── tests/ops/            # Watchdog·배포 정책 테스트
├── .github/workflows/    # CI · AWS SSM CD
├── .env.example
├── docker-compose.yml
└── compose.prod.yml
```

</details>

## 👥 함께 만든 사람들

| [박동준](https://github.com/DongJunee) | [신영석](https://github.com/WithAndWithout0094) | [조권식](https://github.com/ac9989) | [성관현](https://github.com/tsurien) |
|:---:|:---:|:---:|:---:|
| **팀장·PM** | **Backend·QA** | **DevOps** | **Frontend** |
| 백엔드 아키텍처 설계<br>보안 가드레일 | API 연동<br>데이터 검증·QA | Docker·GitHub Actions<br>AWS 배포·Auto Healing | 사용자 화면<br>운영 대시보드 |
| [📝 회고](docs/retrospectives/park-dongjun.md) | [📝 회고](docs/retrospectives/shin-youngseok.md) | [📝 회고](docs/retrospectives/jo-kwonsik.md) | [📝 회고](docs/retrospectives/seong-gwanhyeon.md) |

## 🗺️ 다음에 채워 갈 것들

- 필수 장애시험 9회, CI 고의 실패 차단, 실패 알림 수신의 실행 증빙 확보
- `main` 자동 배포와 실제 서버 장애 롤백 검증, 서버 상시 감시 구성
- 요청·감사 이력의 영속 저장과 서버 범위 지표 연결
- 챗 후보 선택·사용자 확인 흐름 보완
- 신뢰할 수 있는 데이터를 확보한 뒤 운영 시간·외부인 이용·차종별 커넥터·충전 요금 조건 확장

<sub>기능·구현 범위 기준: 2026-11-09 · 소스 0bd94fe. 관리표의 과거 기록, 코드 구현, 실제 실행 증빙을 구분해 기술합니다.</sub>
