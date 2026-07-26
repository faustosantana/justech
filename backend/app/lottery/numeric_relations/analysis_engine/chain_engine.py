"""Chain engine — continuous analyst case chains."""

from __future__ import annotations

from typing import Any

from app.lottery.numeric_relations.analysis_engine.signal_tracker import get_signal_store


def get_chain(chain_id: str | None = None) -> dict[str, Any]:
    store = get_signal_store()
    cid = chain_id or store.active_chain_id
    if not cid or cid not in store.chains:
        return {"chain_id": cid, "case_ids": [], "timeline": []}
    return store.chains[cid].to_dict()


def allow_same_day_reanalysis(analysis_date: str) -> dict[str, Any]:
    return get_signal_store().start_new_analysis_same_day(analysis_date)
