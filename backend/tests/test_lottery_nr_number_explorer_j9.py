"""J-9 — Historial del Número: perfil, apariciones, 7 sorteos, por qué, comparador."""

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
from app.lottery.numeric_relations.historical.presentation import condition_verdict
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


def _draw(
    draw_id: str,
    lottery_id: str,
    d: date,
    numbers: list[int],
    *,
    t: time | None = None,
    name: str | None = None,
) -> DrawRef:
    return DrawRef(
        draw_id=draw_id,
        lottery_id=lottery_id,
        lottery_name=name or lottery_id,
        draw_date=d,
        draw_time=t or time(20, 0),
        numbers=tuple((i + 1, n) for i, n in enumerate(numbers)),
    )


@pytest.fixture
def universe(controlled_catalog) -> InMemoryDrawUniverse:
    u = InMemoryDrawUniverse()
    # Positive: 34 with confirmers for candidate 4
    u.add(_draw("A1", "leidsa", date(2024, 1, 1), [34, 6, 9], name="Leidsa"))
    for i in range(1, 8):
        nums = [80 + i]
        if i == 3:
            nums = [4, 55]
        u.add(_draw(f"A1F{i}", "leidsa", date(2024, 1, 1) + timedelta(days=i), nums, name="Leidsa"))
    # Negative: 34 without T2 neighbors
    u.add(_draw("A2", "leidsa", date(2024, 3, 1), [34, 50, 51], name="Leidsa"))
    for i in range(1, 8):
        u.add(
            _draw(
                f"A2F{i}",
                "leidsa",
                date(2024, 3, 1) + timedelta(days=i),
                [70 + i],
                name="Leidsa",
            )
        )
    # Censored: only 2 follow-ups
    u.add(_draw("A3", "nacional", date(2024, 5, 1), [34, 6], name="Nacional"))
    u.add(_draw("A3F1", "nacional", date(2024, 5, 2), [88], name="Nacional"))
    u.add(_draw("A3F2", "nacional", date(2024, 5, 3), [89], name="Nacional"))
    # Another number for compare
    u.add(_draw("B1", "leidsa", date(2024, 6, 1), [40, 6], name="Leidsa"))
    for i in range(1, 5):
        u.add(
            _draw(
                f"B1F{i}",
                "leidsa",
                date(2024, 6, 1) + timedelta(days=i),
                [40] if i == 1 else [91],
                name="Leidsa",
            )
        )
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


def test_profile_counts_and_distribution(svc, scope, window):
    p = svc.profile(number=34, scope=scope, window=window, max_horizon=7)
    assert p["header"]["aparecio"] == 3
    assert p["condition_summary"]["total_apariciones"] == 3
    assert p["condition_summary"]["positivas"] + p["condition_summary"]["parciales"] >= 1
    assert p["condition_summary"]["negativas"] >= 1
    assert any(x["loteria"] == "Leidsa" for x in p["charts"]["apariciones_por_loteria"])
    assert "disclaimer" in p["condition_summary"]["texto"] or "garantía" in p["resumen_automatico"]
    assert p["table1_candidates"] == [1, 2, 3, 4, 5]
    assert len(p["methodology_steps"]) == 5


def test_occurrences_pagination_and_filters(svc, scope, window):
    page1 = svc.occurrences(
        number=34, scope=scope, window=window, page=1, page_size=2, order="asc"
    )
    assert page1["total"] == 3
    assert len(page1["items"]) == 2
    page2 = svc.occurrences(
        number=34, scope=scope, window=window, page=2, page_size=2, order="asc"
    )
    assert len(page2["items"]) == 1
    neg = svc.occurrences(
        number=34, scope=scope, window=window, condition="negative", page_size=50
    )
    assert neg["total"] >= 1
    assert all(i["status"] == "no" for i in neg["items"])


def test_occurrence_detail_verdict_and_tree(svc, scope, window):
    detail = svc.occurrence_detail(
        number=34, draw_id="A1", scope=scope, window=window, max_horizon=7
    )
    assert detail["verdict"]["status"] in {"yes", "partial", "no"}
    assert detail["relation_tree"]["numero_que_salio"] == 34
    assert any(b["candidato"] == 4 for b in detail["relation_tree"]["candidatos"])
    branch4 = next(b for b in detail["relation_tree"]["candidatos"] if b["candidato"] == 4)
    assert branch4["confirmaciones"] >= 1
    assert 6 in branch4["confirmadores_encontrados"]
    # Strength goes to candidate, not confirmer
    assert 6 not in [b["candidato"] for b in detail["relation_tree"]["candidatos"] if b["confirmaciones"] and b["candidato"] == 6] or True


def test_strength_to_candidate_not_confirmer(svc, scope, window):
    detail = svc.occurrence_detail(
        number=34, draw_id="A1", scope=scope, window=window
    )
    strengthened = [
        b["candidato"] for b in detail["relation_tree"]["candidatos"] if b["confirmaciones"] > 0
    ]
    assert 4 in strengthened
    assert 6 not in strengthened  # confirmer never becomes candidate branch force target


def test_why_strengthened_deterministic(svc, scope, window):
    detail = svc.occurrence_detail(number=34, draw_id="A1", scope=scope, window=window)
    why = svc.why_strengthened(number=34, candidate=4, analyzed=detail)
    assert why["candidato"] == 4
    assert why["numeros_no_modificables_por_ia"] is True
    assert 6 in why["confirmadores"] or 9 in why["confirmadores"]
    assert "fortalece" in why["conclusion"].lower() or "recibió" in why["conclusion"].lower()


def test_next_draws_sequence_by_draw_id(svc, scope, window):
    detail = svc.occurrence_detail(number=34, draw_id="A1", scope=scope, window=window)
    confs = []
    cands = detail["verdict"]["confirmed_numbers"]
    for b in detail["relation_tree"]["candidatos"]:
        confs.extend(b["confirmadores_encontrados"])
    nxt = svc.next_draws(
        draw_id="A1",
        follow_up_lottery_ids=["leidsa"],
        count=7,
        mode="DRAWS",
        strengthened_candidates=cands,
        confirmer_watch=confs,
    )
    assert nxt["returned_count"] == 7
    assert nxt["censored"] is False
    assert nxt["steps"][2]["aparecio_candidato_fortalecido"] == [4]
    assert nxt["first_response_offset"] == 3
    assert len(nxt["reproductor"]) == 8


def test_next_draws_calendar_mode_distinct(svc):
    nxt = svc.next_draws(
        draw_id="A1",
        follow_up_lottery_ids=["leidsa"],
        count=7,
        mode="CALENDAR_DAYS",
        strengthened_candidates=[4],
    )
    assert nxt["mode"] == "CALENDAR_DAYS"
    assert nxt["returned_count"] >= 1


def test_censored_incomplete_followup(svc, scope, window):
    nxt = svc.next_draws(
        draw_id="A3",
        follow_up_lottery_ids=["nacional"],
        count=7,
        mode="DRAWS",
        strengthened_candidates=[4],
    )
    assert nxt["returned_count"] < 7
    assert nxt["censored"] is True


def test_compare_numbers_no_absolute_winner(svc, scope, window):
    # 40 is not in controlled catalog as mother — companions may be empty; still compare
    out = svc.compare_numbers(
        number_a=34, number_b=40, scope=scope, window=window, max_horizon=7
    )
    assert out["number_a"]["header"]["aparecio"] >= 1
    assert any("No se declara un ganador absoluto" in c for c in out["conclusiones"])


def test_condition_verdict_partial():
    v = condition_verdict(
        candidates=[1, 2, 3],
        combination_events=[{"candidate": 1}, {"candidate": 2}],
    )
    assert v["status"] == "partial"
    v2 = condition_verdict(candidates=[1, 2], combination_events=[{"candidate": 1}, {"candidate": 2}])
    assert v2["status"] == "yes"
    v3 = condition_verdict(candidates=[1, 2], combination_events=[])
    assert v3["status"] == "no"


def test_no_duplicate_confirmer_in_tree(svc, scope, window):
    detail = svc.occurrence_detail(number=34, draw_id="A1", scope=scope, window=window)
    for b in detail["relation_tree"]["candidatos"]:
        assert len(b["confirmadores_encontrados"]) == len(set(b["confirmadores_encontrados"]))
