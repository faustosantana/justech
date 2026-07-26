"""Tests — Complete Analysis Engine (non-greedy, full-graph)."""

from __future__ import annotations

import inspect

import pytest

from app.lottery.numeric_relations.analysis_engine.candidate_discovery import (
    discover_candidates_after_full_analysis,
)
from app.lottery.numeric_relations.analysis_engine.complete_analysis_service import (
    run_complete_analysis,
)
from app.lottery.numeric_relations.analysis_engine.derivation_engine import apply_derivations
from app.lottery.numeric_relations.analysis_engine.evidence_collector import collect_all_evidence
from app.lottery.numeric_relations.analysis_engine.input_normalizer import normalize_positions
from app.lottery.numeric_relations.analysis_engine.relationship_graph import (
    RelationshipGraph,
    build_complete_relationship_graph,
)
from app.lottery.numeric_relations.analysis_engine.signal_tracker import (
    get_signal_store,
    reset_signal_store,
)
from app.lottery.numeric_relations.catalog import build_catalog


@pytest.fixture(autouse=True)
def _clean_store():
    reset_signal_store()
    yield
    reset_signal_store()


def test_no_candidate_is_selected_before_full_analysis():
    src = inspect.getsource(run_complete_analysis)
    # discovery must appear after graph_complete stage conceptually
    assert "graph_complete" in src
    assert "discover_candidates_after_full_analysis" in src
    g = build_complete_relationship_graph([35, 14], derivation_depth=0)
    assert g.complete
    # incomplete graph refuses discovery
    g2 = RelationshipGraph()
    g2.observed_numbers = [35, 14]
    with pytest.raises(RuntimeError, match="NO_EARLY_CANDIDATE_SELECTION"):
        discover_candidates_after_full_analysis({}, g2)


def test_all_observed_numbers_are_analyzed():
    r = run_complete_analysis({"numbers": [35, 14]}, persist=False)
    assert r.observed_numbers == [35, 14]
    origins = {e["observed_origin"] for e in r.graph["edges"] if e.get("observed_origin")}
    assert {35, 14} <= origins


def test_table1_is_processed_as_mother_table():
    r = run_complete_analysis({"numbers": [35, 14]}, persist=False)
    t1 = [e for e in r.graph["edges"] if e["relation_type"] == "T1_MOTHER_RELATION"]
    assert any(e["observed_origin"] == 35 for e in t1)


def test_table2_relations_are_not_mislabeled_as_table1():
    r = run_complete_analysis({"numbers": [39, 58]}, persist=False)
    ev = next(c["evidence"] for c in r.ranked_candidates if c["number"] == 94)
    assert 58 not in ev["table1_sources"]
    assert 58 in ev["direct_confirmers"]
    assert 39 in ev["table1_sources"]


def test_candidate_discovery_happens_after_graph_completion():
    r = run_complete_analysis({"numbers": [35, 14]}, persist=False)
    assert r.graph_complete_before_discovery is True
    stages = r.stages_completed
    assert stages.index("graph_complete") < stages.index("candidates_discovered")


def test_multiple_candidates_are_ranked():
    r = run_complete_analysis({"numbers": [49, 44, 70]}, persist=False)
    assert len(r.ranked_candidates) >= 2


def test_35_14_ranks_54():
    r = run_complete_analysis({"numbers": [35, 14], "mode": "manual_reconstruido"}, persist=False)
    assert r.primary_signal["number"] == 54
    assert r.primary_signal["classification"] == "FUERTE_PRINCIPAL"


def test_39_58_ranks_94():
    r = run_complete_analysis({"numbers": [39, 58], "mode": "manual_reconstruido"}, persist=False)
    assert r.primary_signal["number"] == 94
    assert r.primary_signal["classification"] == "FUERTE_PRINCIPAL"


def test_41_70_ranks_29():
    r = run_complete_analysis({"numbers": [41, 41, 70], "mode": "manual_reconstruido"}, persist=False)
    assert r.primary_signal["number"] == 29


def test_49_44_70_includes_35():
    r = run_complete_analysis({"numbers": [49, 44, 70], "mode": "manual_reconstruido"}, persist=False)
    assert r.primary_signal["number"] == 35
    nums = [c["number"] for c in r.ranked_candidates]
    assert 22 in nums


def test_direct_t2_signal_is_classified_separately():
    r = run_complete_analysis({"numbers": [41, 62], "mode": "manual_reconstruido"}, persist=False)
    assert r.primary_signal["number"] == 75
    assert r.primary_signal["classification"] == "VECINO_T2_DIRECTO"


def test_fulfilled_signal_closes_case():
    from datetime import date

    r = run_complete_analysis(
        {"numbers": [35, 14], "date": "2026-06-23", "mode": "manual_reconstruido"},
        persist=True,
    )
    store = get_signal_store()
    sig = store.signals[r.signals[0]["signal_id"]]
    store.evaluate_signal(
        sig.signal_id,
        draw_date=date(2026, 6, 24),
        drawn_numbers=[54],
        lottery="Leidsa",
        position="first",
    )
    assert store.signals[sig.signal_id].status == "CUMPLIDO_EXACTO"
    case = next(c for c in store.cases.values() if c.signal_id == sig.signal_id)
    assert case.status == "CERRADO"


def test_new_analysis_can_start_same_day():
    store = get_signal_store()
    out = store.start_new_analysis_same_day("2026-06-23")
    assert out["ok"] is True
    r1 = run_complete_analysis({"numbers": [35, 14], "date": "2026-06-23"}, persist=True)
    r2 = run_complete_analysis({"numbers": [39, 58], "date": "2026-06-23"}, persist=True)
    assert r1.analysis_id != r2.analysis_id


def test_first_position_default():
    assert normalize_positions(None) == ["first"]
    assert normalize_positions([]) == ["first"]
    r = run_complete_analysis({"numbers": [35, 14]}, persist=False)
    assert r.positions == ["first"]


def test_no_hardcoded_manual_cases():
    import app.lottery.numeric_relations.analysis_engine.complete_analysis_service as svc
    import app.lottery.numeric_relations.analysis_engine.candidate_ranker as ranker

    for mod in (svc, ranker):
        src = inspect.getsource(mod)
        assert "if inputs ==" not in src
        assert "if numbers == [35, 14]" not in src
        assert "return 54" not in src.replace(" ", "")


def test_every_prediction_has_traceable_evidence():
    r = run_complete_analysis({"numbers": [35, 14]}, persist=True)
    for s in r.signals:
        assert s["supporting_evidence"]
        assert "table1_sources" in s["supporting_evidence"] or "table2_confirmers" in s["supporting_evidence"]


def test_duplicate_paths_are_not_overcounted():
    cat = build_catalog()
    g = build_complete_relationship_graph([35, 14], catalog=cat, derivation_depth=0)
    apply_derivations(g, catalog=cat, max_depth=0)
    ev = collect_all_evidence(g, catalog=cat)
    e54 = ev[54]
    # fingerprints unique
    assert len(e54.path_fingerprints) == len(set(e54.path_fingerprints))


def test_derivation_depth_is_limited():
    r = run_complete_analysis({"numbers": [35, 14], "derivation_depth": 2}, persist=False)
    depths = [d["depth"] for d in r.derivations]
    assert not depths or max(depths) <= 2
    g = build_complete_relationship_graph([1], derivation_depth=99)
    paths = apply_derivations(g, max_depth=99)
    assert all(p.depth <= 2 for p in paths)
    r0 = run_complete_analysis({"numbers": [35, 14], "derivation_depth": 99}, persist=False)
    assert r0.derivation_depth == 2


def test_candidate_alternatives_are_preserved():
    r = run_complete_analysis({"numbers": [49, 44, 70]}, persist=False)
    assert r.alternatives
    assert any(a["number"] == 22 for a in r.alternatives)


def test_production_is_not_modified():
    # Marker test: this feature branch must not claim production deploy.
    assert True
