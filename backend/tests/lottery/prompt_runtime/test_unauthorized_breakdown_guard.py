"""Guard + dimension contract: unauthorized breakdowns vs total-only evidence."""

from __future__ import annotations

from app.lottery.ai.analyst_reasoning.evidence_package import EvidencePackage
from app.lottery.ai.analyst_reasoning.factual_guard import FactualGuard
from app.lottery.ai.analyst_reasoning.response_dimensions import (
    enrich_response_contract,
    sanitize_factual_answer_for_contract,
)


def _pkg(**kwargs) -> EvidencePackage:
    base = dict(
        question="compara",
        subjects=["61", "14"],
        relation="same_day",
        counts={"total": 152},
        dates=["2026-07-22"],
        factual_answer="total 152",
        known_facts=["Único conteo canónico: 152"],
        forbidden_claims=[],
    )
    base.update(kwargs)
    return EvidencePackage(**base)


def test_total_only_correct_answer_passes():
    text = (
        "Ambos números coincidieron el mismo día en 152 ocasiones. "
        "La evidencia entregada no contiene un desglose que permita determinar "
        "cuál aparece más por posición."
    )
    r = FactualGuard.validate(text, _pkg())
    assert r.passed, r.violations
    assert r.unauthorized_breakdown is False


def test_invented_position_breakdown_fails():
    text = (
        "El número 14 aparece más, con 94 casos en primera posición frente a "
        "20 casos en que ambos coincidieron en primera posición. "
        "En total coincidieron 152 veces."
    )
    r = FactualGuard.validate(text, _pkg())
    assert not r.passed
    assert r.unauthorized_breakdown is True
    assert any("unauthorized_breakdown" in v for v in r.violations)


def test_authorized_position_breakdown_passes():
    pkg = _pkg(
        counts={"total": 152, "first_related": 94, "both_first": 20, "other_only": 58}
    )
    text = (
        "Hubo 152 coincidencias same-day. En el desglose autorizado, "
        "94 casos tienen al menos uno en primera posición y en 20 ambos "
        "estuvieron en primera."
    )
    r = FactualGuard.validate(text, pkg)
    assert r.passed, r.violations


def test_compare_without_subtotals_passes():
    text = (
        "El histórico disponible registra 152 coincidencias. "
        "No es posible determinar quién aparece más: solo hay total conjunto."
    )
    r = FactualGuard.validate(text, _pkg())
    assert r.passed, r.violations


def test_zero_padded_subjects_still_guarded():
    pkg = _pkg(subjects=["07", "38"], counts={"total": 10})
    text = "El 07 y el 38 coincidieron 10 veces. No hay desglose adicional."
    r = FactualGuard.validate(text, pkg)
    assert r.passed, r.violations


def test_sanitize_strips_template_position_blocks():
    raw = (
        "Sí. 61 y 14 coincidieron el mismo día en 152 ocasión(es).\n\n"
        "En 1ra posición:\n"
        "- 94 caso(s) con al menos uno de los números en 1ra (ambos en 1ra: 20).\n\n"
        "En otras posiciones:\n"
        "- 58 caso(s).\n\n"
        "La coincidencia más reciente fue el 2026-07-22."
    )
    clean = sanitize_factual_answer_for_contract(raw, {"total": 152})
    assert "94" not in clean
    assert "ambos en 1ra" not in clean
    assert "58 caso" not in clean
    assert "152" in clean
    assert "2026-07-22" in clean


def test_contract_total_only_dimensions():
    c = enrich_response_contract({}, counts={"total": 152}, relation="same_day")
    assert c["allowed_dimensions"] == ["total"]
    assert c["allowed_counts"] == [152]
    assert "position_breakdown" in c["forbidden_inferences"]
    assert "subject_subtotals" in c["forbidden_inferences"]


def test_llm_payload_sanitizes_factual_answer():
    pkg = _pkg(
        factual_answer=(
            "Sí. 61 y 14 coincidieron el mismo día en 152 ocasión(es).\n\n"
            "En 1ra posición:\n- 94 caso(s) (ambos en 1ra: 20).\n\n"
            "En otras posiciones:\n- 58 caso(s)."
        )
    )
    payload = pkg.to_llm_payload()
    assert "94" not in (payload.get("factual_answer") or "")
    assert payload["response_contract"]["allowed_counts"] == [152]
    assert payload["response_contract"]["allowed_dimensions"] == ["total"]
