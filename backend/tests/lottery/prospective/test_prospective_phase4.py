"""Phase 4 — prospective pilot persistence, lock, integrity, evaluation."""

from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path

import pytest

from app.lottery.numeric_relations.analysis_engine.prospective.freeze import (
    FROZEN_ENGINE_VERSION,
    FROZEN_TABLE_VERSION,
    OPERATIONAL_RANKING_PROFILE,
    assert_operational_freeze,
    freeze_manifest,
)
from app.lottery.numeric_relations.analysis_engine.prospective.hashing import (
    build_lock_payload,
    hash_payload,
)
from app.lottery.numeric_relations.analysis_engine.prospective.scheduler import run_daily
from app.lottery.numeric_relations.analysis_engine.prospective_validation import (
    get_prospective_store,
    reset_prospective_store,
)
from app.lottery.numeric_relations.j11a import chat
from app.lottery.numeric_relations.j11a.memory_engine import reset_sessions
from app.lottery.numeric_relations.analysis_engine.signal_tracker import reset_signal_store


def _future(days: int = 1) -> str:
    return (date.today() + timedelta(days=days)).isoformat()


@pytest.fixture(autouse=True)
def _clean():
    reset_signal_store()
    reset_sessions()
    reset_prospective_store()
    yield
    reset_signal_store()
    reset_sessions()
    reset_prospective_store()


def test_prospective_prediction_persists_in_database():
    store = get_prospective_store()
    pred = store.create({"numbers": [35, 14], "date": date.today().isoformat()})
    row = store.db.get_prediction(pred.prediction_id)
    assert row is not None
    assert Path(store.db.path).exists()


def test_draft_prediction_can_be_modified():
    store = get_prospective_store()
    pred = store.create({"numbers": [35, 14], "date": date.today().isoformat()})
    updated = store.update_draft(pred.prediction_id, {"notes": "uat note"})
    assert updated.input_data.get("notes") == "uat note"


def test_locked_prediction_is_immutable():
    store = get_prospective_store()
    pred = store.create({"numbers": [35, 14], "date": date.today().isoformat()})
    store.lock(pred.prediction_id)
    with pytest.raises(ValueError):
        store.assert_mutable(pred.prediction_id)
    with pytest.raises(ValueError):
        store.update_draft(pred.prediction_id, {"notes": "nope"})


def test_locked_prediction_hash_is_reproducible():
    store = get_prospective_store()
    pred = store.create({"numbers": [39, 58], "date": date.today().isoformat()})
    locked = store.lock(pred.prediction_id)
    assert hash_payload(locked.canonical_payload) == locked.prediction_hash


def test_hash_changes_when_payload_changes():
    payload = build_lock_payload(
        inputs={"numbers": [1]},
        target_date="2026-01-01",
        lotteries=[],
        positions=["first"],
        candidates=[{"number": 1, "classification": "X"}],
        ranking=[{"number": 1}],
        scores=[{"number": 1, "score": 1}],
        classifications=[{"number": 1, "classification": "X"}],
        tiebreak_rule="R",
        engine_version="E",
        table1_version="T",
        table2_version="T",
        locked_at="t1",
    )
    h1 = hash_payload(payload)
    payload["locked_at"] = "t2"
    assert hash_payload(payload) != h1


def test_integrity_check_detects_tampering():
    store = get_prospective_store()
    pred = store.create({"numbers": [35, 14], "date": date.today().isoformat()})
    locked = store.lock(pred.prediction_id)
    row = store.db.get_prediction(locked.prediction_id)
    tampered = dict(row["canonical_payload"])
    tampered["engine_version"] = "tampered"
    store.db._conn.execute(
        "UPDATE prospective_runs SET canonical_payload=? WHERE prediction_id=?",
        (json.dumps(tampered), locked.prediction_id),
    )
    store.db._conn.commit()
    store._reload_cache()
    assert store.check_integrity(locked.prediction_id)["ok"] is False


def test_prediction_preserves_engine_version():
    pred = get_prospective_store().create({"numbers": [35, 14], "date": date.today().isoformat()})
    assert pred.engine_version == FROZEN_ENGINE_VERSION


def test_prediction_preserves_table_versions():
    pred = get_prospective_store().create({"numbers": [35, 14], "date": date.today().isoformat()})
    assert pred.table1_version == FROZEN_TABLE_VERSION
    assert pred.table2_version == FROZEN_TABLE_VERSION


def test_multi_strong_tie_is_preserved():
    store = get_prospective_store()
    pred = store.create({"numbers": [44, 63], "date": "2023-11-10"})
    locked = store.lock(pred.prediction_id)
    assert set(locked.multi_strong_candidates or []) >= {22, 70}
    assert (locked.primary_signal or {}).get("classification") == "EMPATE_MULTI_FUERTE"


def test_operational_profile_is_profile_socio():
    pred = get_prospective_store().create({"numbers": [35, 14], "mode": "socio"})
    assert pred.ranking_profile == OPERATIONAL_RANKING_PROFILE


def test_shadow_profiles_do_not_change_operational_signal():
    store = get_prospective_store()
    pred = store.create(
        {"numbers": [35, 14], "date": date.today().isoformat(), "include_shadow": True}
    )
    op = (pred.primary_signal or {}).get("number")
    assert op == 54
    assert "baseline_no_tiebreak" in (pred.shadow_profiles or {})
    locked = store.lock(pred.prediction_id)
    assert (locked.primary_signal or {}).get("number") == op


def test_future_result_evaluates_locked_prediction():
    store = get_prospective_store()
    today = date.today().isoformat()
    pred = store.create({"numbers": [35, 14], "date": today, "target_date": today})
    store.lock(pred.prediction_id)
    ev = store.evaluate(pred.prediction_id, {"numbers": [54], "date": _future(1)})
    assert ev.status == "EVALUATED"


def test_result_before_lock_is_rejected():
    store = get_prospective_store()
    pred = store.create({"numbers": [35, 14], "date": date.today().isoformat()})
    store.lock(pred.prediction_id)
    with pytest.raises(ValueError, match="result_before_lock"):
        store.evaluate(pred.prediction_id, {"numbers": [54], "date": "2020-01-01"})


def test_exact_primary_hit_classification():
    store = get_prospective_store()
    today = date.today().isoformat()
    pred = store.create({"numbers": [35, 14], "date": today, "target_date": today})
    store.lock(pred.prediction_id)
    ev = store.evaluate(pred.prediction_id, {"numbers": [54], "date": _future(1)})
    assert ev.evaluation["hit_class"] == "EXACT_PRIMARY_HIT"


def test_exact_multi_strong_hit_classification():
    store = get_prospective_store()
    today = date.today().isoformat()
    pred = store.create({"numbers": [44, 63], "date": today, "target_date": today})
    store.lock(pred.prediction_id)
    ev = store.evaluate(pred.prediction_id, {"numbers": [70], "date": _future(1)})
    assert ev.evaluation["hit_class"] == "EXACT_MULTI_STRONG_HIT"


def test_top2_hit_classification():
    store = get_prospective_store()
    today = date.today().isoformat()
    pred = store.create({"numbers": [49, 44, 70], "date": today, "target_date": today})
    store.lock(pred.prediction_id)
    top = [r["number"] for r in pred.ranking[:2]]
    drawn = [top[1]] if len(top) > 1 and top[1] != top[0] else [22]
    ev = store.evaluate(pred.prediction_id, {"numbers": drawn, "date": _future(1)})
    assert ev.evaluation["hit_class"] in {
        "EXACT_PRIMARY_HIT",
        "EXACT_TOP2_HIT",
        "EXACT_MULTI_STRONG_HIT",
        "EXACT_TOP3_HIT",
    }


def test_t1_family_hit_is_not_exact_hit():
    from app.lottery.numeric_relations.analysis_engine.prospective.evaluation import classify_hit

    cls = classify_hit(
        drawn=[59], primary=35, multi=[], top2=[35, 22], top3=[35, 22], t1_family=[59]
    )
    assert cls == "T1_FAMILY_HIT"


def test_t2_neighbor_hit_is_not_exact_hit():
    from app.lottery.numeric_relations.analysis_engine.prospective.evaluation import classify_hit

    cls = classify_hit(
        drawn=[75], primary=29, multi=[], top2=[29, 41], top3=[29, 41], t2_neighbors=[75]
    )
    assert cls == "T2_NEIGHBOR_HIT"


def test_d1_d7_are_recorded_separately():
    store = get_prospective_store()
    today = date.today().isoformat()
    pred = store.create({"numbers": [35, 14], "date": today, "target_date": today})
    store.lock(pred.prediction_id)
    ev = store.evaluate(pred.prediction_id, {"numbers": [54], "date": _future(1)})
    assert "D+1" in ev.evaluation["d_plus"] and "D+7" in ev.evaluation["d_plus"]
    assert ev.evaluation["d_plus"]["D+1"]


def test_case_closes_only_under_configured_rule():
    store = get_prospective_store()
    today = date.today().isoformat()
    pred = store.create({"numbers": [35, 14], "date": today, "target_date": today})
    store.lock(pred.prediction_id)
    from app.lottery.numeric_relations.analysis_engine.prospective.evaluation import (
        evaluate_locked_prediction,
    )

    fake = evaluate_locked_prediction(pred.to_dict(), {"numbers": [999], "date": _future(1)})
    assert fake["case_closed"] is False
    exact = store.evaluate(pred.prediction_id, {"numbers": [54], "date": _future(1)})
    assert exact.evaluation["case_closed"] is True


def test_scheduler_skips_incomplete_inputs():
    out = run_daily(numbers=None, analysis_date=_future(10), auto_lock=False)
    assert out["ok"] is False
    assert out["reason"] == "INPUT_INCOMPLETE"


def test_scheduler_does_not_duplicate_daily_prediction():
    day = _future(11)
    a = run_daily(numbers=[35, 14], analysis_date=day, auto_lock=False)
    b = run_daily(numbers=[35, 14], analysis_date=day, auto_lock=False)
    assert a["ok"] is True
    assert b["reason"] == "DUPLICATE_DAILY_PREDICTION"


def test_pilot_can_be_paused():
    store = get_prospective_store()
    pilot = store.create_pilot({"pilot_name": "UAT"})
    store.set_pilot_status(pilot["id"], "PAUSED")
    out = run_daily(
        numbers=[35, 14], analysis_date=_future(12), auto_lock=False, pilot_id=pilot["id"]
    )
    assert out["reason"] == "PILOT_PAUSED"


def test_engine_freeze_prevents_silent_change():
    with pytest.raises(ValueError, match="ENGINE_FREEZE"):
        assert_operational_freeze(
            {"engine_version": "other", "table1_version": FROZEN_TABLE_VERSION}
        )
    assert freeze_manifest()["silent_changes_forbidden"] is True


def test_j11a_cannot_modify_locked_prediction():
    store = get_prospective_store()
    pred = store.create({"numbers": [35, 14], "date": date.today().isoformat()})
    store.lock(pred.prediction_id)
    out = chat("¿Puedo modificar la predicción bloqueada?")
    assert out["intent"] == "INVESTIGATE"
    assert "no puede modificar" in out["message"].lower() or "locked" in out["message"].lower()


def test_j11a_reads_prospective_metrics():
    store = get_prospective_store()
    pred = store.create({"numbers": [35, 14], "date": date.today().isoformat()})
    store.lock(pred.prediction_id)
    out = chat("¿Cuántos exactos llevamos en D+1?")
    assert out["intent"] == "INVESTIGATE"


def test_audit_log_records_lock():
    store = get_prospective_store()
    pred = store.create({"numbers": [35, 14], "date": date.today().isoformat()})
    store.lock(pred.prediction_id)
    assert "LOCKED" in [a["action"] for a in store.audit_log(pred.prediction_id)]


def test_audit_log_records_evaluation():
    store = get_prospective_store()
    today = date.today().isoformat()
    pred = store.create({"numbers": [35, 14], "date": today, "target_date": today})
    store.lock(pred.prediction_id)
    store.evaluate(pred.prediction_id, {"numbers": [54], "date": _future(1)})
    assert "EVALUATED" in [a["action"] for a in store.audit_log(pred.prediction_id)]


def test_production_configuration_not_modified():
    assert freeze_manifest()["production_modified"] is False
    mig = Path(__file__).resolve().parents[3] / "alembic/versions/062_lottery_prospective_pilot.py"
    assert "Do NOT apply this migration against Production" in mig.read_text(encoding="utf-8")
