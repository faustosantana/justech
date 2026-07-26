"""In-memory signal / case / chain trackers for continuous analyst workflow."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timedelta
from typing import Any

from app.lottery.numeric_relations.catalog import TableCatalog, build_catalog
from app.lottery.numeric_relations.analysis_engine.schemas import (
    ExperimentalSignal,
    SignalStatus,
    new_id,
)


@dataclass
class CaseRecord:
    case_id: str
    analysis_id: str
    signal_id: str
    observed_numbers: list[int]
    fuerte: int
    opened_at: str
    status: str = SignalStatus.ACTIVO.value
    closed_at: str | None = None
    fulfillment: dict[str, Any] | None = None
    chain_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ChainRecord:
    chain_id: str
    case_ids: list[str] = field(default_factory=list)
    timeline: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class SignalStore:
    """Process-local store (DEV). Domain source of truth for J-11A tools."""

    def __init__(self) -> None:
        self.signals: dict[str, ExperimentalSignal] = {}
        self.cases: dict[str, CaseRecord] = {}
        self.chains: dict[str, ChainRecord] = {}
        self.analyses: dict[str, dict[str, Any]] = {}
        self.active_chain_id: str | None = None

    def save_analysis(self, analysis_id: str, payload: dict[str, Any]) -> None:
        self.analyses[analysis_id] = payload

    def register_signals(
        self,
        signals: list[ExperimentalSignal],
        *,
        open_cases: bool = True,
        chain_id: str | None = None,
    ) -> list[CaseRecord]:
        cases: list[CaseRecord] = []
        cid = chain_id or self.active_chain_id or new_id("chain")
        if cid not in self.chains:
            self.chains[cid] = ChainRecord(chain_id=cid)
        self.active_chain_id = cid

        for sig in signals:
            self.signals[sig.signal_id] = sig
            if not open_cases:
                continue
            if sig.classification not in {
                "FUERTE_PRINCIPAL",
                "FUERTE_SECUNDARIO",
                "CANDIDATO_CONFIRMADO",
                "VECINO_T2_DIRECTO",
            }:
                continue
            case = CaseRecord(
                case_id=new_id("case"),
                analysis_id=sig.analysis_id,
                signal_id=sig.signal_id,
                observed_numbers=list(sig.observed_numbers),
                fuerte=sig.number,
                opened_at=sig.analysis_date or datetime.utcnow().date().isoformat(),
                status=SignalStatus.ACTIVO.value,
                chain_id=cid,
            )
            sig.case_id = case.case_id
            self.cases[case.case_id] = case
            self.chains[cid].case_ids.append(case.case_id)
            self.chains[cid].timeline.append(
                {
                    "event": "NEW_ANALYSIS_STARTED",
                    "case_id": case.case_id,
                    "signal": sig.number,
                    "date": case.opened_at,
                    "classification": sig.classification,
                }
            )
            cases.append(case)
        return cases

    def active_signals(self) -> list[ExperimentalSignal]:
        return [s for s in self.signals.values() if s.status == SignalStatus.ACTIVO.value]

    def history_signals(self) -> list[ExperimentalSignal]:
        return list(self.signals.values())

    def get_signal(self, signal_id: str) -> ExperimentalSignal | None:
        return self.signals.get(signal_id)

    def evaluate_signal(
        self,
        signal_id: str,
        *,
        draw_date: date,
        drawn_numbers: list[int],
        lottery: str | None = None,
        position: str | None = None,
        catalog: TableCatalog | None = None,
    ) -> ExperimentalSignal:
        sig = self.signals[signal_id]
        if sig.status != SignalStatus.ACTIVO.value:
            return sig
        if not sig.analysis_date:
            return sig
        opened = date.fromisoformat(sig.analysis_date[:10])
        delta = (draw_date - opened).days
        if delta < 1:
            # same-day: do not auto-fulfill; allow new analysis same day
            return sig
        if delta > 7:
            sig.status = SignalStatus.EXPIRADO.value
            sig.closed_at = draw_date.isoformat()
            self._close_case_for_signal(sig, fulfillment={"reason": "expired", "day": delta})
            return sig

        cat = catalog or build_catalog()
        nums = [int(x) for x in drawn_numbers]
        appearance = {
            "date": draw_date.isoformat(),
            "lottery": lottery,
            "position": position,
            "numbers": nums,
            "relative_day": delta,
        }

        if sig.number in nums:
            sig.status = SignalStatus.CUMPLIDO_EXACTO.value
            sig.first_appearance_date = draw_date.isoformat()
            sig.relative_day = delta
            sig.first_lottery = lottery
            sig.first_position = position
            sig.all_appearances.append(appearance)
            sig.closed_at = draw_date.isoformat()
            self._close_case_for_signal(sig, fulfillment=appearance)
            return sig

        # Family / neighbor soft hits (tracked, distinct from exact)
        t1_family = set(cat.get_table1_companions(sig.number))
        t2_neigh = set(cat.get_table2_neighbors(sig.number, exclude_self=True))
        if set(nums) & t1_family:
            sig.all_appearances.append({**appearance, "hit_type": "FAMILIA_T1"})
            if sig.status == SignalStatus.ACTIVO.value and delta >= 7:
                sig.status = SignalStatus.CUMPLIDO_FAMILIA_T1.value
                sig.closed_at = draw_date.isoformat()
                self._close_case_for_signal(sig, fulfillment={**appearance, "hit_type": "FAMILIA_T1"})
        elif set(nums) & t2_neigh:
            sig.all_appearances.append({**appearance, "hit_type": "VECINO_T2"})
            if sig.status == SignalStatus.ACTIVO.value and delta >= 7:
                sig.status = SignalStatus.CUMPLIDO_VECINO_T2.value
                sig.closed_at = draw_date.isoformat()
                self._close_case_for_signal(sig, fulfillment={**appearance, "hit_type": "VECINO_T2"})
        return sig

    def _close_case_for_signal(self, sig: ExperimentalSignal, fulfillment: dict[str, Any]) -> None:
        for case in self.cases.values():
            if case.signal_id == sig.signal_id and case.status == SignalStatus.ACTIVO.value:
                case.status = SignalStatus.CERRADO.value
                case.closed_at = sig.closed_at
                case.fulfillment = fulfillment
                chain = self.chains.get(case.chain_id or "")
                if chain:
                    chain.timeline.append(
                        {
                            "event": "CASE_CLOSED",
                            "case_id": case.case_id,
                            "signal": sig.number,
                            "date": case.closed_at,
                            "fulfillment": fulfillment,
                        }
                    )

    def start_new_analysis_same_day(self, analysis_date: str) -> dict[str, Any]:
        """Explicitly allow a new analysis the same day after closure."""
        cid = self.active_chain_id or new_id("chain")
        if cid not in self.chains:
            self.chains[cid] = ChainRecord(chain_id=cid)
        self.chains[cid].timeline.append(
            {
                "event": "NEW_ANALYSIS_STARTED",
                "date": analysis_date,
                "note": "Nuevo análisis permitido el mismo día tras cierre o en paralelo.",
            }
        )
        return {"chain_id": cid, "ok": True}


_STORE: SignalStore | None = None


def get_signal_store() -> SignalStore:
    global _STORE
    if _STORE is None:
        _STORE = SignalStore()
    return _STORE


def reset_signal_store() -> SignalStore:
    global _STORE
    _STORE = SignalStore()
    return _STORE
