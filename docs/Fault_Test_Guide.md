# Test API · Test Checker 실행 안내

## 목적

실제 카카오·환경공단·LLM을 호출하지 않고, 고정된 장애 응답을 실제 검색 흐름에 주입한다. Test Checker는 응답, Critic 판정, 자동 재시도, Handoff, 운영 요약을 함께 확인한다.

`/boom/1~5`는 화면 문구 시연용이며 아래 장애 복구 검증을 대신하지 않는다.

## 테스트 API 안전 경계

- 경로: `GET /api/v1/test/faults`, `POST /api/v1/test/faults/{scenario}`, `POST /api/v1/test/faults/reset`
- 조건: `.env`의 `CHARGEPIN_ENABLE_FAULT_INJECTION=true`일 때만 동작한다.
- 권한: 상급 관리자 세션만 사용할 수 있다.
- 기본값: `.env.example`은 `false`다. AWS 배포 환경에서는 반드시 `false`를 유지한다.
- 이 API는 프런트 사용자 화면에 연결하지 않는다.

## Test Checker 시나리오

| ID | Test API scenario | Test Checker 판정 |
|---|---|---|
| 정상 | `normal` | `PASS`, 정상 가용성 카드 |
| 데이터 품질 | `stale` | `SAFE_UNAVAILABLE`, `DELAYED`, 가용 수치 숨김, 재시도 없음 |
| 데이터 품질 | `invalid_count` | `SAFE_UNAVAILABLE`, `UNAVAILABLE`, 가용 수치 숨김, 재시도 없음 |
| FT-01 | `timeout` | 최초 호출 뒤 자동 재시도 2회, 총 3회 시도 후 안전 응답·재시도 이력 2건 |
| FT-02 | `executor_exception` | HTTP 500이 아닌 안전 응답, `executor_exception` 감사 이력 |
| FT-04 | `llm_invalid_schema` | `NEEDS_INPUT`, `llm_plan_error`, 장소 Provider 미호출 |

## 자동 검사

```powershell
cd Backend
py -m pytest -q tests/test_fault_recovery.py
```

## 내일 실행 증빙

1. 로컬 `.env`에만 아래 값을 추가한 뒤 Compose를 재시작한다.

```text
CHARGEPIN_ENABLE_FAULT_INJECTION=true
```

2. PowerShell 현재 창에만 상급 관리자 서비스 키를 설정한다. 이 값은 파일이나 Git에 저장하지 않는다.

```powershell
$env:CHARGEPIN_TEST_OPERATOR_KEY = "상급_관리자_서비스_키"
```

3. 각 필수 장애를 3회씩 실행하고 결과 JSON을 만든다.

```powershell
py Backend/scripts/run_fault_evidence.py --repeat 3
```

4. 생성된 `artifacts/fault-recovery-evidence.json`과 운영 대시보드의 재시도·오류 이력을 캡처한다.

5. 증빙 후 `.env`의 `CHARGEPIN_ENABLE_FAULT_INJECTION`을 다시 `false`로 바꾸고 Compose를 재시작한다.
