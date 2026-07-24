"""Consulta histórica: solo ocurrencias reales con drawn_number = N."""

from __future__ import annotations

from typing import Protocol
from uuid import UUID

from app.lottery.numeric_relations.models import HistoricalOccurrence, OccurrenceLimit


class DrawHistoryPort(Protocol):
    def find_occurrences(
        self,
        observed_number: int,
        lottery_ids: list[UUID | str],
        limit: OccurrenceLimit,
    ) -> list[HistoricalOccurrence]:
        """Devuelve ocurrencias donde salió realmente observed_number, más recientes primero."""
        ...


class InMemoryDrawHistory:
    """Puerto en memoria para pruebas (Fase B) — no toca producción ni sync."""

    def __init__(self, occurrences: list[HistoricalOccurrence] | None = None) -> None:
        self._occurrences = list(occurrences or [])

    def find_occurrences(
        self,
        observed_number: int,
        lottery_ids: list[UUID | str],
        limit: OccurrenceLimit,
    ) -> list[HistoricalOccurrence]:
        wanted = {str(x) for x in lottery_ids}
        n = int(observed_number)
        matched: list[HistoricalOccurrence] = []
        for occ in self._occurrences:
            if str(occ.lottery_id) not in wanted:
                continue
            # Evento = drawn_number == N (no por compañeros)
            if any(int(ref.drawn_number) == n for ref in occ.draw_numbers):
                matched.append(occ)
        matched.sort(
            key=lambda o: (o.draw_date, o.draw_time or "", str(o.draw_id)),
            reverse=True,
        )
        if limit.mode == "all":
            return matched
        return matched[: int(limit.k or 0)]
