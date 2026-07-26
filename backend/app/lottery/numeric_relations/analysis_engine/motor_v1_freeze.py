"""Official Motor v1.0 freeze registry — read-only product freeze.

Does not alter T1/T2 formulas, ranking, or tiebreak computation.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.lottery.numeric_relations.analysis_engine.prospective.freeze import (
    FROZEN_ENGINE_VERSION,
    FROZEN_TABLE_VERSION,
    FROZEN_TIEBREAK_RULE,
    OPERATIONAL_RANKING_PROFILE,
    OPERATIONAL_TIEBREAK_POLICY,
    git_commit_short,
)

# Product freeze label (Phase 5.2)
MOTOR_PRODUCT_VERSION = "1.0"
MOTOR_FREEZE_STATUS = "FROZEN"
MOTOR_FREEZE_DATE = "2026-07-26"
MOTOR_ACTIVE_PROFILE = OPERATIONAL_RANKING_PROFILE  # socio
MOTOR_TIEBREAK_RULE = FROZEN_TIEBREAK_RULE  # TIEBREAK_PROFILE_SOCIO_V1
MOTOR_TIEBREAK_POLICY = "EMPATE_MULTI_FUERTE"
MOTOR_ACTIVE_TIEBREAK = OPERATIONAL_TIEBREAK_POLICY
MOTOR_RELEASE_TAG = "lottery-ia-motor-v1.0"


def motor_v1_freeze_manifest() -> dict[str, Any]:
    """Immutable product freeze view for Dashboard (UI must not edit)."""
    commit = git_commit_short()
    return {
        "motor_version": MOTOR_PRODUCT_VERSION,
        "status": MOTOR_FREEZE_STATUS,
        "freeze_date": MOTOR_FREEZE_DATE,
        "frozen_at_display": MOTOR_FREEZE_DATE,
        "active_profile": MOTOR_ACTIVE_PROFILE,
        "tiebreak": MOTOR_TIEBREAK_RULE,
        "tiebreak_policy": MOTOR_TIEBREAK_POLICY,
        "active_tiebreak": MOTOR_ACTIVE_TIEBREAK,
        "tiebreak_rule_id": FROZEN_TIEBREAK_RULE,
        "engine_version": FROZEN_ENGINE_VERSION,
        "table1_version": FROZEN_TABLE_VERSION,
        "table2_version": FROZEN_TABLE_VERSION,
        "engine_commit": commit,
        "release_tag": MOTOR_RELEASE_TAG,
        "read_only": True,
        "ui_editable": False,
        "silent_changes_forbidden": True,
        "production_modified": False,
        "notes": (
            "Motor v1.0 congelado (Lottery IA). "
            "Cambios requieren nueva engine_version, tag y cohorte de métricas."
        ),
    }


def persist_freeze_artifact(root: Path | None = None) -> Path:
    base = root or Path(__file__).resolve().parents[5]
    out = base / "artifacts" / "motor_freeze" / "motor_v1_freeze.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        **motor_v1_freeze_manifest(),
        "written_at": datetime.now(timezone.utc).isoformat(),
    }
    out.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return out
