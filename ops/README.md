# ChargePin local Docker Auto Healing watcher (Step 1)

Scope: local development, Windows PowerShell. **Only the Streamlit frontend**
`chargepin_repo-frontend-1` is eligible for automated restarts. PostgreSQL and
Redis are deliberately excluded to protect data and support investigation.

## How it works

- Docker healthcheck decides health; this tool polls `docker inspect` every 15s.
- It ignores `starting`, `healthy`, and manually stopped containers.
- Two consecutive `running/unhealthy` observations trigger one restart **only
  when `--apply` is supplied**. Without it, monitoring is dry-run.
- A 120s cooldown and 3 attempts per rolling 10 minutes limit restart loops.
  Restart attempts are also loaded from the JSONL log after a watcher restart.
- It records transitions, attempts, recovery elapsed seconds, failed commands,
  and recovery timeouts in `ops/logs/autoheal.jsonl` (ignored by Git).
- Run it in a separate PowerShell window while the local Docker Desktop is on.
  Exiting the window or pressing Ctrl+C stops the watcher. **It is not yet a
  24/7 Windows service or AWS deployment agent.**
- Logs contain UTC timestamps and may be used as a basis for a *real* fault
  injection report. They do not represent measured production incidents.

## Commands from ChargePin_repo

```powershell
python .\ops\autoheal.py --once
python -m unittest discover -s .\tests\ops -v
python .\ops\autoheal.py --watch
# Press Ctrl+C after checking dry-run. Enable real restarts only when ready:
python .\ops\autoheal.py --watch --apply
```

The `--watch --apply` command should remain in its own terminal. No need to
commit any logs or credentials. If running with a different Compose project
name, use `--container <name>`.

## Next steps

Test a controlled frontend-only `unhealthy` injection, observe recovery time,
verify manual stop does not auto-restart, and later configure OS-level
supervision on AWS with alerting and centralized audit logs.
