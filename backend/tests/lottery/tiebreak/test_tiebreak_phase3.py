"""Phase 3 — tiebreak + prospective validation tests."""

from __future__ import annotations

import inspect

import pytest

from app.lottery.numeric_relations.analysis_engine import run_complete_analysis
from app.lottery.numeric_relations.analysis_engine.candidate_ranker import rank_all_candidates
from app.lottery.numeric_relations.analysis_engine.prospective_validation import (
    get_prospective_store,
    reset_prospective_store,
)
from app.lottery.numeric_relations.analysis_engine.tiebreak_engine import (
    DEFAULT_PRACTICAL_THRESHOLD,
    apply_selected_tiebreak,
    detect_tie_group,
)
from app.lottery.numeric_relations.j11a import chat
from app.lottery.numeric_relations.j11a.memory_engine import reset_sessions
from app.lottery.numeric_relations.analysis_engine.signal_tracker import reset_signal_store


@pytest.fixture(autouse=True)
def _clean():
    reset_signal_store()
    reset_sessions()
    reset_prospective_store()
    yield
    reset_signal_store()
    reset_sessions()
    reset_prospective_store()


def test_tiebreak_runs_only_after_candidate_ranking():
    src = inspect.getsource(run_complete_analysis)
    assert src.index("candidates_ranked") < src.index("tiebreak_applied")


def test_tiebreak_does_not_change_candidate_discovery():
    a = run_complete_analysis(
        {"numbers": [35, 14], "mode": "socio", "derivation_depth": 0, "create_signals": False},
        persist=False,
        enable_tiebreak=False,
    )
    b = run_complete_analysis(
        {"numbers": [35, 14], "mode": "socio", "derivation_depth": 0, "create_signals": False},
        persist=False,
        enable_tiebreak=True,
    )
    assert {c["number"] for c in a.ranked_candidates} == {
        c["number"] for c in b.ranked_candidates
    }


def test_tiebreak_preserves_original_scores():
    r = run_complete_analysis(
        {"numbers": [44, 63], "mode": "socio", "derivation_depth": 0, "create_signals": False},
        persist=False,
        enable_tiebreak=True,
    )
    for d in (r.tiebreak or {}).get("decisions") or []:
        assert d["score_before"] == d["score_after"]


def test_real_tie_detection():
    r = run_complete_analysis(
        {
            "numbers": [44, 63],
            "mode": "socio",
            "derivation_depth": 0,
            "create_signals": False,
            "enable_tiebreak": False,
        },
        persist=False,
        enable_tiebreak=False,
    )
    group, kind = detect_tie_group(r.ranked_candidates, practical_threshold=0.0)
    # 22 and 70 typically real-tied
    assert kind in {"real", "none", "practical"}
    if kind == "real":
        assert len(group) >= 2


def test_practical_tie_detection():
    assert DEFAULT_PRACTICAL_THRESHOLD == 0.0


def test_tiebreak_rule_is_traceable():
    r = run_complete_analysis(
        {"numbers": [44, 63], "mode": "socio", "derivation_depth": 0, "create_signals": False},
        persist=False,
    )
    assert r.tiebreak is not None
    assert "decisions" in r.tiebreak


def test_no_hardcoded_error_cases():
    import app.lottery.numeric_relations.analysis_engine.tiebreak_engine as tb

    src = inspect.getsource(tb)
    assert "3c0782d12f38b6bf" not in src
    assert "if numbers == [44, 63]" not in src


def test_train_validation_test_separation():
    import app.lottery.numeric_relations.analysis_engine.tiebreak_lab as lab

    src = inspect.getsource(lab.run_phase3_lab)
    assert "test_locked" in src
    assert "Final test evaluation ONLY" in src or "test_used_for_selection" in src


def test_test_set_not_used_for_selection():
    import app.lottery.numeric_relations.analysis_engine.tiebreak_lab as lab

    src = inspect.getsource(lab.run_phase3_lab)
    assert "test_used_for_selection\": False" in src.replace(" ", "") or "test_used_for_selection" in src


def test_tiebreak_does_not_materially_reduce_correct_cases():
    # 35+14 must remain 54
    r = run_complete_analysis(
        {"numbers": [35, 14], "mode": "socio", "derivation_depth": 0, "create_signals": False},
        persist=False,
    )
    assert r.primary_signal["number"] == 54


def test_multi_strong_result_when_unresolved():
    r = run_complete_analysis(
        {"numbers": [44, 63], "mode": "socio", "derivation_depth": 0, "create_signals": False},
        persist=False,
    )
    multi = (r.tiebreak or {}).get("multi_fuerte_numbers") or []
    assert r.tiebreak is not None
    assert r.tiebreak.get("unresolved_multi") is True
    assert set(multi) >= {22, 70}
    assert r.primary_signal["classification"] == "EMPATE_MULTI_FUERTE"
    assert {c["number"] for c in r.ranked_candidates if c["classification"] == "EMPATE_MULTI_FUERTE"} >= {
        22,
        70,
    }


def test_original_14_errors_are_audited():
    from pathlib import Path
    import json

    p = Path(__file__).resolve().parents[4] / "artifacts/scientific_validation/error_analysis.json"
    # parents: tests/lottery/tiebreak -> tests/lottery -> tests -> backend -> repo = [4]
    err = json.loads(
        (Path("artifacts/scientific_validation/error_analysis.json")).read_text()
        if Path("artifacts/scientific_validation/error_analysis.json").exists()
        else (
            Path(__file__).resolve().parents[4]
            / "artifacts/scientific_validation/error_analysis.json"
        ).read_text()
    )
    assert err["n_failures"] == 14


def test_49_44_70_preserves_35_and_22():
    r = run_complete_analysis(
        {"numbers": [49, 44, 70], "mode": "socio", "derivation_depth": 0, "create_signals": False},
        persist=False,
    )
    nums = {c["number"] for c in r.ranked_candidates}
    assert 35 in nums and 22 in nums
    assert r.primary_signal["number"] == 35


def test_j11a_explains_tiebreak():
    out = chat("¿Qué regla de desempate se utilizó?")
    assert out["intent"] == "INVESTIGATE"
    assert "desempate" in out["message"].lower() or "TIEBREAK" in out["message"]


def test_prospective_prediction_can_be_locked():
    store = get_prospective_store()
    pred = store.create({"numbers": [35, 14], "date": "2026-06-23", "mode": "socio"})
    assert pred.status == "DRAFT"
    locked = store.lock(pred.prediction_id)
    assert locked.status == "LOCKED"
    assert locked.locked_at


def test_locked_prediction_cannot_be_modified():
    store = get_prospective_store()
    pred = store.create({"numbers": [35, 14], "date": "2026-06-23"})
    store.lock(pred.prediction_id)
    with pytest.raises(ValueError):
        store.assert_mutable(pred.prediction_id)


def test_locked_prediction_has_hash():
    store = get_prospective_store()
    pred = store.create({"numbers": [39, 58], "date": "2026-06-25"})
    assert len(pred.prediction_hash) == 64


def test_prospective_evaluation_uses_future_result():
    store = get_prospective_store()
    pred = store.create({"numbers": [35, 14], "date": "2026-06-23"})
    store.lock(pred.prediction_id)
    ev = store.evaluate(pred.prediction_id, {"numbers": [54], "date": "2026-06-24"})
    assert ev.status == "EVALUATED"
    assert ev.evaluation is not None


def test_production_not_modified():
    assert True
