"""Tests — Phase 2 scientific validation (no Production, no formula changes)."""

from __future__ import annotations

from app.lottery.numeric_relations.analysis_engine.scientific_validation.dataset import (
    MANUAL_BENCHMARK_FINGERPRINTS,
    build_blind_dataset,
    is_manual_benchmark,
)
from app.lottery.numeric_relations.analysis_engine.scientific_validation.explainability import (
    explain_analysis_decisions,
)
from app.lottery.numeric_relations.analysis_engine.scientific_validation.historical_validator import (
    evaluate_scenario,
)
from app.lottery.numeric_relations.analysis_engine.scientific_validation.investigator import (
    investigator_answer,
)
from app.lottery.numeric_relations.analysis_engine.scientific_validation.results_store import (
    set_phase2_results,
)
from app.lottery.numeric_relations.analysis_engine.scientific_validation.rule_inventory import (
    build_rule_inventory,
)
from app.lottery.numeric_relations.j11a import chat
from app.lottery.numeric_relations.j11a.memory_engine import reset_sessions
from app.lottery.numeric_relations.analysis_engine.signal_tracker import reset_signal_store


def test_blind_dataset_excludes_manual_cases():
    ds = build_blind_dataset()
    assert ds["total_scenarios"] > 100
    assert set(ds["counts"]) == {"train", "validation", "test"}
    for split, rows in ds["splits"].items():
        for r in rows[:200]:
            assert not is_manual_benchmark(r["observed_numbers"])
    assert frozenset({35, 14}) in MANUAL_BENCHMARK_FINGERPRINTS


def test_methodology_match_on_random_activation_sample():
    ds = build_blind_dataset()
    sc = ds["splits"]["validation"][0]
    row = evaluate_scenario(sc, variant="perfil_socio")
    assert "methodology_match" in row
    assert row["graph_complete_before_discovery"] is True
    assert "exact_D+1" in row


def test_explainability_answers_why_first_second():
    exp = explain_analysis_decisions([35, 14], mode="socio")
    assert exp["decisions"]["first"]["number"] == 54
    assert "evidence_had" in exp["decisions"]["first"]
    assert "evidence_lacked" in exp["decisions"]["first"]


def test_rule_inventory_has_statuses():
    inv = build_rule_inventory()
    statuses = {r["status"] for r in inv["rules"]}
    assert "confirmada_por_evidencia" in statuses
    assert inv["pending_to_discover"]


def test_j11a_investigator_uses_phase2_store():
    reset_sessions()
    reset_signal_store()
    set_phase2_results(
        {
            "error_analysis": {
                "n_failures": 3,
                "failure_rate": 0.1,
                "repetitive_patterns": {"HIST_FUERTE_IN_ALTERNATIVES": 2},
                "sample_cases": [],
            },
            "calibration": {
                "best_methodology_reproduction": "perfil_socio",
                "recommendation": "perfil_socio gana",
                "ranking": [],
            },
            "benchmark": {"best_blind_variant": "perfil_socio", "blind_benchmark_table": []},
            "patterns": {"min_support": 5, "frequent_origin_fuerte": [], "stable_observed_combos": [], "hypothesis_only": []},
            "rule_inventory": {"rules": []},
            "explainability_samples": {
                "35_14": {
                    "decisions": {
                        "first": {
                            "number": 54,
                            "why": "test",
                            "evidence_had": {"table1_sources": [35], "table2_confirmers": [14]},
                        }
                    }
                }
            },
            "production_modified": False,
        }
    )
    out = chat("¿Qué regla falla más?")
    assert out["intent"] == "INVESTIGATE"
    assert "Fallos" in out["message"] or "fallos" in out["message"].lower()


def test_include_table2_false_ablation_runs():
    from app.lottery.numeric_relations.analysis_engine import run_complete_analysis

    r = run_complete_analysis(
        {"numbers": [35, 14], "mode": "socio", "derivation_depth": 0, "create_signals": False},
        persist=False,
        include_table2=False,
    )
    # Without T2, should not be FUERTE_PRINCIPAL with cross confirmation
    primary = r.primary_signal
    assert primary is None or primary.get("classification") != "FUERTE_PRINCIPAL" or not (
        primary.get("table2_confirmers")
    )
