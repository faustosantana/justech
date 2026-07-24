"""Puntuación y deduplicación de coincidencias vecino→compañero."""

from __future__ import annotations

from app.lottery.numeric_relations.models import Match


def make_dedupe_key(
    *,
    lottery_id: object,
    draw_id: object,
    position: object,
    neighbor: int,
    companion: int,
) -> str:
    return f"{lottery_id}|{draw_id}|{position}|{neighbor}|{companion}"


def score_candidate(matches: list[Match]) -> int:
    """Regla inicial: +1 por cada Match válido (ya deduplicado)."""
    return sum(int(m.points) for m in matches)
