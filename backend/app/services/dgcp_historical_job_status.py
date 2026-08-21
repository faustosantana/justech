"""Estados formales de jobs de indexación histórica DGCP.

SUCCESS / FAILED / TIMEOUT / COMPLETED_AFTER_TIMEOUT / SOURCE_UNAVAILABLE

Regla: un completion marker SUCCESS no se sobrescribe por un timeout de shell posterior.
"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from typing import Any

import httpx

from app.models.dgcp_historical_award import DGCPHistoricalIndexJob

JOB_SUCCESS = "SUCCESS"
JOB_FAILED = "FAILED"
JOB_TIMEOUT = "TIMEOUT"
JOB_COMPLETED_AFTER_TIMEOUT = "COMPLETED_AFTER_TIMEOUT"
JOB_SOURCE_UNAVAILABLE = "SOURCE_UNAVAILABLE"
JOB_RUNNING = "running"

# Legacy aliases still accepted when reading
_SUCCESS_ALIASES = {JOB_SUCCESS, "completed", "success", JOB_COMPLETED_AFTER_TIMEOUT}
_FAILED_ALIASES = {JOB_FAILED, "failed", "error"}

# Never downgrade these once persisted
_TERMINAL_SUCCESS = {JOB_SUCCESS, JOB_COMPLETED_AFTER_TIMEOUT, "completed"}


def is_job_success(status: str | None) -> bool:
    return (status or "").lower() in {s.lower() for s in _SUCCESS_ALIASES}


def classify_exception(exc: BaseException) -> str:
    if isinstance(exc, httpx.TimeoutException):
        return JOB_TIMEOUT
    if isinstance(exc, httpx.HTTPStatusError):
        code = exc.response.status_code if exc.response is not None else 0
        if code in (502, 503, 504):
            return JOB_SOURCE_UNAVAILABLE
        return JOB_FAILED
    msg = str(exc).lower()
    if "502" in msg or "503" in msg or "bad gateway" in msg or "service unavailable" in msg:
        return JOB_SOURCE_UNAVAILABLE
    if "timeout" in msg or "timed out" in msg:
        return JOB_TIMEOUT
    return JOB_FAILED


def mark_job_complete(
    job: DGCPHistoricalIndexJob,
    *,
    status: str,
    error_message: str | None = None,
    source_status: str | None = None,
    result_meta: dict[str, Any] | None = None,
) -> None:
    """Persiste completion. No degrada SUCCESS ya marcado."""
    if job.status in _TERMINAL_SUCCESS and status not in _TERMINAL_SUCCESS:
        # Shell/wrapper timeout after success → annotate, keep SUCCESS
        meta = dict(job.result_meta or {})
        meta["shell_post_timeout"] = True
        meta["ignored_status"] = status
        if error_message:
            meta["ignored_error"] = error_message
        job.result_meta = meta
        if status == JOB_TIMEOUT:
            # Explicit signal for ops without flipping SUCCESS
            job.source_status = job.source_status or "AVAILABLE"
        return

    started = job.started_at
    now = datetime.now(UTC)
    job.status = status
    job.completed_at = now
    if error_message is not None:
        job.error_message = error_message
    if source_status is not None:
        job.source_status = source_status
    job.rows_processed = int(job.items_indexed or 0)
    if started is not None:
        try:
            job.duration_ms = int((now - started).total_seconds() * 1000)
        except Exception:
            job.duration_ms = None
    payload = f"{job.pages_indexed}:{job.contracts_indexed}:{job.items_indexed}:{status}"
    job.result_hash = hashlib.sha1(payload.encode("utf-8")).hexdigest()[:16]
    meta = dict(job.result_meta or {})
    if result_meta:
        meta.update(result_meta)
    meta["completed_at"] = now.isoformat()
    meta["status"] = status
    job.result_meta = meta


def should_auto_retry(job: DGCPHistoricalIndexJob | None) -> bool:
    if job is None:
        return True
    if is_job_success(job.status):
        return False
    return job.status in {JOB_FAILED, JOB_TIMEOUT, JOB_SOURCE_UNAVAILABLE, "failed", "running"}
