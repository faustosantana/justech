"""Run-scoped paths for autonomous certification jobs.

Never reuse global /tmp/shadow_eligible_* across runs.
"""
from __future__ import annotations

import re
from pathlib import Path

_CTR_ROOT = Path("/tmp/prompt_cert")
_RUN_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{2,120}$")


def validate_run_id(run_id: str) -> str:
    rid = (run_id or "").strip()
    if not _RUN_ID_RE.match(rid):
        raise ValueError(f"invalid run_id: {run_id!r}")
    if ".." in rid or "/" in rid or "\\" in rid:
        raise ValueError(f"invalid run_id path segment: {run_id!r}")
    return rid


def container_run_dir(run_id: str) -> Path:
    return _CTR_ROOT / validate_run_id(run_id)


def host_run_dir(cert_root: str | Path, run_id: str) -> Path:
    return Path(cert_root) / validate_run_id(run_id)


def run_files(run_dir: Path) -> dict[str, Path]:
    d = Path(run_dir)
    return {
        "suite": d / "suite.json",
        "run_log": d / "run.log",
        "checkpoint": d / "CHECKPOINT.json",
        "heartbeat": d / "heartbeat.json",
        "worker_pid": d / "worker.pid",
        "wrapper_pid": d / "wrapper.pid",
        "exit_code": d / "exit_code",
        "summary": d / "SUMMARY.json",
        "results": d / "RESULTS.json",
        "started_at": d / "started_at",
        "status": d / "status.txt",
        "precheck": d / "PROMPT_HASH_PRECHECK.json",
        "precheck_failed": d / "PRECHECK_FAILED",
        "launch_failed": d / "LAUNCH_FAILED",
        "freeze": d / "PROMPT_FREEZE.json",
        "auth": d / "routing3_auth.json",
    }


def assert_not_legacy_global(path: str | Path) -> None:
    p = str(path)
    banned = (
        "/tmp/shadow_eligible_out",
        "/tmp/shadow_eligible_inner.log",
        "/tmp/SHADOW_ELIGIBLE.json",
    )
    for b in banned:
        if p == b or p.startswith(b + "/"):
            raise ValueError(f"legacy global path forbidden for run-scoped jobs: {p}")
