"""Breakdown20 — authorized position/lottery dimensions (offline guard suite)."""

from __future__ import annotations

from app.lottery.ai.analyst_reasoning.evidence_package import EvidencePackage
from app.lottery.ai.analyst_reasoning.factual_guard import FactualGuard


def _pkg_auth(**counts):
    return EvidencePackage(
        question="desglose",
        subjects=["22", "38"],
        relation="same_day",
        counts=counts,
        dates=["2026-01-01"],
        factual_answer="ok",
    )


def test_breakdown20_authorized_position_variants():
    cases = []
    for i in range(20):
        total = 100 + i
        first = 40 + (i % 10)
        both = 5 + (i % 5)
        other = total - first
        pkg = _pkg_auth(
            total=total,
            first_related=first,
            both_first=both,
            other_only=other,
        )
        text = (
            f"Hay {total} coincidencias same-day. Desglose autorizado: "
            f"{first} con al menos uno en primera posición; "
            f"{both} con ambos en primera; {other} solo en otras posiciones."
        )
        r = FactualGuard.validate(text, pkg)
        cases.append(r.passed)
        assert r.passed, (i, r.violations)
    assert sum(cases) == 20
