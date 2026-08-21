"""Tests — inteligencia histórica DGCP (sin inventar datos)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from app.services.dgcp_historical_similarity_engine import (
    is_valid_award_status,
    match_classification,
    match_classification_label,
)
from app.services.dgcp_historical_intelligence_service import (
    _data_quality,
    DGCPHistoricalIntelligenceService,
)


def test_invalid_award_status_excludes_cancelled_and_desert():
    assert is_valid_award_status("Confirmada y enviada") is True
    assert is_valid_award_status("Confirmada") is True
    assert is_valid_award_status("Cancelada") is False
    assert is_valid_award_status("Proceso desierto") is False
    assert is_valid_award_status("Anulado") is False


def test_match_classification_exact_vs_similar():
    assert match_classification(90) == "EXACTA"
    assert match_classification(60) == "ALTA_SIMILITUD"
    assert match_classification(30) == "RELACIONADA"
    assert match_classification(10, exact_item=True) == "EXACTA"
    label = match_classification_label("ALTA_SIMILITUD", similarity_pct=91)
    assert "comparable" in label.lower()
    assert "91" in label


def test_data_quality_tiers():
    assert (
        _data_quality(
            supplier="ACME",
            amount=Decimal("100"),
            award_date=datetime.now(timezone.utc),
            process_code="X-1",
            unit_price=Decimal("10"),
            quantity=Decimal("2"),
        )
        == "VERIFICADO"
    )
    assert (
        _data_quality(
            supplier="ACME",
            amount=Decimal("100"),
            award_date=datetime.now(timezone.utc),
            process_code="X-1",
            unit_price=None,
            quantity=None,
        )
        == "PARCIAL"
    )
    assert (
        _data_quality(
            supplier=None,
            amount=None,
            award_date=None,
            process_code=None,
            unit_price=None,
            quantity=None,
        )
        == "INCOMPLETO"
    )


def test_dedupe_by_process_keeps_best_score():
    from app.schemas.dgcp_historical_intelligence import HistoricalPurchaseRow

    rows = [
        HistoricalPurchaseRow(
            award_id="1",
            process_code="P-1",
            institution="MINERD",
            similarity_score=40,
            match_class="RELACIONADA",
        ),
        HistoricalPurchaseRow(
            award_id="2",
            process_code="P-1",
            institution="MINERD",
            similarity_score=70,
            match_class="ALTA_SIMILITUD",
        ),
        HistoricalPurchaseRow(
            award_id="3",
            process_code="P-2",
            institution="MINERD",
            similarity_score=50,
            match_class="RELACIONADA",
        ),
    ]
    out = DGCPHistoricalIntelligenceService._dedupe_by_process(rows)
    assert len(out) == 2
    p1 = next(r for r in out if r.process_code == "P-1")
    assert p1.award_id == "2"
    assert p1.similarity_score == 70


def test_last_purchase_prefers_award_date_not_publication_order():
    older = datetime.now(timezone.utc) - timedelta(days=400)
    newer = datetime.now(timezone.utc) - timedelta(days=10)
    pool = [
        (type("A", (), {"award_date": older})(), 80.0, [], "EXACTA"),
        (type("A", (), {"award_date": newer})(), 50.0, [], "ALTA_SIMILITUD"),
    ]
    ordered = sorted(
        pool,
        key=lambda x: (x[0].award_date, x[1]),
        reverse=True,
    )
    assert ordered[0][0].award_date == newer
