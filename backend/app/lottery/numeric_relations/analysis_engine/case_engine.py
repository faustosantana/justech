"""Case engine — wraps signal store case lifecycle."""

from __future__ import annotations

from typing import Any

from app.lottery.numeric_relations.analysis_engine.signal_tracker import get_signal_store


def list_active_cases() -> list[dict[str, Any]]:
    store = get_signal_store()
    return [c.to_dict() for c in store.cases.values() if c.status == "ACTIVO"]


def list_closed_cases() -> list[dict[str, Any]]:
    store = get_signal_store()
    return [c.to_dict() for c in store.cases.values() if c.status == "CERRADO"]


def get_case(case_id: str) -> dict[str, Any] | None:
    store = get_signal_store()
    c = store.cases.get(case_id)
    return c.to_dict() if c else None
