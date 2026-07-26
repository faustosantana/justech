"""J-11A conversational memory (session) — not a substitute for engine truth."""

from __future__ import annotations

from typing import Any

from app.lottery.numeric_relations.analysis_engine.schemas import new_id
from app.lottery.numeric_relations.j11a.schemas import SessionMemory


_SESSIONS: dict[str, SessionMemory] = {}


def get_or_create_session(conversation_id: str | None = None) -> SessionMemory:
    cid = conversation_id or new_id("conv")
    if cid not in _SESSIONS:
        _SESSIONS[cid] = SessionMemory(conversation_id=cid)
    return _SESSIONS[cid]


def update_from_analysis(memory: SessionMemory, result: dict[str, Any]) -> SessionMemory:
    memory.analysis_id = result.get("analysis_id")
    memory.observed_numbers = list(result.get("observed_numbers") or [])
    memory.analysis_date = result.get("analysis_date")
    memory.positions = list(result.get("positions") or [])
    memory.mode = result.get("mode")
    memory.derivation_depth = int(result.get("derivation_depth") or 2)
    memory.primary_signal = result.get("primary_signal")
    memory.alternatives = list(result.get("alternatives") or [])
    memory.secondary_signals = [
        s for s in (result.get("signals") or []) if s.get("classification") == "FUERTE_SECUNDARIO"
    ]
    memory.last_ranked = list(result.get("ranked_candidates") or [])
    memory.last_result = result
    if memory.primary_signal:
        memory.last_candidate = int(memory.primary_signal["number"])
    return memory


def reset_sessions() -> None:
    _SESSIONS.clear()
