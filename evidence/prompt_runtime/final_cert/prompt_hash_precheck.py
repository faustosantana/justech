#!/usr/bin/env python3
"""Resolve and validate EXPECTED_HASH for shadow eligible harness.

No silent fallback to a legacy hardcoded hash.
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable


class PromptHashPrecheckError(RuntimeError):
    """Raised when prompt hash precheck fails before any case runs."""

    code = "PROMPT_HASH_PRECHECK_FAILED"


@dataclass(frozen=True)
class ActivePrompt:
    version_id: str
    semantic_version: str
    compiled_hash: str


@dataclass(frozen=True)
class ResolvedHash:
    expected_hash: str
    hash_source: str  # runtime_status|env|freeze_manifest
    active_version_id: str
    active_semantic_version: str
    active_hash: str
    freeze_hash: str | None
    freeze_version_id: str | None
    freeze_semantic_version: str | None


def load_freeze_manifest(path: str | Path | None) -> dict[str, Any] | None:
    if not path:
        return None
    p = Path(path)
    if not p.exists():
        return None
    data = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise PromptHashPrecheckError("PROMPT_HASH_PRECHECK_FAILED: freeze manifest is not an object")
    return data


def parse_active_from_status(status: dict[str, Any]) -> ActivePrompt:
    active = status.get("active")
    if not isinstance(active, dict) or not active:
        raise PromptHashPrecheckError(
            "PROMPT_HASH_PRECHECK_FAILED: runtime status has no active reasoning-studio prompt"
        )
    version_id = str(active.get("id") or "").strip()
    semantic = str(active.get("version") or "").strip()
    compiled = str(active.get("checksum") or active.get("compiled_prompt_hash") or "").strip()
    if not version_id or not semantic or not compiled:
        raise PromptHashPrecheckError(
            "PROMPT_HASH_PRECHECK_FAILED: active prompt missing id/version/checksum"
        )
    return ActivePrompt(version_id=version_id, semantic_version=semantic, compiled_hash=compiled)


def fetch_runtime_status(
    base_url: str,
    *,
    headers: dict[str, str] | None = None,
    opener: Callable[..., Any] | None = None,
    timeout: float = 15.0,
) -> dict[str, Any]:
    url = base_url.rstrip("/") + "/lottery/admin/ai/prompt-runtime/status"
    req = urllib.request.Request(url, headers=headers or {}, method="GET")
    open_fn = opener or urllib.request.urlopen
    try:
        with open_fn(req, timeout=timeout) as resp:
            raw = resp.read()
            if isinstance(raw, bytes):
                raw = raw.decode("utf-8")
            data = json.loads(raw)
    except Exception as exc:  # noqa: BLE001
        raise PromptHashPrecheckError(
            f"PROMPT_HASH_PRECHECK_FAILED: status API inaccessible ({type(exc).__name__}: {exc})"
        ) from exc
    if not isinstance(data, dict):
        raise PromptHashPrecheckError("PROMPT_HASH_PRECHECK_FAILED: status API returned non-object")
    return data


def resolve_expected_hash(
    *,
    status: dict[str, Any] | None,
    env_expected_hash: str | None,
    freeze: dict[str, Any] | None,
    status_fetcher: Callable[[], dict[str, Any]] | None = None,
) -> ResolvedHash:
    """Resolve EXPECTED_HASH.

    Priority for hash_source when env empty:
      1) runtime status active hash
      2) explicit env (if provided, it must match runtime)
      3) freeze manifest (must match runtime)

    Env/freeze never override a conflicting runtime active hash — mismatch aborts.
    Empty env → resolve from status API (fetcher or provided status).
    """
    if status is None:
        if status_fetcher is None:
            raise PromptHashPrecheckError(
                "PROMPT_HASH_PRECHECK_FAILED: status API inaccessible (no status/fetcher)"
            )
        status = status_fetcher()

    active = parse_active_from_status(status)
    env_hash = (env_expected_hash or "").strip() or None
    freeze_hash = None
    freeze_vid = None
    freeze_sem = None
    if freeze:
        freeze_hash = str(
            freeze.get("compiled_prompt_hash")
            or freeze.get("expected_hash")
            or freeze.get("hash")
            or ""
        ).strip() or None
        freeze_vid = str(freeze.get("version_id") or freeze.get("prompt_version_id") or "").strip() or None
        freeze_sem = str(
            freeze.get("semantic_version") or freeze.get("version") or freeze.get("frozen_prompt") or ""
        ).strip() or None

    # Resolution order for the expected value:
    # 1) runtime active hash (always authoritative)
    # 2) explicit env must match runtime when provided
    # 3) freeze must match runtime when provided
    # hash_source reports which non-runtime input was supplied; else runtime_status.
    expected = active.compiled_hash
    if env_hash:
        hash_source = "env"
    elif freeze_hash:
        hash_source = "freeze_manifest"
    else:
        hash_source = "runtime_status"

    # All present identifiers must agree with runtime active.
    mismatches: list[str] = []
    if env_hash and env_hash != active.compiled_hash:
        mismatches.append(
            f"EXPECTED_HASH={env_hash} != active_hash={active.compiled_hash}"
        )
    if freeze_hash and freeze_hash != active.compiled_hash:
        mismatches.append(f"freeze_hash={freeze_hash} != active_hash={active.compiled_hash}")
    if freeze_vid and freeze_vid != active.version_id:
        mismatches.append(f"freeze_version_id={freeze_vid} != active_version_id={active.version_id}")
    if freeze_sem and freeze_sem != active.semantic_version:
        mismatches.append(
            f"freeze_semantic_version={freeze_sem} != active_semantic_version={active.semantic_version}"
        )
    if env_hash and freeze_hash and env_hash != freeze_hash:
        mismatches.append(f"env EXPECTED_HASH={env_hash} != freeze_hash={freeze_hash}")

    if mismatches:
        raise PromptHashPrecheckError(
            "PROMPT_HASH_PRECHECK_FAILED: " + "; ".join(mismatches)
        )

    return ResolvedHash(
        expected_hash=active.compiled_hash,
        hash_source=hash_source if hash_source == "runtime_status" else (
            "env" if env_hash else "freeze_manifest"
        ),
        # Prefer runtime_status as source when env/freeze only confirmed runtime.
        # If env was provided and matched, report env; elif freeze matched, freeze; else runtime.
        active_version_id=active.version_id,
        active_semantic_version=active.semantic_version,
        active_hash=active.compiled_hash,
        freeze_hash=freeze_hash,
        freeze_version_id=freeze_vid,
        freeze_semantic_version=freeze_sem,
    )


def resolve_expected_hash_fixed_source(resolved: ResolvedHash) -> ResolvedHash:
    """Normalize hash_source reporting: env > freeze > runtime when that input drove selection."""
    return resolved


def classify_hash_mismatch(observed: str | None, expected: str | None) -> str | None:
    """Return result_class for hash mismatch, or None if match/unknown."""
    if not expected:
        return "harness_configuration_error"
    if not observed:
        return "harness_configuration_error"
    if observed != expected:
        return "harness_configuration_error"
    return None


def annotate_hash_fields(
    row: dict[str, Any],
    *,
    observed: str | None,
    expected: str | None,
    hash_source: str | None,
) -> dict[str, Any]:
    match = bool(observed and expected and observed == expected)
    row["observed_prompt_hash"] = observed
    row["expected_prompt_hash"] = expected
    row["hash_match"] = match
    row["hash_source"] = hash_source
    row["hash_ok"] = match if (observed and expected) else False
    row["prompt_hash"] = observed
    return row


def precheck_or_exit(
    *,
    base_url: str,
    auth_headers: dict[str, str],
    env_expected_hash: str | None,
    freeze_path: str | Path | None,
) -> ResolvedHash:
    freeze = load_freeze_manifest(freeze_path)
    try:
        status = fetch_runtime_status(base_url, headers=auth_headers)
        resolved = resolve_expected_hash(
            status=status,
            env_expected_hash=env_expected_hash,
            freeze=freeze,
        )
    except PromptHashPrecheckError:
        raise
    # Force reported source: empty env → runtime_status even if freeze also present and matched.
    if not (env_expected_hash or "").strip():
        if freeze and (
            str(freeze.get("compiled_prompt_hash") or freeze.get("expected_hash") or "").strip()
        ):
            # freeze participated in validation; source remains runtime when env empty per priority #1
            resolved = ResolvedHash(
                expected_hash=resolved.expected_hash,
                hash_source="runtime_status",
                active_version_id=resolved.active_version_id,
                active_semantic_version=resolved.active_semantic_version,
                active_hash=resolved.active_hash,
                freeze_hash=resolved.freeze_hash,
                freeze_version_id=resolved.freeze_version_id,
                freeze_semantic_version=resolved.freeze_semantic_version,
            )
        else:
            resolved = ResolvedHash(
                expected_hash=resolved.expected_hash,
                hash_source="runtime_status",
                active_version_id=resolved.active_version_id,
                active_semantic_version=resolved.active_semantic_version,
                active_hash=resolved.active_hash,
                freeze_hash=resolved.freeze_hash,
                freeze_version_id=resolved.freeze_version_id,
                freeze_semantic_version=resolved.freeze_semantic_version,
            )
    elif (env_expected_hash or "").strip():
        resolved = ResolvedHash(
            expected_hash=resolved.expected_hash,
            hash_source="env",
            active_version_id=resolved.active_version_id,
            active_semantic_version=resolved.active_semantic_version,
            active_hash=resolved.active_hash,
            freeze_hash=resolved.freeze_hash,
            freeze_version_id=resolved.freeze_version_id,
            freeze_semantic_version=resolved.freeze_semantic_version,
        )
    return resolved


def write_run_freeze(path: Path, resolved: ResolvedHash) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "version_id": resolved.active_version_id,
                "semantic_version": resolved.active_semantic_version,
                "compiled_prompt_hash": resolved.active_hash,
                "expected_hash": resolved.expected_hash,
                "hash_source": resolved.hash_source,
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )


def main_cli() -> int:
    """CLI used by launchers. Prints JSON ResolvedHash or errors with code."""
    base = os.environ.get("FORENSIC_BASE_URL", "http://127.0.0.1:8000/api/v1")
    env_hash = os.environ.get("EXPECTED_HASH")
    freeze_path = os.environ.get("PROMPT_FREEZE_PATH")
    headers: dict[str, str] = {}
    tok = os.environ.get("PRECHECK_BEARER_TOKEN")
    tid = os.environ.get("PRECHECK_TENANT_ID")
    auth_path = Path(os.environ.get("PRECHECK_AUTH_JSON", "/tmp/routing3_auth.json"))
    if not tok and auth_path.exists():
        try:
            from uuid import UUID

            from app.core.security import create_access_token

            auth = json.loads(auth_path.read_text(encoding="utf-8"))
            tok = create_access_token(
                subject=auth["uid"],
                tenant_id=UUID(auth["tid"]),
                role=auth.get("role") or "owner",
            )
            tid = tid or auth["tid"]
        except Exception as exc:  # noqa: BLE001
            print(
                f"PROMPT_HASH_PRECHECK_FAILED: cannot build auth token ({type(exc).__name__}: {exc})",
                flush=True,
            )
            return 2
    if tok:
        headers["Authorization"] = f"Bearer {tok}"
    if tid:
        headers["X-Tenant-Id"] = tid
    try:
        resolved = precheck_or_exit(
            base_url=base,
            auth_headers=headers,
            env_expected_hash=env_hash,
            freeze_path=freeze_path,
        )
    except PromptHashPrecheckError as exc:
        print(str(exc), flush=True)
        return 2
    print(json.dumps(asdict(resolved), ensure_ascii=False), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main_cli())
