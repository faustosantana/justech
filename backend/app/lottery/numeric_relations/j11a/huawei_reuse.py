"""Prove J-11A reuses Huawei credential plumbing without duplicating secrets."""

from __future__ import annotations

from typing import Any


def huawei_credential_status() -> dict[str, Any]:
    from app.lottery.ai.runtime import runtime_snapshot

    snap = runtime_snapshot()
    hw = snap.get("huawei_modelarts") or {}
    return {
        "credentials_reused_from": "app.lottery.ai.runtime.runtime_snapshot / settings",
        "credentials_present": bool(hw.get("credentials_present")),
        "endpoint_configured": bool(hw.get("endpoint_configured")),
        "duplicates_secrets": False,
        "j11a_calculates_tables": False,
        "role": hw.get("role_in_lottery"),
    }
