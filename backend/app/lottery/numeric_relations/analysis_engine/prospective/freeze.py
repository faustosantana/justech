"""Engine freeze policy helpers for the prospective pilot."""

from __future__ import annotations

import subprocess
from typing import Any

from app.lottery.numeric_relations.analysis_engine.schemas import ENGINE_VERSION, TABLE_VERSION
from app.lottery.numeric_relations.analysis_engine.tiebreak_engine import (
    SELECTED_RULE_ID,
    TIEBREAK_ENGINE_VERSION,
)

FROZEN_ENGINE_VERSION = ENGINE_VERSION
FROZEN_TABLE_VERSION = TABLE_VERSION
FROZEN_TIEBREAK_VERSION = TIEBREAK_ENGINE_VERSION
FROZEN_TIEBREAK_RULE = SELECTED_RULE_ID
OPERATIONAL_RANKING_PROFILE = "socio"
OPERATIONAL_TIEBREAK_POLICY = "TIEBREAK_PROFILE_SOCIO_V1+EMPATE_MULTI_FUERTE"


def git_commit_short() -> str | None:
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()
        return out or None
    except Exception:
        return None


def freeze_manifest() -> dict[str, Any]:
    return {
        "engine_version": FROZEN_ENGINE_VERSION,
        "table1_version": FROZEN_TABLE_VERSION,
        "table2_version": FROZEN_TABLE_VERSION,
        "tiebreak_engine_version": FROZEN_TIEBREAK_VERSION,
        "tiebreak_rule": FROZEN_TIEBREAK_RULE,
        "ranking_profile": OPERATIONAL_RANKING_PROFILE,
        "tiebreak_policy": OPERATIONAL_TIEBREAK_POLICY,
        "engine_commit": git_commit_short(),
        "silent_changes_forbidden": True,
        "production_modified": False,
    }


def assert_operational_freeze(record: dict[str, Any]) -> None:
    if record.get("engine_version") != FROZEN_ENGINE_VERSION:
        raise ValueError("ENGINE_FREEZE_VIOLATION: engine_version mismatch")
    if record.get("table1_version") != FROZEN_TABLE_VERSION:
        raise ValueError("ENGINE_FREEZE_VIOLATION: table1_version mismatch")
    if record.get("ranking_profile") not in {None, OPERATIONAL_RANKING_PROFILE, "socio"}:
        raise ValueError("ENGINE_FREEZE_VIOLATION: ranking_profile mismatch")
