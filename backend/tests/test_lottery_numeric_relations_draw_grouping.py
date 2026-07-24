"""Validación: el histórico agrupa números por draw_id, no por fecha+lotería."""

from __future__ import annotations

from datetime import date, time
from uuid import uuid4

from app.lottery.numeric_relations.analysis import analyze_observed_number
from app.lottery.numeric_relations.history import InMemoryDrawHistory
from app.lottery.numeric_relations.models import DrawNumberRef, HistoricalOccurrence, OccurrenceLimit


def test_same_lottery_date_different_draw_ids_stay_separate():
    """No asumir que misma fecha+lotería = mismo sorteo."""
    lot = uuid4()
    draw_a = uuid4()
    draw_b = uuid4()
    # Misma lotería y fecha; draw_time NULL en ambos — solo draw_id los distingue
    occ_a = HistoricalOccurrence(
        lottery_id=lot,
        lottery_name="Test",
        draw_id=draw_a,
        draw_date=date(2025, 8, 27),
        draw_time=None,
        observed_number=26,
        draw_numbers=(
            DrawNumberRef(1, 26),
            DrawNumberRef(2, 68),
            DrawNumberRef(3, 76),
            DrawNumberRef(4, 92),
        ),
    )
    occ_b = HistoricalOccurrence(
        lottery_id=lot,
        lottery_name="Test",
        draw_id=draw_b,
        draw_date=date(2025, 8, 27),
        draw_time=None,
        observed_number=26,
        draw_numbers=(
            DrawNumberRef(1, 26),
            DrawNumberRef(2, 11),
            DrawNumberRef(3, 12),
            DrawNumberRef(4, 13),
        ),
    )
    hist = InMemoryDrawHistory([occ_a, occ_b])
    found = hist.find_occurrences(26, [lot], OccurrenceLimit.all())
    assert len(found) == 2
    assert {str(o.draw_id) for o in found} == {str(draw_a), str(draw_b)}
    # Números del sorteo A no se mezclan con B
    nums_by_id = {str(o.draw_id): o.numbers_1_to_100() for o in found}
    assert 68 in nums_by_id[str(draw_a)] and 11 not in nums_by_id[str(draw_a)]
    assert 11 in nums_by_id[str(draw_b)] and 68 not in nums_by_id[str(draw_b)]


def test_analysis_dedupe_keys_include_draw_id_not_only_date():
    lot = uuid4()
    draw_a = uuid4()
    draw_b = uuid4()
    # Dos sorteos misma fecha; vecinos en A fortalecen, en B no
    hist = InMemoryDrawHistory(
        [
            HistoricalOccurrence(
                lottery_id=lot,
                lottery_name="Test",
                draw_id=draw_a,
                draw_date=date(2026, 5, 1),
                draw_time=time(14, 0),
                observed_number=26,
                draw_numbers=(
                    DrawNumberRef(1, 26),
                    DrawNumberRef(2, 68),
                    DrawNumberRef(3, 76),
                    DrawNumberRef(4, 92),
                ),
            ),
            HistoricalOccurrence(
                lottery_id=lot,
                lottery_name="Test",
                draw_id=draw_b,
                draw_date=date(2026, 5, 1),
                draw_time=time(21, 0),
                observed_number=26,
                draw_numbers=(
                    DrawNumberRef(1, 26),
                    DrawNumberRef(2, 1),
                    DrawNumberRef(3, 2),
                    DrawNumberRef(4, 3),
                ),
            ),
        ]
    )
    result = analyze_observed_number(26, [lot], OccurrenceLimit.all(), history=hist)
    top = result.candidates[0]
    assert top.number == 27
    assert top.score == 3  # solo del draw_a
    draw_ids_in_matches = {str(m.draw_id) for m in top.matches}
    assert str(draw_a) in draw_ids_in_matches
    assert str(draw_b) not in draw_ids_in_matches
    assert all(m.dedupe_key.startswith(f"{lot}|") or str(lot) in m.dedupe_key for m in top.matches)
    assert all(str(draw_a) in m.dedupe_key for m in top.matches)


def test_db_history_source_groups_by_draw_id_only():
    """Evidencia estática: el adaptador DB filtra números por LotteryDrawNumber.draw_id."""
    from pathlib import Path

    src = (
        Path(__file__).resolve().parents[1]
        / "app/lottery/numeric_relations/db_history.py"
    ).read_text(encoding="utf-8")
    assert "LotteryDrawNumber.draw_id == draw.id" in src
    assert "key = str(draw.id)" in src
    # No debe agrupar por (lottery_id, draw_date) como identidad del sorteo
    assert "group by lottery_id, draw_date" not in src.lower()
    assert "groupby((lottery" not in src.lower().replace(" ", "")
