"""Secret redaction for forensic artifacts."""

from __future__ import annotations

import re
from typing import Any

_SECRET_KEY_RE = re.compile(
    r"(authorization|api[_-]?key|access[_-]?token|refresh[_-]?token|password|"
    r"secret|cookie|set-cookie|x-api-key|bearer|connection.?string|"
    r"database_url|redis_url|jwt)",
    re.I,
)
_BEARER_RE = re.compile(r"(Bearer\s+)[A-Za-z0-9\-._~+/]+=*", re.I)
_LONG_TOKEN_RE = re.compile(r"\b(?:sk-|hk-|eyJ)[A-Za-z0-9\-._]{12,}\b")


def redact_string(value: str) -> str:
    if not value:
        return value
    out = _BEARER_RE.sub(r"\1[REDACTED]", value)
    out = _LONG_TOKEN_RE.sub("[REDACTED]", out)
    return out


def redact_obj(value: Any, *, depth: int = 0) -> Any:
    if depth > 12:
        return "[TRUNCATED_DEPTH]"
    if value is None or isinstance(value, (bool, int, float)):
        return value
    if isinstance(value, str):
        return redact_string(value)
    if isinstance(value, bytes):
        return f"[BYTES:{len(value)}]"
    if isinstance(value, dict):
        out: dict[str, Any] = {}
        for k, v in value.items():
            key = str(k)
            if _SECRET_KEY_RE.search(key):
                out[key] = "[REDACTED]"
            else:
                out[key] = redact_obj(v, depth=depth + 1)
        return out
    if isinstance(value, (list, tuple)):
        return [redact_obj(v, depth=depth + 1) for v in value[:500]]
    return redact_string(str(value))[:4000]
