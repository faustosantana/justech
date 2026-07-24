"""Fases C+D — API schemas, intent/planner, narrativa, centralización del motor."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.lottery.ai.conversation_state import ConversationState
from app.lottery.ai.planner import build_plan
from app.lottery.ai.understanding import understand
from app.lottery.numeric_relations.analysis import analyze_observed_number
from app.lottery.numeric_relations.api_schemas import (
    AnalyzeBody,
    enrich_table_rows,
    limit_from_body,
)
from app.lottery.numeric_relations.catalog import build_catalog
from app.lottery.numeric_relations.chat_narrative import format_numeric_relations_reply
from app.lottery.numeric_relations.history import InMemoryDrawHistory
from app.lottery.numeric_relations.models import DrawNumberRef, HistoricalOccurrence, OccurrenceLimit
from app.services.lottery_ai_contracts import LOTTERY_TOOL_CATALOG, LotteryToolName, TOOL_PERMISSIONS
from app.services.lottery_chat_context import LotterySessionContext
from app.services.lottery_intent import resolve_intent


def _controlled_history():
    lot = uuid4()
    occ = HistoricalOccurrence(
        lottery_id=lot,
        lottery_name="Quiniela Leidsa (controlado)",
        draw_id=uuid4(),
        draw_date=date(2026, 5, 1),
        observed_number=26,
        draw_numbers=(
            DrawNumberRef(position=1, drawn_number=26, position_label="Primera"),
            DrawNumberRef(position=2, drawn_number=68, position_label="Segunda"),
            DrawNumberRef(position=3, drawn_number=76, position_label="Tercera"),
            DrawNumberRef(position=4, drawn_number=92, position_label="Cuarta"),
        ),
    )
    return lot, InMemoryDrawHistory([occ])


def test_api_analyze_body_validates_observed_number_1_100():
    with pytest.raises(ValidationError):
        AnalyzeBody(observed_number=0, lottery_ids=[uuid4()], occurrence_mode="last_k", occurrence_k=10)
    with pytest.raises(ValidationError):
        AnalyzeBody(observed_number=101, lottery_ids=[uuid4()], occurrence_mode="last_k", occurrence_k=10)
    ok = AnalyzeBody(observed_number=26, lottery_ids=[uuid4()], occurrence_mode="last_k", occurrence_k=10)
    assert ok.observed_number == 26


def test_api_no_hidden_occurrence_default():
    body = AnalyzeBody(
        observed_number=26,
        lottery_ids=[uuid4()],
        occurrence_mode="last_k",
        occurrence_k=None,
    )
    with pytest.raises(ValueError, match="occurrence_k is required"):
        limit_from_body(body)
    all_body = AnalyzeBody(
        observed_number=26,
        lottery_ids=[uuid4()],
        occurrence_mode="all",
        occurrence_k=None,
    )
    assert limit_from_body(all_body).mode == "all"


def test_tables_api_enrichment_keeps_table1_and_table2_separate():
    t1 = enrich_table_rows("table1")
    t2 = enrich_table_rows("table2")
    assert len(t1) == 100 and len(t2) == 100
    assert t1[0]["number"] == 1 and "group_numbers" in t1[0]
    assert all(r.get("table") == "table_1" for r in t1)
    assert all(r.get("table") == "table_2" for r in t2)


def test_tool_registered_with_permissions():
    assert LotteryToolName.ANALYZE_NUMERIC_RELATIONS in TOOL_PERMISSIONS
    names = {c.name for c in LOTTERY_TOOL_CATALOG}
    assert LotteryToolName.ANALYZE_NUMERIC_RELATIONS in names


def test_intent_single_lottery_last_10():
    ctx = LotterySessionContext()
    intent = resolve_intent(
        "Analiza el 26 en las últimas 10 veces que salió en Leidsa",
        ctx,
    )
    assert intent.kind == "tool"
    assert intent.tool == LotteryToolName.ANALYZE_NUMERIC_RELATIONS
    assert intent.params["observed_number"] == 26
    assert intent.params["occurrence_mode"] == "last_k"
    assert intent.params["occurrence_k"] == 10
    assert "leidsa" in str(intent.params.get("lottery") or intent.params.get("lotteries")).lower()


def test_intent_multi_lottery():
    ctx = LotterySessionContext()
    intent = resolve_intent(
        "Analiza el 45 en Leidsa y Loteka con las últimas 20 veces",
        ctx,
    )
    assert intent.kind == "tool"
    assert intent.tool == LotteryToolName.ANALYZE_NUMERIC_RELATIONS
    lots = intent.params.get("lotteries") or []
    assert len(lots) >= 2
    assert intent.params["occurrence_k"] == 20


def test_intent_all_occurrences():
    ctx = LotterySessionContext()
    intent = resolve_intent(
        "Muéstrame todas las ocurrencias disponibles del 26 en Leidsa",
        ctx,
    )
    assert intent.kind == "tool"
    assert intent.params["occurrence_mode"] == "all"


def test_intent_asks_when_occurrence_limit_missing():
    ctx = LotterySessionContext()
    intent = resolve_intent(
        "¿Cuáles compañeros están más fuertes cuando sale el 34 en Leidsa?",
        ctx,
    )
    assert intent.kind == "clarify"
    assert "occurrence_limit" in (intent.params.get("pending_slots") or [])
    assert "5" in (intent.clarify_message or "") and "todas" in (intent.clarify_message or "").lower()


def test_intent_asks_when_lottery_missing():
    ctx = LotterySessionContext()
    intent = resolve_intent(
        "Busca las últimas 20 veces que salió el 18 y revisa sus vecinos",
        ctx,
    )
    assert intent.kind == "clarify"
    assert "lottery" in (intent.params.get("pending_slots") or [])


def test_planner_single_tool_to_motor():
    understanding, _ = understand(
        "Analiza el 26 en las últimas 10 veces que salió en Leidsa",
        ConversationState(),
    )
    plan = build_plan(understanding)
    assert len(plan.steps) == 1
    assert plan.steps[0].tool == LotteryToolName.ANALYZE_NUMERIC_RELATIONS.value
    assert plan.rationale == "numeric_relations_single_engine"


def test_controlled_example_ranking_and_zero_score():
    lot, hist = _controlled_history()
    result = analyze_observed_number(
        26,
        [lot],
        OccurrenceLimit.all(),
        history=hist,
        catalog=build_catalog(),
        lottery_names={str(lot): "Quiniela Leidsa (controlado)"},
    )
    assert result.direct_companions == [27, 38]
    assert result.candidates[0].number == 27
    assert result.candidates[0].score == 3
    assert result.candidates[0].table2_code == 53
    assert result.candidates[0].neighbors == [68, 76, 92]
    assert result.candidates[1].number == 38
    assert result.candidates[1].score == 0
    assert len(result.candidates) == 2
    assert all(m.trace for m in result.candidates[0].matches)


def test_exclude_observed_n_and_dedupe_and_multi_neighbor():
    lot, hist = _controlled_history()
    result = analyze_observed_number(26, [lot], OccurrenceLimit.all(), history=hist)
    keys = [m.dedupe_key for m in result.candidates[0].matches]
    assert len(keys) == len(set(keys))
    assert 26 not in result.candidates[0].matched_neighbors
    assert result.candidates[0].score == 3


def test_last_k_vs_all_occurrence_limits():
    lot = uuid4()
    occs = []
    for i in range(15):
        occs.append(
            HistoricalOccurrence(
                lottery_id=lot,
                lottery_name="Test",
                draw_id=uuid4(),
                draw_date=date(2026, 1, 1 + i),
                observed_number=26,
                draw_numbers=(DrawNumberRef(position=1, drawn_number=26),),
            )
        )
    hist = InMemoryDrawHistory(occs)
    last5 = analyze_observed_number(26, [lot], OccurrenceLimit.last_k(5), history=hist)
    allx = analyze_observed_number(26, [lot], OccurrenceLimit.all(), history=hist)
    assert last5.occurrences_used == 5
    assert last5.occurrences_found == 15
    assert allx.occurrences_used == 15


def test_chat_template_based_only_on_motor_result():
    data = {
        "observed_number": 26,
        "mother_code": 26,
        "lottery_names": ["Leidsa"],
        "occurrence_limit": {"mode": "last_k", "k": 10},
        "occurrences_found": 1,
        "occurrences_used": 1,
        "direct_companions": [27, 38],
        "ranking": [
            {
                "number": 27,
                "score": 3,
                "table2_code": 53,
                "neighbors": [68, 76, 92],
                "matched_neighbors": [68, 76, 92],
                "matches": [
                    {
                        "neighbor": 68,
                        "lottery_name": "Leidsa",
                        "draw_date": "2026-05-01",
                        "position": 2,
                    }
                ],
            },
            {
                "number": 38,
                "score": 0,
                "table2_code": 1,
                "neighbors": [],
                "matched_neighbors": [],
                "matches": [],
            },
        ],
    }
    text = format_numeric_relations_reply(data)
    assert "26" in text and "score 3" in text and "38" in text and "score 0" in text
    assert "certeza" in text.lower()


def test_chat_template_no_invention_when_empty():
    data = {
        "observed_number": 26,
        "mother_code": 26,
        "lottery_names": ["Leidsa"],
        "occurrence_limit": {"mode": "all"},
        "occurrences_found": 0,
        "occurrences_used": 0,
        "direct_companions": [27, 38],
        "ranking": [],
    }
    text = format_numeric_relations_reply(data)
    assert "No encontré ocurrencias" in text
    assert "No invento" in text
    assert "score 3" not in text


def test_admin_screen_permission_gate():
    from app.core.admin_permissions import role_has_permission

    assert role_has_permission("owner", "lottery_admin_ai") or role_has_permission(
        "owner", "lottery.statistics"
    )
    assert not role_has_permission("lottery_client", "lottery_admin_ai")


def test_centralization_single_engine_symbol():
    """Evidence: API + tool share analyze_from_db; no local math in those layers."""
    root = Path(__file__).resolve().parents[1]
    tool_src = (root / "app/services/lottery_tools.py").read_text(encoding="utf-8")
    api_src = (root / "app/api/v1/lottery_numeric_relations.py").read_text(encoding="utf-8")
    chat_src = (root / "app/services/lottery_chat_service.py").read_text(encoding="utf-8")
    assert "analyze_from_db" in tool_src
    assert "ANALYZE_NUMERIC_RELATIONS" in tool_src
    assert "analyze_from_db" in api_src
    assert "calculate_table1_value" not in api_src
    assert "format_numeric_relations_reply" in chat_src
    assert "1220" not in chat_src.split("lottery_analyze_numeric_relations")[1][:800]


def test_ui_page_keeps_table_tabs_separate():
    page = (
        Path(__file__).resolve().parents[2]
        / "frontend/src/app/(platform)/lottery/admin/numeric-relations/page.tsx"
    )
    text = page.read_text(encoding="utf-8")
    assert 'id: "table1"' in text and 'id: "table2"' in text
    assert 'id: "groups1"' in text and 'id: "groups2"' in text
    assert "no mezcla" in text.lower() or "nunca se mezclan" in text.lower()
