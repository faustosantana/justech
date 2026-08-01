# LAUNCH_FAILED — SHADOW25_20260801T191120Z

**Classification:** launcher detach failure (not a product failure).

## Cause

Host `launch_autonomous_job.sh` used `nohup bash -c 'run_shadow_eligible.sh…'` under the Cursor/tool shell.
That host process was reaped when the tool session ended (process-group/cgroup teardown), before it reached `docker exec -d`.

Evidence:
- `run.log` / `launch.out` only contain the initial `suite=…` line
- no `exit_code`, empty `host.log`
- host PID 43428 dead immediately
- `/tmp/shadow_eligible_*` remained from prior aborted run `183121Z`

## Fix

Durable launcher: stage run-scoped `/tmp/prompt_cert/<run_id>/` and detach solely via `docker exec -d` + container wrapper (no host nohup worker).
