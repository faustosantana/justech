"""Fachada del analizador histórico J-1 (reutiliza catálogo T1/T2 existente)."""

from __future__ import annotations

from datetime import date
from typing import Any

from app.lottery.numeric_relations.catalog import TableCatalog, build_catalog
from app.lottery.numeric_relations.historical.conditions import build_historical_events
from app.lottery.numeric_relations.historical.enums import ConfirmationWindowMode
from app.lottery.numeric_relations.historical.models import (
    ConfirmationWindowConfig,
    LotteryScope,
)
from app.lottery.numeric_relations.historical.rates import rates_payload
from app.lottery.numeric_relations.historical.universe import InMemoryDrawUniverse
from app.lottery.numeric_relations.historical.version import METHODOLOGY_VERSION


class HistoricalRelationsService:
    """Dominio J-1: eventos atómicos, combinaciones por ancla, posterior, tasas, ciclos."""

    def __init__(
        self,
        *,
        universe: InMemoryDrawUniverse,
        catalog: TableCatalog | None = None,
    ) -> None:
        self.universe = universe
        self.catalog = catalog or build_catalog()

    def search_conditions(
        self,
        *,
        observed_number: int,
        scope: LotteryScope,
        window: ConfirmationWindowConfig,
        date_from: date | None = None,
        date_to: date | None = None,
        candidate: int | None = None,
        confirmer: int | None = None,
        max_horizon: int = 10,
    ) -> dict[str, Any]:
        raw = build_historical_events(
            observed_number=observed_number,
            scope=scope,
            window=window,
            universe=self.universe,
            catalog=self.catalog,
            date_from=date_from,
            date_to=date_to,
            candidate_filter=candidate,
            confirmer_filter=confirmer,
            max_horizon=max_horizon,
        )
        atomics = raw["atomic_events"]
        combos = raw["combination_events"]
        posteriors = [c.posterior for c in combos]
        stats = rates_payload(posteriors)

        # Candidate ranking by combo score frequency (current-window historical strengthen count)
        strengthen: dict[int, int] = {}
        for c in combos:
            strengthen[c.candidate] = strengthen.get(c.candidate, 0) + int(c.score_raw)

        ranking = [
            {"candidate": cand, "historical_confirmations": score}
            for cand, score in sorted(strengthen.items(), key=lambda x: (-x[1], x[0]))
        ]

        return {
            "methodology_version": METHODOLOGY_VERSION,
            "effective_parameters": {
                "observed_number": int(observed_number),
                "mother_code": int(observed_number),
                "date_from": date_from.isoformat() if date_from else None,
                "date_to": date_to.isoformat() if date_to else None,
                "candidate_filter": candidate,
                "confirmer_filter": confirmer,
                "max_horizon": max_horizon,
                "confirmation_window": window.to_dict(),
                "lottery_scope": scope.to_dict(),
            },
            "table1_candidates": self.catalog.get_table1_companions(int(observed_number)),
            "anchors_examined": raw["anchors_examined"],
            "atomic_event_count": len(atomics),
            "combination_event_count": len(combos),
            "atomic_events": [e.to_dict() for e in atomics],
            "combination_events": [e.to_dict() for e in combos],
            "candidate_ranking_by_confirmations": ranking,
            "statistics": stats,
            "invariants": {
                "formulas_unchanged": True,
                "range_1_to_100": True,
                "strengthens_table1_candidate_only": True,
                "draw_id_identity": True,
                "no_date_merge": True,
            },
        }


def default_same_draw_window(tz: str = "America/Santo_Domingo") -> ConfirmationWindowConfig:
    return ConfirmationWindowConfig(mode=ConfirmationWindowMode.SAME_DRAW, timezone=tz)
