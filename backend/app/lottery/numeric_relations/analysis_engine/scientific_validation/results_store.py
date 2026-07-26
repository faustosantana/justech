"""Phase 2 results store — in-memory + disk artifacts for J-11A investigator."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


_RESULTS: dict[str, Any] = {}


def set_phase2_results(payload: dict[str, Any]) -> None:
    global _RESULTS
    _RESULTS = payload


def get_phase2_results() -> dict[str, Any]:
    if _RESULTS:
        return _RESULTS
    # try load from default artifact
    path = (
        Path(__file__).resolve().parents[6]
        / "artifacts"
        / "scientific_validation"
        / "phase2_summary.json"
    )
    if path.exists():
        data = json.loads(path.read_text(encoding="utf-8"))
        set_phase2_results(data)
        return data
    return {}


def save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
