"""Metadata de dedupe y draws duplicados por contenido (Fase E)."""

from __future__ import annotations

from datetime import date
from uuid import uuid4

from app.lottery.numeric_relations.analysis import analyze_observed_number
from app.lottery.numeric_relations.history import InMemoryDrawHistory
from app.lottery.numeric_relations.models import DrawNumberRef, HistoricalOccurrence, OccurrenceLimit


def test_analysis_metadata_reports_draw_ids_and_keeps_content_duplicates_separate():
    lot = uuid4()
    d1, d2 = uuid4(), uuid4()
    # Identical content, distinct draw_id (sync residual pattern)
    shared_nums = (
        DrawNumberRef(1, 26),
        DrawNumberRef(2, 68),
        DrawNumberRef(3, 76),
        DrawNumberRef(4, 92),
    )
    hist = InMemoryDrawHistory(
        [
            HistoricalOccurrence(
                lottery_id=lot,
                lottery_name="Leidsa",
                draw_id=d1,
                draw_date=date(2026, 5, 1),
                observed_number=26,
                draw_numbers=shared_nums,
            ),
            HistoricalOccurrence(
                lottery_id=lot,
                lottery_name="Leidsa",
                draw_id=d2,
                draw_date=date(2026, 5, 1),
                observed_number=26,
                draw_numbers=shared_nums,
            ),
        ]
    )
    result = analyze_observed_number(26, [lot], OccurrenceLimit.all(), history=hist)
    meta = result.analysis_metadata
    assert meta["draw_ids_analyzed_count"] == 2
    assert set(meta["draw_ids_analyzed"]) == {str(d1), str(d2)}
    assert meta["possible_content_duplicate_draws_detected"] is True
    assert meta["content_duplicates_kept_separate_by_draw_id"] is True
    assert meta["internal_dedupe_discarded_count"] == 0
    # Score accumulates across both draw_ids (not silently merged)
    assert result.candidates[0].number == 27
    assert result.candidates[0].score == 6
    assert "sync" in meta["sync_duplicate_policy"].lower()
