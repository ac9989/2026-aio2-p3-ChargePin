"""Run the three required fault scenarios repeatedly against a local test backend.

This is an evidence runner, not a production operation tool.  The target
backend must explicitly enable fault injection and use a senior-manager key.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


SEARCH_BODY = {
    "center": {"lat": 37.498, "lng": 127.027},
    "radius_km": 0.5,
    "connector_types": ["FAST", "SLOW"],
    "region_filters": [],
}
SCENARIOS = ("timeout", "executor_exception", "llm_invalid_schema")
EXPECTED_RETRY_DELTAS = {
    "timeout": 2,
    "executor_exception": 2,
    "llm_invalid_schema": 2,
}


def request(base_url: str, method: str, path: str, *, token: str | None = None, body: dict | None = None) -> tuple[int, dict]:
    payload = json.dumps(body).encode("utf-8") if body is not None else None
    headers = {"Accept": "application/json"}
    if payload is not None:
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        with urlopen(Request(f"{base_url}{path}", data=payload, method=method, headers=headers), timeout=50) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except HTTPError as error:
        try:
            return error.code, json.loads(error.read().decode("utf-8"))
        except json.JSONDecodeError:
            return error.code, {"detail": "응답 형식을 읽을 수 없습니다."}
    except URLError as error:
        raise RuntimeError("백엔드에 연결하지 못했습니다. Docker Compose 실행 상태를 확인해 주세요.") from error


def main() -> int:
    parser = argparse.ArgumentParser(description="ChargePin fault-recovery evidence runner")
    parser.add_argument("--base-url", default=os.environ.get("CHARGEPIN_TEST_BASE_URL", "http://127.0.0.1:8000"))
    parser.add_argument("--repeat", type=int, default=3, choices=range(1, 11))
    parser.add_argument("--output", default="artifacts/fault-recovery-evidence.json")
    args = parser.parse_args()

    service_key = os.environ.get("CHARGEPIN_TEST_OPERATOR_KEY", "").strip()
    if not service_key:
        raise SystemExit("CHARGEPIN_TEST_OPERATOR_KEY에 상급 관리자 서비스 키를 설정해 주세요.")

    status, login = request(args.base_url, "POST", "/api/v1/auth/login", body={"service_key": service_key})
    if status != 200 or not isinstance(login.get("access_token"), str):
        raise SystemExit("상급 관리자 로그인에 실패했습니다. 테스트 키를 확인해 주세요.")
    token = login["access_token"]
    records: list[dict] = []

    for scenario in SCENARIOS:
        for run_no in range(1, args.repeat + 1):
            before_status, before = request(args.base_url, "GET", "/api/v1/ops/summary", token=token)
            if before_status != 200:
                raise SystemExit("운영 요약을 읽지 못했습니다. 테스트 API 설정을 확인해 주세요.")
            before_retries = int(before.get("metrics", {}).get("retry_count", 0))
            activate_status, activated = request(args.base_url, "POST", f"/api/v1/test/faults/{scenario}", token=token)
            if activate_status != 200:
                raise SystemExit(f"{scenario} 장애 주입 활성화에 실패했습니다: {activated.get('detail', '알 수 없는 오류')}")

            try:
                if scenario == "llm_invalid_schema":
                    response_status, response = request(
                        args.base_url,
                        "POST",
                        "/api/v1/chat/plan",
                        token=token,
                        body={"message": "사당역 근처 두 키로 급속으로 찾아 줘"},
                    )
                    passed = response_status == 200 and response.get("status") == "NEEDS_INPUT"
                    request_id = response.get("request_id")
                    verdict = response.get("status")
                else:
                    response_status, response = request(args.base_url, "POST", "/api/v1/search", token=token, body=SEARCH_BODY)
                    request_id = response.get("request_id")
                    verdict = response.get("critic_decision")
                    passed = response_status == 200 and response.get("status") == "degraded" and verdict == "SAFE_UNAVAILABLE"

                after_status, after = request(args.base_url, "GET", "/api/v1/ops/summary", token=token)
                retry_delta = int(after.get("metrics", {}).get("retry_count", 0)) - before_retries if after_status == 200 else None
                passed = passed and retry_delta == EXPECTED_RETRY_DELTAS[scenario]
                records.append({
                    "scenario": scenario,
                    "run": run_no,
                    "occurred_at": datetime.now(timezone.utc).isoformat(),
                    "request_id": request_id,
                    "http_status": response_status,
                    "verdict": verdict,
                    "retry_delta": retry_delta,
                    "passed": passed,
                })
            finally:
                request(args.base_url, "POST", "/api/v1/test/faults/reset", token=token)

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps({"repeat": args.repeat, "records": records}, ensure_ascii=False, indent=2), encoding="utf-8")
    failed = [record for record in records if not record["passed"]]
    print(f"증빙 결과: {len(records) - len(failed)}/{len(records)} 통과 → {output}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
