"""Unit tests — AllowedSubjectSet + contextual subject guard."""

from __future__ import annotations

from app.lottery.ai.analyst_reasoning.allowed_subjects import AllowedSubjectSet, normalize_ball
from app.lottery.ai.analyst_reasoning.evidence_package import EvidencePackage
from app.lottery.ai.analyst_reasoning.factual_guard import FactualGuard
from app.lottery.ai.prompt_runtime.compiler import PromptStudioCompiler
from app.lottery.ai.prompt_runtime.seed_reasoning_studio_v7_rc3 import (
    INITIAL_REASONING_STUDIO_BLOCKS_RC3,
)
from app.lottery.ai.prompt_runtime.validator import PromptStudioValidator


def test_normalize_ball_forms():
    assert normalize_ball("07") == "7"
    assert normalize_ball(7) == "7"
    assert normalize_ball("7") == "7"
    assert AllowedSubjectSet.from_values(["07"]).contains("7")
    assert AllowedSubjectSet.from_values(["07"]).contains("07")


def test_dates_counts_positions_not_extra_subjects():
    pkg = EvidencePackage(
        subjects=["07"],
        dates=["2026-07-23"],
        counts={"total": 3},
        positions=["1", "2"],
        factual_answer="ok",
        response_contract={"allowed_subjects": ["07"], "allow_related_subjects": False},
    )
    text = (
        "La última vez del número 07 fue el 2026-07-23. "
        "Apareció 3 veces durante 2026. Estaba en posición 2. "
        "Ver Tabla 2 y el top 10 no cambia el subject."
    )
    g = FactualGuard.validate(text, pkg)
    assert g.passed, g.violations


def test_studio_invented_related_stats_rejected_as_extra_subjects():
    pkg = EvidencePackage(subjects=["50", "90"], counts={"total": 134}, factual_answer="134")
    # Counts that are NOT total and look like invented related balls in subject phrasing
    bad = (
        "Los números **50** y **90** coincidieron 134 veces. "
        "También destacan el número 51, el 60 y el 83 como compañeros frecuentes."
    )
    g = FactualGuard.validate(bad, pkg)
    assert not g.passed
    assert g.rejection_reason and "extra_subjects" in g.rejection_reason


def test_count_83_alone_not_subject_when_phrased_as_count():
    pkg = EvidencePackage(subjects=["50", "90"], counts={"total": 134}, factual_answer="134")
    # 83 as count mismatches total → count_mismatch (ok), but not extra_subjects
    text = (
        "Los números 50 y 90 coincidieron 134 veces. "
        "En 83 ocasiones al menos uno salió en primera posición."
    )
    g = FactualGuard.validate(text, pkg)
    # May fail count_mismatch (83!=134) which is correct; must NOT invent extra_subjects
    assert not any(v.startswith("extra_subjects") for v in g.violations), g.violations


def test_pair_and_other_two_quantity():
    pkg = EvidencePackage(subjects=["22", "38"], counts={"total": 5}, factual_answer="5")
    text = "El 22 y el 38 coincidieron 5 veces. Las otras dos apariciones fueron en Leidsa."
    g = FactualGuard.validate(text, pkg)
    assert not any(v.startswith("extra_subjects") for v in g.violations), g.violations


def test_sample_size_confusion_vs_muestra_de():
    dates = [f"2026-01-{i:02d}" for i in range(1, 41)]
    pkg = EvidencePackage(subjects=["35", "77"], counts={"total": 111}, dates=dates, factual_answer="111")
    bad = (
        "Sí, 35 y 77 coincidieron 111 veces. "
        "La evidencia muestra 40 fechas distintas donde ambos aparecieron."
    )
    assert not FactualGuard.validate(bad, pkg).passed
    ok = (
        "Sí, 35 y 77 coincidieron 111 veces. "
        "Limitación: la muestra de 40 fechas es truncada y no es el total."
    )
    assert FactualGuard.validate(ok, pkg).passed

    v = PromptStudioValidator.validate(INITIAL_REASONING_STUDIO_BLOCKS_RC3)
    assert v["ok"] is True, v["errors"]
    assert v["tokens_estimated"] <= 8000
    assert v["tokens_estimated"] >= 400
    assert "allowed_subjects" in v["compiled"]["body"]
    c = PromptStudioCompiler.compile(INITIAL_REASONING_STUDIO_BLOCKS_RC3)
    assert c["compiled_prompt_hash"] == v["compiled_prompt_hash"]


def test_payload_includes_response_contract():
    pkg = EvidencePackage(subjects=["07", "7"], counts={"total": 1}, factual_answer="x")
    payload = pkg.to_llm_payload()
    assert "response_contract" in payload
    assert "07" in payload["response_contract"]["allowed_subjects"] or "7" in payload[
        "response_contract"
    ]["allowed_subjects"]
    assert payload["response_contract"]["allow_related_subjects"] is False
