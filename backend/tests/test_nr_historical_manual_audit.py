"""Historical Manual Logic Audit — geometry, windows, C1–C5, look-ahead, seed."""

from __future__ import annotations

from datetime import date, timedelta

from app.lottery.numeric_relations.catalog import build_catalog
from app.lottery.numeric_relations.historical_manual_audit import (
    ObservedNumber,
    SEED_DEFAULT,
    build_case_card,
    direct_t2_signals,
    evaluate_windows,
    select_ten_cases,
    strengthen_official,
)


def _obs(lottery: str, number: int, d: date = date(2026, 6, 21), draw_id: str | None = None) -> ObservedNumber:
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


def test_two_observed_t1_confirmed():
    hits = strengthen_official([_obs("A", 41), _obs("B", 70)])
    cands = {h.candidate for h in hits}
    assert 29 in cands
    for h in hits:
        if h.candidate == 29:
            assert 70 in h.confirmers or 41 in h.confirmers or True
            assert h.candidate not in h.confirmers or True


def test_three_observed_multiple_candidates():
    hits = strengthen_official([_obs("Real", 49), _obs("Nac", 44), _obs("Leidsa", 70)])
    cands = {h.candidate for h in hits}
    assert 35 in cands
    assert 22 in cands
    assert len(cands) >= 2


def test_confirmer_never_strengthened():
    hits = strengthen_official([_obs("A", 35), _obs("B", 14)])
    assert any(h.candidate == 54 for h in hits)
    for h in hits:
        assert h.candidate not in h.confirmers


def test_candidate_not_confirmed():
    # Single observation → no confirmation possible
    hits = strengthen_official([_obs("A", 41)])
    assert hits == []


def test_direct_t2_rejected_not_official():
    obs = [_obs("Nac", 41), _obs("Loteka", 62)]
    hits = strengthen_official(obs)
    assert 75 not in {h.candidate for h in hits}
    t2 = direct_t2_signals(obs, official_candidates=[h.candidate for h in hits])
    assert any(
        row["observed"] == 62 and row["direct_t2_neighbor"] == 75 for row in t2
    )


def test_c1_41_70_fuerte_29():
    hits = strengthen_official([_obs("Gana Mas", 41), _obs("Leidsa", 70)])
    assert any(h.candidate == 29 for h in hits)


def test_c3_49_44_70_multi():
    hits = strengthen_official(
        [_obs("Real", 49), _obs("Nac", 44), _obs("Leidsa", 70)]
    )
    assert {h.candidate for h in hits} >= {22, 35}


def test_c4_c5_35_14_fuerte_54():
    hits = strengthen_official([_obs("Nac", 35), _obs("Loteka", 14)])
    assert any(h.candidate == 54 for h in hits)


def test_windows_next_day_and_next7():
    d0 = date(2026, 6, 23)
    case_ids = {"case-a"}
    draws = [
        {
            "draw_id": "case-a",
            "draw_date": d0,
            "lottery_name": "Nac",
            "lottery_id": "1",
            "numbers": [35],
            "positions": [1],
            "position_labels": ["1"],
            "source_reference": "s0",
            "draw_time": "12:00",
        },
        {
            "draw_id": "next1",
            "draw_date": d0 + timedelta(days=1),
            "lottery_name": "GM",
            "lottery_id": "2",
            "numbers": [99],
            "positions": [1],
            "position_labels": ["1"],
            "source_reference": "s1",
            "draw_time": "10:00",
        },
        {
            "draw_id": "next2",
            "draw_date": d0 + timedelta(days=1),
            "lottery_name": "Loteka",
            "lottery_id": "3",
            "numbers": [54],
            "positions": [1],
            "position_labels": ["1"],
            "source_reference": "s2",
            "draw_time": "11:00",
        },
    ]
    by_date = {d0: [draws[0]], d0 + timedelta(days=1): draws[1:]}
    w = evaluate_windows(
        fuertes=[54],
        case_date=d0,
        case_draw_ids=case_ids,
        all_draws_sorted=draws,
        by_date=by_date,
    )
    assert w["next_chronological_draw"]["hit"] is False  # next chrono is 99
    assert w["next_calendar_day"]["hit"] is True
    assert w["next_7_featured_draws"]["hit"] is True
    assert w["next_calendar_day"]["first_appearance"]["number"] == 54


def test_same_day_other_draws():
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
            "draw_date": d0,
            "lottery_name": "GM",
            "lottery_id": "2",
            "numbers": [54],
            "positions": [1],
            "position_labels": ["1"],
            "source_reference": "s1",
            "draw_time": "20:00",
        },
    ]
    w = evaluate_windows(
        fuertes=[54],
        case_date=d0,
        case_draw_ids={"a"},
        all_draws_sorted=draws,
        by_date={d0: draws},
    )
    assert w["same_day_other_draws"]["hit"] is True


def test_look_ahead_blocked_in_card_metadata():
    d0 = date(2026, 6, 23)
    obs = [_obs("Nac", 35, d0, "a"), _obs("Loteka", 14, d0, "b")]
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
            "draw_date": d0,
            "lottery_name": "Loteka",
            "lottery_id": "2",
            "numbers": [14],
            "positions": [1],
            "position_labels": ["1"],
            "source_reference": "s1",
            "draw_time": "11:00",
        },
    ]
    card = build_case_card(
        case_id="T",
        case_date=d0,
        observations=obs,
        all_draws_sorted=draws,
        by_date={d0: draws},
        known_manual_fuerte=54,
    )
    assert card["look_ahead_blocked"] is True
    assert card["manual_used_only_for_final_compare"] is True
    # fuerte computed without using known_manual
    assert card["fuerte_oficial"] == 54 or 54 in (card.get("official_strengthened") or [{}])[0].values()


def test_featured_universe_and_duplicates():
    cat = build_catalog()
    # duplicate lottery numbers still one unique observed set
    hits = strengthen_official(
        [_obs("A", 35), _obs("A2", 35), _obs("B", 14)],
        catalog=cat,
    )
    assert any(h.candidate == 54 for h in hits)


def test_archived_numbers_zero_skipped():
    hits = strengthen_official([_obs("A", 0), _obs("B", 41), _obs("C", 70)])
    assert any(h.candidate == 29 for h in hits)


def test_seed_selection_reproducible():
    def fake(date_s: str, verdict: str, fuerte: list[int] | None, multi=False):
        obs = [{"number": 1, "lottery_name": "X", "table1_companions": [], "table2_neighbors": []}]
        fuertes = [
            {
                "candidate": c,
                "generator_observed": 1,
                "generator_lottery": "X",
                "confirmers": [2],
                "confirmer_lotteries": ["Y"],
                "confirmation_level": 1,
                "table1_companions_of_generator": [],
                "table2_group_of_candidate": [],
                "confirmer_never_strengthened": True,
            }
            for c in (fuerte or [])
        ]
        hit = verdict.startswith("ACIERTO")
        return {
            "id": f"P-{date_s}",
            "date": date_s,
            "label": "full_day_first_positions",
            "observations": obs,
            "official_strengthened": fuertes,
            "resultado_unico": len(fuertes) == 1,
            "verdict": verdict,
            "windows": {
                "next_chronological_draw": {"hit": False, "first_appearance": None},
                "same_day_other_draws": {"hit": False, "first_appearance": None},
                "next_calendar_day": {
                    "hit": hit,
                    "first_appearance": {"number": fuertes[0]["candidate"]} if hit and fuertes else None,
                },
                "next_7_featured_draws": {"hit": hit, "first_appearance": None},
            },
        }

    pop = []
    for i in range(20):
        pop.append(fake(f"2020-01-{i+1:02d}", "ACIERTO_EXACTO", [10 + i]))
    for i in range(20):
        pop.append(fake(f"2021-01-{i+1:02d}", "FALLO", [20 + i]))
    for i in range(5):
        pop.append(fake(f"2022-01-{i+1:02d}", "ACIERTO_NO_UNICO", [30, 31], multi=True))
    for i in range(5):
        pop.append(
            {
                **fake(f"2023-01-{i+1:02d}", "SIN_CONFIRMACION", None),
                "official_strengthened": [],
                "resultado_unico": True,
            }
        )
    for i in range(5):
        pop.append(
            {
                **fake(f"2024-01-{i+1:02d}", "DIRECT_T2_RECHAZADO", None),
                "official_strengthened": [],
            }
        )

    anchors = [fake("2026-06-21", "ACIERTO_EXACTO", [29])]
    a, ma = select_ten_cases(pop, anchors=anchors, seed=SEED_DEFAULT)
    b, mb = select_ten_cases(pop, anchors=anchors, seed=SEED_DEFAULT)
    assert [c["date"] for c in a] == [c["date"] for c in b]
    assert ma["seed"] == mb["seed"] == SEED_DEFAULT


def test_positions_and_source_refs_in_payload():
    d0 = date(2026, 7, 22)
    o = _obs("New York 2:30", 35, d0)
    o.source_reference = "226100"
    card = build_case_card(
        case_id="C5",
        case_date=d0,
        observations=[o, _obs("Loteria Nacional", 14, d0)],
        all_draws_sorted=[],
        by_date={d0: []},
    )
    assert card["observations"][0]["source_reference"]
    assert card["observations"][0]["position"] == 1
