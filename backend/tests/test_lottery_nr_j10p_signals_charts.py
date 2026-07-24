"""J-10P — Señales, gráficas enriquecidas y explicación estructurada."""

from __future__ import annotations

from datetime import date, time, timedelta

import pytest

from app.lottery.numeric_relations.catalog import TableCatalog
from app.lottery.numeric_relations.historical.enums import ConfirmationWindowMode
from app.lottery.numeric_relations.historical.models import (
    ConfirmationWindowConfig,
    DrawRef,
    LotteryScope,
)
from app.lottery.numeric_relations.historical.number_explorer import NumberExplorerService
from app.lottery.numeric_relations.historical.universe import InMemoryDrawUniverse
from app.lottery.numeric_relations.models import FormattedComputation, TableKind


def _row(n: int, code: int, table: TableKind) -> FormattedComputation:
    return FormattedComputation(
        number=n,
        table=table,
        formula=f"test-{n}",
        visible_value=str(n),
        digits_without_point=str(n),
        digit_count=len(str(n)),
        digit_list=tuple(int(c) for c in str(n)),
        code=code,
    )


@pytest.fixture
def controlled_catalog() -> TableCatalog:
    t1_nums = {1: 34, 2: 34, 3: 34, 4: 34, 5: 34}
    t2_code = {4: 99, 6: 99, 7: 99, 8: 99, 9: 99, 10: 99, 11: 99, 1: 1, 2: 2, 3: 3, 5: 5}
    t1_rows = [_row(n, c, TableKind.TABLE_1) for n, c in t1_nums.items()]
    t2_rows = [_row(n, c, TableKind.TABLE_2) for n, c in t2_code.items()]
    t1_groups: dict[int, list[int]] = {}
    for n, c in t1_nums.items():
        t1_groups.setdefault(c, []).append(n)
    t2_groups: dict[int, list[int]] = {}
    for n, c in t2_code.items():
        t2_groups.setdefault(c, []).append(n)
    for g in t1_groups.values():
        g.sort()
    for g in t2_groups.values():
        g.sort()
    return TableCatalog(
        table1_rows=t1_rows,
        table2_rows=t2_rows,
        table1_number_to_code=t1_nums,
        table1_code_to_numbers=t1_groups,
        table2_number_to_code=t2_code,
        table2_code_to_numbers=t2_groups,
    )


def _draw(draw_id, lottery_id, d, numbers, *, name=None):
    return DrawRef(
        draw_id=draw_id,
        lottery_id=lottery_id,
        lottery_name=name or lottery_id,
        draw_date=d,
        draw_time=time(20, 0),
        numbers=tuple((i + 1, n) for i, n in enumerate(numbers)),
    )


@pytest.fixture
def universe(controlled_catalog) -> InMemoryDrawUniverse:
    u = InMemoryDrawUniverse()
    u.add(_draw("A1", "leidsa", date(2024, 1, 1), [34, 6, 9], name="Leidsa"))
    for i in range(1, 8):
        nums = [80 + i]
        if i == 3:
            nums = [4, 55]
        u.add(_draw(f"A1F{i}", "leidsa", date(2024, 1, 1) + timedelta(days=i), nums, name="Leidsa"))
    u.add(_draw("A2", "leidsa", date(2024, 3, 1), [34, 50, 51], name="Leidsa"))
    for i in range(1, 8):
        u.add(_draw(f"A2F{i}", "leidsa", date(2024, 3, 1) + timedelta(days=i), [70 + i], name="Leidsa"))
    u.add(_draw("A3", "nacional", date(2024, 5, 1), [34, 6], name="Nacional"))
    u.add(_draw("A3F1", "nacional", date(2024, 5, 2), [88], name="Nacional"))
    u.add(_draw("A3F2", "nacional", date(2024, 5, 3), [89], name="Nacional"))
    return u


@pytest.fixture
def scope() -> LotteryScope:
    return LotteryScope(
        primary_lottery_ids=("leidsa", "nacional"),
        confirming_lottery_ids=("leidsa", "nacional"),
        follow_up_lottery_ids=("leidsa", "nacional"),
        lottery_names={"leidsa": "Leidsa", "nacional": "Nacional"},
    )


@pytest.fixture
def window() -> ConfirmationWindowConfig:
    return ConfirmationWindowConfig(mode=ConfirmationWindowMode.SAME_DRAW)


@pytest.fixture
def svc(universe, controlled_catalog) -> NumberExplorerService:
    return NumberExplorerService(universe=universe, catalog=controlled_catalog)


def test_profile_signals_and_seven_draw_enrichment(svc, scope, window):
    p = svc.profile(number=34, scope=scope, window=window, max_horizon=7)
    charts = p["charts"]
    assert "senales" in charts
    assert isinstance(charts["senales"], list)
    if charts["senales"]:
        s0 = charts["senales"][0]
        for key in (
            "number",
            "confirmation_count",
            "evaluable_cases",
            "evidence_level",
            "activators_text",
            "historical_rate_label",
            "typical_cycle_label",
        ):
            assert key in s0
        assert "garantiza" not in s0["activators_text"].lower()
        assert "ganador" not in s0["activators_text"].lower()

    seven = charts["respuesta_en_siete_sorteos"]
    assert "casos_evaluables" in seven
    assert len(seven["por_posicion"]) == 7
    assert "evaluables" in seven["por_posicion"][0]
    assert "porcentaje" in seven["por_posicion"][0]
    assert charts["condicion_censurados"] == seven["sin_seguimiento_suficiente"]

    for lot in charts["apariciones_por_loteria"]:
        assert "porcentaje" in lot

    cand = charts["candidatos_fortalecidos"]
    assert cand
    assert "veces" in cand[0]


def test_why_strengthened_structured_fields(svc, scope, window):
    detail = svc.occurrence_detail(
        number=34, draw_id="A1", scope=scope, window=window, max_horizon=7
    )
    why = svc.why_strengthened(number=34, candidate=4, analyzed=detail)
    assert why["observed_number"] == 34
    assert why["candidato"] == 4
    assert why["related_confirmers"]
    assert why["confirmation_count"] == len(why["observed_confirmers"])
    assert why["numeros_no_modificables_por_ia"] is True
    assert why["pasos"]
    assert "4" in why["pasos"][1] or "4" in str(why["candidato"])


def test_display_order_rule_document():
    """Mirrors frontend signal-order.ts (orden de visualización, no fuerza oficial)."""

    def key(s):
        return (
            -s["confirmation_count"],
            -s["evaluable_cases"],
            -(s["rate_within_3"] if s["rate_within_3"] is not None else -1),
            s["typical_cycle"] if s["typical_cycle"] is not None else float("inf"),
            s["number"],
        )

    items = [
        {"number": 9, "confirmation_count": 1, "evaluable_cases": 10, "rate_within_3": 0.5, "typical_cycle": 3},
        {"number": 4, "confirmation_count": 2, "evaluable_cases": 5, "rate_within_3": 0.2, "typical_cycle": 4},
        {"number": 2, "confirmation_count": 2, "evaluable_cases": 8, "rate_within_3": 0.2, "typical_cycle": 2},
        {"number": 7, "confirmation_count": 2, "evaluable_cases": 8, "rate_within_3": 0.9, "typical_cycle": 5},
    ]
    ordered = sorted(items, key=key)
    assert [x["number"] for x in ordered] == [7, 2, 4, 9]


def test_empty_profile_zeros_not_hidden(svc, scope, window):
    p = svc.profile(number=99, scope=scope, window=window, max_horizon=7)
    assert p["header"]["aparecio"] == 0
    assert p["charts"]["condicion"]
    assert all("cantidad" in row for row in p["charts"]["condicion"])
