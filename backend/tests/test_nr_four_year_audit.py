"""Four-year audit — geometry, windows, seed, no look-ahead selection."""

from __future__ import annotations

from datetime import date, timedelta

from app.lottery.numeric_relations.catalog import build_catalog
from app.lottery.numeric_relations.four_year_audit import (
    build_day_case,
    classify_day_level,
    decide_verdicts,
    evaluate_all_windows,
    pick_ten_explained,
    security_level,
)
from app.lottery.numeric_relations.historical_manual_audit import (
    SEED_DEFAULT,
    ObservedNumber,
    strengthen_official,
)


def _obs(lottery: str, number: int, d: date, draw_id: str | None = None) -> ObservedNumber:
    return ObservedNumber(
        lottery_id=f"id-{lottery}",
        lottery_name=lottery,
        draw_id=draw_id or f"d-{lottery}-{number}",
        draw_date=d,
        draw_time="12:00:00",
        position=1,
        position_label="1",
        number=number,
        source_reference=f"ref-{number}",
    )


def test_c1_c4_c5_geometry():
    assert any(h.candidate == 29 for h in strengthen_official([_obs("A", 41, date(2026, 6, 21)), _obs("B", 70, date(2026, 6, 21))]))
    assert any(h.candidate == 54 for h in strengthen_official([_obs("A", 35, date(2026, 6, 23)), _obs("B", 14, date(2026, 6, 23))]))


def test_c2_direct_t2_not_official():
    hits = strengthen_official([_obs("A", 41, date(2026, 6, 21)), _obs("B", 62, date(2026, 6, 21))])
    assert 75 not in {h.candidate for h in hits}


def test_c3_multi():
    hits = strengthen_official(
        [
            _obs("R", 49, date(2026, 6, 21)),
            _obs("N", 44, date(2026, 6, 21)),
            _obs("L", 70, date(2026, 6, 21)),
        ]
    )
    assert {h.candidate for h in hits} >= {22, 35}


def test_level_classification():
    hits = strengthen_official([_obs("A", 35, date.today()), _obs("B", 14, date.today())])
    assert classify_day_level(hits, has_t1_unconfirmed=False, has_direct_t2=False).startswith("NIVEL_2")
    assert classify_day_level([], has_t1_unconfirmed=True, has_direct_t2=False) == "NIVEL_1_T1_SIN_CONFIRMACION"
    assert classify_day_level([], has_t1_unconfirmed=False, has_direct_t2=True) == "NIVEL_X_DIRECT_T2_RECHAZADO"


def test_windows_separated():
    d0 = date(2026, 6, 23)
    draws = [
        {
            "draw_id": "a",
            "draw_date": d0,
            "lottery_name": "Nac",
            "lottery_id": "1",
            "numbers": [35],
            "positions": [1],
            "position_labels": ["1"],
            "source_reference": "s0",
            "draw_time": "10:00",
        },
        {
            "draw_id": "b",
            "draw_date": d0 + timedelta(days=1),
            "lottery_name": "GM",
            "lottery_id": "2",
            "numbers": [54],
            "positions": [1],
            "position_labels": ["1"],
            "source_reference": "s1",
            "draw_time": "11:00",
        },
    ]
    w = evaluate_all_windows(
        [54],
        case_date=d0,
        case_draw_ids={"a"},
        all_draws_sorted=draws,
        by_date={d0: [draws[0]], d0 + timedelta(days=1): [draws[1]]},
    )
    assert w["W3_next_calendar_day"]["hit"] is True
    assert w["W1_next_chronological_draw"]["hit"] is True


def test_seed_explained_reproducible():
    cat = build_catalog()
    d0 = date(2024, 1, 1)
    days = []
    for i in range(40):
        d = d0 + timedelta(days=i)
        obs = [_obs("A", 35, d, f"a{i}"), _obs("B", 14, d, f"b{i}")]
        days.append(
            build_day_case(
                case_date=d,
                observations=obs,
                catalog=cat,
                all_draws_sorted=[],
                by_date={d: []},
            )
        )
    a = pick_ten_explained(days, seed=SEED_DEFAULT)
    b = pick_ten_explained(days, seed=SEED_DEFAULT)
    assert [c["date"] for c in a] == [c["date"] for c in b]


def test_security_near_one_not_strong():
    assert security_level(n=100, lift=1.02, ci=(0.9, 1.1), years_positive=3, years_total=3, oos_lift=1.0).startswith("D_")


def test_decide_verdicts_no_predictive_near_one():
    agg = {
        "baselines_w3": {
            "official_t1_x_t2": {
                "hits": 226,
                "denominator": 794,
                "hit_rate": 0.284635,
                "wilson_ci_95": [0.25, 0.32],
            },
            "lift_official_vs_random_same_k": 1.066,
        },
        "walk_forward": [],
    }
    v = decide_verdicts(agg)
    assert v["veredicto_matematico"] == "GEOMETRIA_CORRECTA"
    assert v["veredicto_estadistico"] == "SIN_VENTAJA"
    assert "NO_GO_PARA_J11A_PREDICTIVO" in v["decision_j11a"]
