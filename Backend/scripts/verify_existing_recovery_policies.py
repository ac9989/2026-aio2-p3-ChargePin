"""Run three distinct recovery-policy tests on the UNMODIFIED ChargePin image.

No running service, database, frontend, production API, or real provider is touched.
Mocks inject exactly one transient error in the same Python process. All test
results are separate from original nine permanent-fault drills.
"""
from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from unittest.mock import patch
import json
import os
import sys

sys.path.insert(0, os.getcwd())
from app.agents import SearchOrchestrator
from app.models import PlaceCandidate, Point, SearchInput
from app.providers import ProviderError

BODY = SearchInput(center=Point(lat=37.498,lng=127.027),radius_km=0.5,connector_types=["FAST","SLOW"],region_filters=[])
PLACE = PlaceCandidate(candidate_id="isolated-fixture",name="사당역",category="지하철역",address="서울특별시 동작구 사당동",location=Point(lat=37.498,lng=127.027),district_code="11680")
OUTPUT = Path("/evidence/chargepin-existing-recovery-9runs.json")

def stamp(): return datetime.now(timezone.utc).isoformat()
def case_timeout(run):
    o = SearchOrchestrator()
    o.test_scenarios.activate("normal")
    normal = o.test_scenarios.execute_fixture
    state = {"n":0}
    def one_shot(request):
        state["n"] += 1
        if state["n"] == 1:
            raise ProviderError("KECO","temporary test timeout",retryable=True)
        return normal(request)
    t0=perf_counter()
    with patch.object(o.test_scenarios,"execute_fixture",side_effect=one_shot), patch("app.agents.sleep"):
        res=o.direct_search(BODY,"SENIOR_ADMIN")
    elapsed=round(perf_counter()-t0,6)
    handoff=o.memory.handoffs[res.request_id]
    retries=[r for r in handoff.get("retry_history",[]) if r.get("kind")=="automatic"]
    passed=res.status=="completed" and res.critic_decision=="PASS" and len(retries)==1 and state["n"]==2
    return dict(scenario="FT-01",run=run,criterion="same_request_automatic_retry",automatic_recovery=passed,
                safe_handling=passed,manual_operator_intervention=False,attempt_count=state["n"],
                automatic_retries=len(retries),response_status=res.status,elapsed_seconds=elapsed,passed=passed)

def case_executor(run):
    o=SearchOrchestrator()
    o.test_scenarios.activate("normal")
    normal=o.test_scenarios.execute_fixture
    state={"n":0}
    def one_shot(request):
        state["n"]+=1
        if state["n"]==1:
            raise RuntimeError("isolated executor test exception")
        return normal(request)
    with patch.object(o.test_scenarios,"execute_fixture",side_effect=one_shot):
        t0=perf_counter()
        first=o.direct_search(BODY,"SENIOR_ADMIN")
        t1=perf_counter()
        second=o.direct_search(BODY,"SENIOR_ADMIN")
        t2=perf_counter()
    passed=first.status=="degraded" and first.critic_decision=="SAFE_UNAVAILABLE" and second.status=="completed" and second.critic_decision=="PASS"
    return dict(scenario="FT-02",run=run,criterion="exception_isolation_then_next_independent_request",
                automatic_recovery=False,service_continuity=passed,manual_operator_intervention=False,
                first_status=first.status,second_status=second.status,first_request_seconds=round(t1-t0,6),
                next_request_seconds=round(t2-t1,6),passed=passed,
                note="No automatic retry of the failed request; next request is initiated by the test harness.")

def case_schema(run):
    o=SearchOrchestrator()
    o.planner._api_key=""  # force local rule path after the injected schema failure
    o.test_scenarios.activate("llm_invalid_schema")
    t0=perf_counter()
    first=o.plan_chat("사당역 1km 급속","SENIOR_ADMIN",session_ref=f"fail-{run}")
    t1=perf_counter()
    o.test_scenarios.clear() # harness ends the test-only fault; NOT autonomous remediation
    with patch.object(o.executor,"place_candidates",return_value=[PLACE]):
        second=o.plan_chat("사당역 1km 급속","SENIOR_ADMIN",session_ref=f"healthy-{run}")
    t2=perf_counter()
    passed=first.status=="NEEDS_INPUT" and second.status=="AWAITING_CONFIRMATION"
    return dict(scenario="FT-04",run=run,criterion="invalid_schema_blocked_then_next_rule_based_plan",
                automatic_recovery=False,service_continuity=passed,manual_operator_intervention=False,
                first_status=first.status,second_status=second.status,
                first_request_seconds=round(t1-t0,6),next_request_seconds=round(t2-t1,6),
                passed=passed,note="Harness clears fault and forces rule planner. NOT actual LLM re-generation/recovery.")

def main():
    records=[]
    try:
        for name,fn in (("FT-01",case_timeout),("FT-02",case_executor),("FT-04",case_schema)):
            for run in range(1,4):
                try:
                    row=fn(run)
                except Exception as error:
                    row=dict(scenario=name,run=run,passed=False,error=repr(error))
                records.append(row)
                print(f"{name}-R{run}: policy_pass={row['passed']} auto_recovery={row.get('automatic_recovery')} elapsed={row.get('elapsed_seconds', row.get('next_request_seconds'))}",flush=True)
    finally:
        OUTPUT.parent.mkdir(parents=True,exist_ok=True)
        OUTPUT.write_text(json.dumps(dict(checked_at_utc=stamp(),scope="isolated new process using original production backend image",records=records),ensure_ascii=False,indent=2))
        print(f"Policy result: {sum(r['passed'] for r in records)}/{len(records)}; evidence={OUTPUT}",flush=True)
    return 0 if all(r["passed"] for r in records) else 1
if __name__=="__main__":
    raise SystemExit(main())
