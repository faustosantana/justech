"""ANALYST_REASONING_40 + FactualGuard + EvidencePackage — offline suite."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from app.lottery.ai.active_investigation.hermes_decision_engine import HermesDecision
from app.lottery.ai.analyst_reasoning.evidence_package import EvidencePackage, EvidencePackageBuilder
from app.lottery.ai.analyst_reasoning.factual_guard import FactualGuard
from app.lottery.ai.analyst_reasoning.reasoning_layer import AnalystReasoningLayer
from app.lottery.ai.analyst_reasoning.reasoning_modes import (
    ReasoningModeSelector,
    should_invoke_reasoning,
)
from app.lottery.ai.official_lottery_scope import OFFICIAL_LOTTERY_SCOPE

BANK = (
    Path(__file__).resolve().parents[2]
    / "evidence"
    / "lottery-analyst-certification-200"
    / "ANALYST_REASONING_40.json"
)
if not BANK.exists():
    BANK = Path("/tmp/ANALYST_REASONING_40.json")


def _load_cases() -> list[dict]:
    data = json.loads(BANK.read_text(encoding="utf-8"))
    return list(data["cases"])


def _fake_decision(case: dict) -> HermesDecision:
    d = HermesDecision(
        turn_type="attribute_of_last_event" if case.get("attr") else "new_investigation",
        requested_attribute=case.get("attr"),
        inherited_relation=case.get("relation"),
        inherited_subjects=["35", "14"],
        requires_research=not bool(case.get("attr")),
    )
    return d


@pytest.mark.parametrize("case", _load_cases(), ids=lambda c: c["id"])
def test_reasoning_40_mode_selection(case: dict):
    d = _fake_decision(case)
    mode = ReasoningModeSelector.select(
        case["message"],
        hermes_decision=d,
        relation=case.get("relation"),
        has_evidence=not case.get("empty_evidence"),
    )
    assert mode == case["expect_mode"], (case["id"], mode, case["expect_mode"])
    assert should_invoke_reasoning(mode) is bool(case["invoke"])


def test_evidence_package_official_scope():
    pkg = EvidencePackageBuilder.build(
        question="¿Cuántas veces coincidieron el 35 y el 14?",
        factual_answer="Sí. 35 y 14 coincidieron 120 veces.",
        structured={
            "data": {
                "relation": "same_day",
                "numbers": ["35", "14"],
                "total": 120,
                "items": [
                    {
                        "date": "2026-07-20",
                        "appearances": [
                            {"number": "14", "lottery": "Quiniela Loteka", "position": 2},
                            {"number": "35", "lottery": "Loteria Nacional", "position": 1},
                        ],
                    }
                ],
                "last": {
                    "date": "2026-07-20",
                    "appearances": [
                        {"number": "14", "lottery": "Quiniela Loteka"},
                        {"number": "35", "lottery": "Loteria Nacional"},
                    ],
                },
            }
        },
    )
    assert pkg.counts.get("total") == 120
    assert set(pkg.subjects) >= {"35", "14"}
    assert pkg.official_lotteries == list(OFFICIAL_LOTTERY_SCOPE)
    assert any("same-day" in x.lower() or "misma fecha" in x.lower() for x in pkg.known_facts + pkg.limitations)
    assert len(pkg.evidence_hash()) == 16


def test_factual_guard_rejects_count_and_external():
    pkg = EvidencePackage(
        question="q",
        subjects=["35", "14"],
        dates=["2026-07-20"],
        counts={"total": 120},
        official_lotteries=list(OFFICIAL_LOTTERY_SCOPE),
        factual_answer="120",
    )
    bad = (
        "Hubo 200 ocasiones en Haiti Bolet el 2019-01-01. "
        "Seguro que va a salir el 54 mañana."
    )
    g = FactualGuard.validate(bad, pkg)
    assert g.passed is False
    assert g.rejection_reason


def test_factual_guard_rejects_invented_date_count():
    pkg = EvidencePackage(
        question="q",
        subjects=["35", "14"],
        dates=["2026-07-20"],
        counts={"total": 120},
        official_lotteries=list(OFFICIAL_LOTTERY_SCOPE),
        factual_answer="120",
        relation="same_day",
    )
    invented = (
        "Los números 35 y 14 coincidieron el mismo día en 20 fechas distintas "
        "dentro de las 7 loterías. Registros consultados: 120."
    )
    g = FactualGuard.validate(invented, pkg)
    assert g.passed is False
    assert "count_mismatch" in (g.rejection_reason or "")



def test_factual_guard_accepts_good_analysis():
    pkg = EvidencePackage(
        question="q",
        subjects=["35", "14"],
        dates=["2026-07-20"],
        counts={"total": 120},
        official_lotteries=list(OFFICIAL_LOTTERY_SCOPE),
        factual_answer="120",
        known_facts=["Total verificado: 120."],
    )
    good = (
        "Dentro de las 7 loterías habilitadas, el 35 y el 14 han aparecido "
        "en la misma fecha 120 ocasiones.\n\n"
        "Eso no significa necesariamente que salieran en la misma lotería; "
        "la coincidencia se cuenta por día calendario. "
        "La cifra es histórica. Conviene revisar loterías y fechas recientes "
        "como 2026-07-20."
    )
    g = FactualGuard.validate(good, pkg)
    assert g.passed is True


@pytest.mark.asyncio
async def test_reasoning_layer_guard_fallback():
    pkg = EvidencePackage(
        question="explica",
        subjects=["35", "14"],
        dates=["2026-07-20"],
        counts={"total": 120},
        factual_answer="SAFE FACTUAL 120",
    )

    async def evil_caller(messages, max_tokens):
        return (
            "Hubo 999 ocasiones en Anguila. Seguro que va a salir el 54.",
            "DeepSeek-V3.2",
            {"input_tokens": 10, "output_tokens": 20},
        )

    layer = AnalystReasoningLayer(huawei_caller=evil_caller)
    rr = await layer.run(
        package=pkg,
        mode="explain_evidence",
        factual_fallback="SAFE FACTUAL 120",
    )
    assert rr.fallback_used is True
    assert rr.guard_passed is False
    assert "120" in rr.text
    assert rr.rejection_reason
    # Rich same_day fallback when relation+total present
    pkg2 = EvidencePackage(
        question="explica",
        subjects=["35", "14"],
        relation="same_day",
        counts={"total": 120},
        factual_answer="SAFE FACTUAL 120",
    )
    rr2 = await layer.run(
        package=pkg2, mode="interpret_pattern", factual_fallback="SAFE FACTUAL 120"
    )
    assert rr2.fallback_used is True
    assert "misma lotería" in rr2.text.lower() or "misma loteria" in rr2.text.lower()
    assert "120" in rr2.text



@pytest.mark.asyncio
async def test_reasoning_layer_skip_mode():
    pkg = EvidencePackage(question="fecha", factual_answer="2026-07-20")
    layer = AnalystReasoningLayer(huawei_caller=AsyncMock())
    rr = await layer.run(package=pkg, mode="skip", factual_fallback="2026-07-20")
    assert rr.used_reasoning is False
    assert rr.provider_used == "local_template"
    assert rr.text == "2026-07-20"


def test_hermes_attaches_reasoning_mode():
    from app.lottery.ai.active_investigation.hermes_decision_engine import HermesDecisionEngine
    from app.lottery.ai.conversation_state import ConversationState

    st = ConversationState(active_relation="same_day", active_numbers=["35", "14"])
    d = HermesDecisionEngine.decide(
        "Explícame la coincidencia del 35 y el 14",
        state=st,
        investigation=None,
        resolution={"relation": "same_day", "numbers": ["35", "14"]},
    )
    assert d.reasoning_mode == "explain_evidence"
