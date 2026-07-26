"""Prospective validation facade — Phase 3 API compatibility + Phase 4 persistence."""

from __future__ import annotations

from app.lottery.numeric_relations.analysis_engine.prospective.store import (
    ProspectivePrediction,
    ProspectiveStore,
    get_prospective_store,
    reset_prospective_store,
)
from app.lottery.numeric_relations.analysis_engine.prospective.hashing import (
    hash_payload as _hash_payload,
)

__all__ = [
    "ProspectivePrediction",
    "ProspectiveStore",
    "get_prospective_store",
    "reset_prospective_store",
    "_hash_payload",
]
