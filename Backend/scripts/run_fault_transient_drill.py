"""Three distinct transient recovery probes for isolated AWS Backend.

FT-01: retry completes SAME request (one-shot provider timeout).
FT-02: exception is isolated, NEXT independent request succeeds (no auto re-run).
FT-04: schema rejection is isolated, NEXT independent LLM plan succeeds.
Fixture expires internally after first fault; test harness does NOT reset before probe.
FT-02/FT-04 recovery is SERVICE CONTINUITY, not same-request automatic retry.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
from time import monotonic
from urllib.error import HTTPError
from urllib.request import Request, urlopen

SEARCH={"center":{"lat":37.498,"lng":127.027},"radius_km":0.5,"connector_types":["FAST","SLOW"],"region_filters":[]}
CHAT={"message":"사당역 근처 두 키로 급속으로 찾아 줘"}

def ts(): return datetime.now(timezone.utc).isoformat()
def req(base,method,path,token="",body=None):
    data=json.dumps(body).encode() if body is not None else None
    h={"Accept":"application/json"}
    if token: h["Authorization"]="Bearer "+token
    if data is not None: h["Content-Type"]="application/json"
    try:
        with urlopen(Request(base+path,data=data,headers=h,method=method),timeout=50) as res:
            return res.status,json.load(res)
    except HTTPError as e:
        return e.code,json.load(e)
def ok(base,method,path,token,body=None):
    code,resp=req(base,method,path,token,body)
    if code!=200: raise RuntimeError(f"{path}: HTTP {code}, body={resp}")
    return resp
def search(base,token): return ok(base,"POST","/api/v1/search",token,SEARCH)
def chat(base,token): return ok(base,"POST","/api/v1/chat/plan",token,CHAT)

def run(base,token,scenario,n):
    row={"scenario":scenario,"run":n,"started_utc":ts(),"manual_operator_intervention":False,
         "fault_fixture":"one_shot_internal_expiry","request_recovery_type":None,"passed":False}
    t0=monotonic()
    before=ok(base,"GET","/api/v1/ops/summary",token)
    retry_before=int(before["metrics"]["retry_count"])
    ok(base,"POST","/api/v1/test/faults/"+scenario,token)
    try:
        if scenario=="timeout_once":
            restored=search(base,token)
            after=ok(base,"GET","/api/v1/ops/summary",token)
            delta=int(after["metrics"]["retry_count"])-retry_before
            row.update({"retries":delta,"first_request_status":restored.get("status"),"first_request_id":restored.get("request_id"),
                        "request_recovery_type":"same_request_automatic_retry",
                        "passed":delta==1 and restored.get("status")=="completed" and len(restored.get("results",[]))>0})
        elif scenario=="executor_exception_once":
            first=search(base,token)
            second=search(base,token)
            row.update({"first_request_status":first.get("status"),"second_request_status":second.get("status"),
                        "first_request_id":first.get("request_id"),"second_request_id":second.get("request_id"),
                        "request_recovery_type":"exception_isolation_then_new_request_service_continuity",
                        "passed":first.get("status")=="degraded" and second.get("status")=="completed" and bool(second.get("results"))})
        elif scenario=="llm_invalid_schema_once":
            first=chat(base,token)
            second=chat(base,token)
            row.update({"first_request_status":first.get("status"),"second_request_status":second.get("status"),
                        "first_request_id":first.get("request_id"),"second_request_id":second.get("request_id"),
                        "request_recovery_type":"schema_rejection_then_new_request_planner_continuity",
                        "passed":first.get("status")=="NEEDS_INPUT" and second.get("status") in {
                            "AWAITING_CONFIRMATION","AWAITING_LOCATION_CONFIRMATION"}})
        row["finished_utc"]=ts()
        row["cycle_seconds"]=round(monotonic()-t0,3)
        row["active_before_cleanup"]=ok(base,"GET","/api/v1/test/faults",token).get("active")
        return row
    finally:
        ok(base,"POST","/api/v1/test/faults/reset",token)

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--base-url",default="http://127.0.0.1:8000")
    p.add_argument("--repeat",type=int,default=3)
    p.add_argument("--output",default="/tmp/fault-transient-evidence.json")
    a=p.parse_args()
    if a.repeat not in range(1,11): raise SystemExit("repeat 1..10")
    key=os.getenv("CHARGEPIN_TEST_OPERATOR_KEY","").strip()
    if not key: raise SystemExit("Missing CHARGEPIN_TEST_OPERATOR_KEY")
    base=a.base_url.rstrip("/")
    code,auth=req(base,"POST","/api/v1/auth/login",body={"service_key":key})
    if code!=200 or not auth.get("access_token"): raise SystemExit("test operator login failed")
    token=auth["access_token"]
    if ok(base,"GET","/api/v1/test/faults",token).get("test_only") is not True:
        raise SystemExit("No test-only fault injection gate")
    records=[]
    try:
        for scenario in ("timeout_once","executor_exception_once","llm_invalid_schema_once"):
            for n in range(1,a.repeat+1):
                try:
                    row=run(base,token,scenario,n)
                except Exception as e:
                    row={"scenario":scenario,"run":n,"passed":False,"error":str(e)}
                records.append(row)
                print(f"{scenario} R{n}: pass={row['passed']} type={row.get('request_recovery_type')} "
                      f"seconds={row.get('cycle_seconds')} "
                      f"statuses={row.get('first_request_status')},{row.get('second_request_status')}",
                      flush=True)
    finally:
        try: ok(base,"POST","/api/v1/test/faults/reset",token)
        except Exception: pass
        out=Path(a.output)
        out.parent.mkdir(parents=True,exist_ok=True)
        out.write_text(json.dumps({
            "scope":"isolated_test_backend_only",
            "note":"FT-02/04 second independent request initiated by harness, NOT automatic retry of first request; do not mark same-request autohealing PASS.",
            "records":records},ensure_ascii=False,indent=2))
        print(f"Transient scenario verification {sum(r['passed'] for r in records)}/{len(records)}; evidence={out}",flush=True)
    return 0 if all(r["passed"] for r in records) else 1
if __name__=="__main__":
    raise SystemExit(main())
