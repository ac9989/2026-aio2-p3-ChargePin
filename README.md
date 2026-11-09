# ChargePin 1.0 초기 구현

현재 개발 중인 ChargePin 초기 실행 버전이다. 기능 요구사항은 `docs/PRD.md`를 참고한다. 팀원이 만든 기존 Streamlit 시연 화면의 따뜻한 노랑·우드 톤, 카드형 검색 패널, 큰 지도, 운영 대시보드 구성을 새 아키텍처에 맞춰 재구성했다.

## 구성

```text
Backend/
  app/          FastAPI, Planner·Executor·Critic·Memory Keeper
  tests/        초기 단위 테스트
Frontend/
  app.py        Streamlit 사용자·운영 대시보드 UI
  api_client.py 백엔드 API 클라이언트
docker-compose.yml
```

## 1.0 포함 범위

- 첫 진입 시 강남역 주변 지름 1 km(반경 0.5 km), 급속·완속 전체 자동 검색
- 첫 화면의 서비스 키 로그인과 손님·하급 관리자·상급 관리자 역할 세션
- 충전소 중심 검색과 `충전 가능 n/전체 m` 표시
- 모호한 `서울`·`강남` 입력에 대한 카카오 장소 후보 상위 2개와 1순위 제안
- Planner → Executor → Critic → Memory Keeper 논리 역할과 Handoff 메모리
- 손님·하급 관리자·상급 관리자 UI 시연 규칙과 안내 팝업
- 테스트 전용 `/boom/1`~`/boom/5`

## 실제 연동과 시연 범위의 경계

- 카카오 장소 후보는 서버가 `KAKAO_REST_API_KEY`로 실제 키워드 장소 검색 API를 호출한다.
- 자연어 조건은 백엔드 Planner가 `OPENAI_API_KEY`의 `gpt-4o-mini`로 구조화한다. Planner에는 장소·충전 상태 API 도구가 없고, 실제 조회는 사용자 확인 뒤 Executor만 수행한다.
- 충전소·충전기 상태는 서버가 `KECO_SERVICE_KEY`로 환경공단 `getChargerInfo`와 `getChargerStatus`를 호출한다.
- 지도는 `KAKAO_JAVASCRIPT_KEY`와 카카오 개발자 콘솔의 등록 도메인이 설정된 경우 실제 카카오 지도를 사용한다. 둘 중 하나가 없으면 예시 지도로 폴백한다.
- 운영 대시보드와 역할 변경/재처리/정책 버튼은 실제 운영 시스템을 변경하지 않는다.
- 외부인 이용 여부와 빈자리 예측은 제공하지 않는다.

## 실행

Docker가 있다면 프로젝트 폴더에서 다음을 실행한다.

```powershell
Copy-Item .env.example .env
docker compose up --build
```

- 프런트: `http://localhost:8501`
- 백엔드 문서: `http://localhost:8000/docs`
- 상태 확인: `http://localhost:8000/healthz`

`.env`는 프로젝트 최상위 폴더에 둔다. 실제 키는 커밋하지 않으며, 처음에는 `.env.example`을 복사해 사용한다. `KECO_SERVICE_KEY`에는 데이터셋 `15076352`의 활용 신청이 완료된 공공데이터포털 서비스키를, `KAKAO_REST_API_KEY`에는 카카오 REST API 키를 넣는다. Planner를 실제 LLM으로 쓰려면 `OPENAI_API_KEY`를 넣고, 기본 모델은 `OPENAI_PLANNER_MODEL=gpt-4o-mini`이다. 지도까지 실제로 보려면 `KAKAO_JAVASCRIPT_KEY`와 카카오 콘솔 Web 플랫폼의 `http://127.0.0.1:8501` 등록이 필요하다. `localhost`로 접속할 때는 `http://localhost:8501`도 별도로 등록한다.

첫 화면에서는 `.env`의 `CUSTOMER_SERVICE_KEY`, `LOW_MANAGER_SERVICE_KEY`, `HIGH_MANAGER_SERVICE_KEY` 중 하나를 입력한다. 백엔드가 키를 비교해 짧은 역할 세션을 발급하며, 서비스 키·환경공단 키·카카오 REST 키는 프런트 컨테이너에 전달하지 않는다.

로컬 실행은 각각의 폴더에서 의존성을 설치한 뒤 실행한다.

```powershell
cd Backend
py -m pip install -r requirements.txt
py -m uvicorn app.main:app --reload
```

새 터미널에서:

```powershell
cd Frontend
$env:CHARGEPIN_API_BASE_URL = "http://localhost:8000/api/v1"
py -m pip install -r requirements.txt
py -m streamlit run app.py
```

## 기본 검증

```powershell
cd Backend
py -m pytest -q

cd ..\Frontend
py -m pytest -q

cd ..
py -m pytest -q tests/ops
```

테스트 전용 장애 주입과 실행 증빙 절차는 [Test API · Test Checker 안내](docs/Fault_Test_Guide.md)를 따른다. `CHARGEPIN_ENABLE_FAULT_INJECTION`은 로컬 테스트에서만 켠다.
