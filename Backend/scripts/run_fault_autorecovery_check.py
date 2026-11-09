"""Prove/disprove autonomous recovery while a fault remains ACTIVE.

This does not count fixture reset as recovery. Operates ONLY against an isolated
test backend with explicit test-only injection enabled. Always clears fault at
end of each round for test isolation. The clearing is NOT an autoheal event.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
from time import monotonic, sleep
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

SEARCH_BODY = {
    "center": {"lat": 37.498, "lng": 127.027},
    "radius_km": 0.5,
    "connector_types": ["FAST", "SLOW"],
    "region_filters": [],
}
SCENARIOS = ("timeout", "executor_exception", "llm_invalid_schema")
CHAT_BODY = {"message": "사당역 근처 두 키로 급속으로 찾아 줘"}

def now():
    return datetime.now(timezone.utc).isoformat()

def api(base, method, path, token=None, body=None):
    data = json.dumps(body).encode() if body is not None else None
    headers = {"Accept": "application/json"}
    if data is not None:
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = "Bearer " + token
    req = Request(base + path, data=data, headers=headers, method=method)
    try:
        with urlopen(req, timeout=50) as res:
            return res.status, json.load(res)
    except HTTPError as exc:
        try:
            return exc.code, json.load(exc)
        except Exception:
            return exc.code, {"detail": "non-json error"}

def checked(base, method, path, token, body=None):
    code, obj = api(base, method, path, token, body)
    if code != 200:
        raise RuntimeError(f"{method} {path} returned HTTP {code}: {obj}")
    return obj

def probe(base, token, scenario):
    if scenario == "llm_invalid_schema":
        code, res = api(base, "POST", "/api/v1/chat/plan", token, CHAT_BODY)
        return {"http_status": code, "status": res.get("status"), "request_id": res.get("request_id"),
                "normal": code == 200 and res.get("status") in
                          {"AWAITING_CONFIRMATION", "AWAITING_LOCATION_CONFIRMATION"}}
    code, res = api(base, "POST", "/api/v1/search", token, SEARCH_BODY)
    return {"http_status": code, "status": res.get("status"),
            "critic_decision": res.get("critic_decision"), "request_id": res.get("request_id"),
            "normal": code == 200 and res.get("status") == "completed" and bool(res.get("results"))}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--repeat", type=int, default=3)
    parser.add_argument("--probes", type=int, default=3)
    parser.add_argument("--probe-interval", type=float, default=1)
    parser.add_argument("--output", default="/tmp/fault-autorecovery-evidence.json")
    a = parser.parse_args()
    if not 1 <= a.repeat <= 10 or not 1 <= a.probes <= 10:
        raise SystemExit("repeat/probes must be between 1 and 10")
    base = a.base_url.rstrip("/")
    key = os.getenv("CHARGEPIN_TEST_OPERATOR_KEY", "").strip()
    if not key:
        raise SystemExit("Missing CHARGEPIN_TEST_OPERATOR_KEY")
    code, auth = api(base, "POST", "/api/v1/auth/login", body={"service_key": key})
    if code != 200 or not auth.get("access_token"):
        raise SystemExit("Operator authentication failed")
    token = auth["access_token"]
    gate = checked(base, "GET", "/api/v1/test/faults", token)
    if gate.get("test_only") is not True:
        raise SystemExit("Not an isolated test-only fault endpoint")
    checked(base, "POST", "/api/v1/test/faults/reset", token)
    records = []
    try:
        for scenario in SCENARIOS:
            for run in range(1, a.repeat + 1):
                row = {"scenario": scenario, "run": run, "fault_started_utc": now(),
                       "autonomous_recovery": False, "manual_operator_recovery": False,
                       "probes_while_fault_active": [], "seconds_until_recovery": None}
                injected = False
                t0 = monotonic()
                try:
                    checked(base, "POST", f"/api/v1/test/faults/{scenario}", token)
                    injected = True
                    for p in range(a.probes):
                        result = probe(base, token, scenario)
                        result["checked_at_utc"] = now()
                        result["elapsed_seconds"] = round(monotonic()-t0,3)
                        row["probes_while_fault_active"].append(result)
                        if result["normal"]:
                            row["autonomous_recovery"] = True
                            row["recovered_at_utc"] = result["checked_at_utc"]
                            row["seconds_until_recovery"] = result["elapsed_seconds"]
                            break
                        if p < a.probes-1:
                            sleep(a.probe_interval)
                    row["final_fault_active"] = checked(base, "GET", "/api/v1/test/faults", token).get("active")
                except Exception as exc:
                    row["error"] = str(exc)
                finally:
                    if injected:
                        try:
                            checked(base, "POST", "/api/v1/test/faults/reset", token)
                            row["harness_cleanup_only"] = True
                        except Exception as exc:
                            row["harness_cleanup_error"] = str(exc)
                    records.append(row)
                    print(f"{scenario} R{run}: autonomous_recovery={row['autonomous_recovery']} "
                          f"elapsed={row['seconds_until_recovery']} active_before_cleanup={row.get('final_fault_active')}",
                          flush=True)
    finally:
        try:
            checked(base, "POST", "/api/v1/test/faults/reset", token)
        except Exception:
            pass
        path = Path(a.output)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"scope":"test-only isolated backend",
            "rule":"Auto recovery counted ONLY if normal result while injected fault remains active; harness reset excluded.",
            "records":records}, ensure_ascii=False, indent=2))
        print(f"Verified autonomous recovery: {sum(r['autonomous_recovery'] for r in records)}/{len(records)}; evidence={path}", flush=True)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
