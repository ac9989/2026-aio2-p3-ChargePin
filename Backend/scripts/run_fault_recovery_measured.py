"""AWS isolated-backend drill: fault handling + measured post-reset functional recovery.

WARNING: The reset is explicitly performed by this test harness. These metrics
do NOT establish autonomous upstream repair or watchdog container recovery.
Run only against an isolated backend with fault injection enabled.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
from time import monotonic
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

SEARCH = {
    "center": {"lat": 37.498, "lng": 127.027},
    "radius_km": 0.5,
    "connector_types": ["FAST", "SLOW"],
    "region_filters": [],
}
LLM_MESSAGE = "사당역 근처 두 키로 급속으로 찾아 줘"
SCENARIOS = ("timeout", "executor_exception", "llm_invalid_schema")


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def call(base: str, method: str, path: str, token: str = "", body: dict | None = None) -> tuple[int, dict]:
    payload = json.dumps(body).encode("utf-8") if body is not None else None
    headers = {"Accept": "application/json"}
    if token:
        headers["Authorization"] = "Bearer " + token
    if payload is not None:
        headers["Content-Type"] = "application/json"
    try:
        with urlopen(Request(base + path, data=payload, method=method, headers=headers), timeout=50) as response:
            return response.status, json.load(response)
    except HTTPError as error:
        try:
            return error.code, json.load(error)
        except Exception:
            return error.code, {"detail": "non-json HTTP error"}
    except URLError as error:
        raise RuntimeError("Test backend unreachable: " + str(error.reason)) from error


def require(status: int, obj: dict, expected: int, label: str) -> None:
    if status != expected:
        raise RuntimeError(f"{label}: HTTP {status}, expected {expected}, response={obj}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default=os.environ.get("CHARGEPIN_TEST_BASE_URL", "http://127.0.0.1:8000"))
    parser.add_argument("--repeat", type=int, default=3, choices=range(1, 11))
    parser.add_argument("--output", default="/tmp/fault-recovery-measured.json")
    args = parser.parse_args()
    base = args.base_url.rstrip("/")
    service_key = os.environ.get("CHARGEPIN_TEST_OPERATOR_KEY", "").strip()
    if not service_key:
        raise SystemExit("Missing CHARGEPIN_TEST_OPERATOR_KEY")
    status, login = call(base, "POST", "/api/v1/auth/login", body={"service_key": service_key})
    require(status, login, 200, "operator login")
    token = login.get("access_token")
    if not token:
        raise SystemExit("Operator login returned no token")
    status, flags = call(base, "GET", "/api/v1/test/faults", token)
    require(status, flags, 200, "fault-injection gate")
    if flags.get("test_only") is not True:
        raise SystemExit("Refusing target without test-only fault-injection API")
    print("Test-only injection confirmed. Running 9 fault/recovery cycles.", flush=True)
    records = []

    for scenario in SCENARIOS:
        for run in range(1, args.repeat + 1):
            row = {
                "scenario": scenario,
                "run": run,
                "passed_fault_handling": False,
                "passed_post_reset_functional_recovery": False,
                "autonomous_fault_repair_verified": False,
                "manual_recovery_action_by_operator": False,
                "recovery_method": "harness_reset_then_functional_probe",
            }
            fault_enabled = False
            started = monotonic()
            try:
                status, before = call(base, "GET", "/api/v1/ops/summary", token)
                require(status, before, 200, "pre-fault metrics")
                retries_before = int(before.get("metrics", {}).get("retry_count", 0))

                row["fault_injected_at_utc"] = utcnow()
                status, activated = call(base, "POST", f"/api/v1/test/faults/{scenario}", token)
                require(status, activated, 200, "fault activation")
                fault_enabled = True

                if scenario == "llm_invalid_schema":
                    code, response = call(base, "POST", "/api/v1/chat/plan", token, {"message": LLM_MESSAGE})
                    verdict = response.get("status")
                    accepted = code == 200 and verdict == "NEEDS_INPUT"
                else:
                    code, response = call(base, "POST", "/api/v1/search", token, SEARCH)
                    verdict = response.get("critic_decision")
                    accepted = code == 200 and response.get("status") == "degraded" and verdict == "SAFE_UNAVAILABLE"

                row["fault_response_at_utc"] = utcnow()
                row["fault_response_http"] = code
                row["fault_response_verdict"] = verdict
                row["fault_request_id"] = response.get("request_id")
                status, after = call(base, "GET", "/api/v1/ops/summary", token)
                require(status, after, 200, "post-fault metrics")
                retry_delta = int(after.get("metrics", {}).get("retry_count", 0)) - retries_before
                row["automatic_retry_count"] = retry_delta
                row["passed_fault_handling"] = bool(accepted and retry_delta == (2 if scenario == "timeout" else 0))

            except Exception as error:
                row["fault_error"] = str(error)
            finally:
                # NEVER rely on the previous fault remaining active during recovery.
                row["reset_requested_at_utc"] = utcnow()
                reset_started = monotonic()
                try:
                    code, reset = call(base, "POST", "/api/v1/test/faults/reset", token)
                    require(code, reset, 200, "test harness reset")
                    row["fault_reset_confirmed"] = reset.get("active") is None
                    fault_enabled = False
                except Exception as error:
                    row["fault_reset_confirmed"] = False
                    row["reset_error"] = str(error)

            if row.get("fault_reset_confirmed"):
                try:
                    if scenario == "llm_invalid_schema":
                        code, restored = call(base, "POST", "/api/v1/chat/plan", token, {"message": LLM_MESSAGE})
                        row["recovery_probe_status"] = restored.get("status")
                        row["passed_post_reset_functional_recovery"] = code == 200 and restored.get("status") in {
                            "AWAITING_CONFIRMATION", "AWAITING_LOCATION_CONFIRMATION"
                        }
                    else:
                        # Deterministic normal fixture proves the Executor/Critic path
                        # works again; it does not prove the upstream KECO API recovered.
                        code, flag = call(base, "POST", "/api/v1/test/faults/normal", token)
                        require(code, flag, 200, "normal fixture activation")
                        code, restored = call(base, "POST", "/api/v1/search", token, SEARCH)
                        row["recovery_probe_status"] = restored.get("status")
                        row["passed_post_reset_functional_recovery"] = (
                            code == 200 and restored.get("status") == "completed"
                            and len(restored.get("results", [])) > 0
                        )
                    row["recovery_probe_http"] = code
                    row["recovery_probed_at_utc"] = utcnow()
                    row["post_reset_probe_seconds"] = round(monotonic() - reset_started, 3)
                    row["test_cycle_seconds"] = round(monotonic() - started, 3)
                except Exception as error:
                    row["recovery_error"] = str(error)
                finally:
                    try:
                        code, cleared = call(base, "POST", "/api/v1/test/faults/reset", token)
                        require(code, cleared, 200, "final fixture reset")
                    except Exception as error:
                        row["final_reset_error"] = str(error)

            row["passed_test_cycle"] = bool(row["passed_fault_handling"] and row["passed_post_reset_functional_recovery"])
            records.append(row)
            print(
                f"{scenario} R{run}: handling={row['passed_fault_handling']} "
                f"post_reset_recovery={row['passed_post_reset_functional_recovery']} "
                f"probe_seconds={row.get('post_reset_probe_seconds', 'N/A')}",
                flush=True,
            )

    result = {
        "repeat": args.repeat,
        "scope": "isolated_backend_test_only",
        "important": "Recovery requires TEST HARNESS reset; autonomous fault repair is NOT established.",
        "records": records,
    }
    path = Path(args.output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    passed = sum(record["passed_test_cycle"] for record in records)
    print(f"Post-reset functional recovery: {passed}/{len(records)}; output={path}", flush=True)
    return 0 if passed == len(records) else 1


if __name__ == "__main__":
    raise SystemExit(main())
