"""DEV-safe auth rejection telemetry (no JWT body logged)."""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any

logger = logging.getLogger("jaios.auth.cert")

_TRACE_PATH = Path("/tmp/jaios_auth_401_trace.jsonl")


def record_auth_reject(
    *,
    reason: str,
    path: str | None = None,
    correlation_id: str | None = None,
    token_present: bool = False,
    subject: str | None = None,
    user_lookup: str | None = None,
    extra: dict[str, Any] | None = None,
) -> None:
    row = {
        "ts": time.time(),
        "correlation_id": correlation_id,
        "path": path,
        "token_present": token_present,
        "token_decode_result": "ok" if reason in {"user_not_found", "user_inactive"} else "fail",
        "expiration_validation": "expired" if reason == "token_expired" else "n/a",
        "subject": subject,
        "user_lookup_result": user_lookup,
        "reason": reason,
    }
    if extra:
        row["extra"] = extra
    try:
        logger.warning("auth_reject %s", json.dumps(row, ensure_ascii=False))
    except Exception:  # noqa: BLE001
        pass
    try:
        with _TRACE_PATH.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    except Exception:  # noqa: BLE001
        pass
