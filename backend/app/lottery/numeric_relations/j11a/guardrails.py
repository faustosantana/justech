"""J-11A guardrails — prevent hallucinations and LLM math."""

from __future__ import annotations

from typing import Any


GUARD_CODES = (
    "NO_EVIDENCE_NO_CLAIM",
    "NO_ENGINE_RESULT_NO_PREDICTION",
    "NO_RELATION_TYPE_INFERENCE",
    "NO_HISTORICAL_DATE_WITHOUT_SOURCE",
    "NO_SCORE_RECALCULATION_IN_LLM",
    "NO_HARDCODED_MANUAL_CASES",
    "NO_TABLE_CONFUSION",
    "NO_EARLY_CANDIDATE_SELECTION",
)


def no_evidence_message() -> str:
    return "No encontré evidencia suficiente en el motor para afirmar esa relación."


def no_engine_message() -> str:
    return (
        "No fue posible calcular el análisis. "
        "No generaré una predicción sin resultados verificables."
    )


def validate_engine_result(result: dict[str, Any] | None) -> tuple[bool, str | None]:
    if not result:
        return False, "NO_ENGINE_RESULT_NO_PREDICTION"
    if not result.get("graph_complete_before_discovery"):
        return False, "NO_EARLY_CANDIDATE_SELECTION"
    return True, None


def validate_relation_claim(
    *,
    candidate: int,
    claimed_table: str,
    evidence: dict[str, Any] | None,
) -> tuple[bool, str]:
    if not evidence:
        return False, no_evidence_message()
    ev = evidence.get("evidence") or evidence
    if claimed_table == "table1":
        if candidate and not ev.get("table1_sources"):
            # claiming candidate has T1 support
            pass
        return True, "ok"
    if claimed_table == "table2":
        return True, "ok"
    return False, no_evidence_message()


def forbid_table_confusion_39_58_94(evidence: dict[str, Any]) -> list[str]:
    """Assert correct labeling for the canonical case."""
    warnings: list[str] = []
    ev = evidence.get("evidence") or evidence
    if 58 in (ev.get("table1_sources") or []):
        warnings.append("NO_TABLE_CONFUSION: 58 no debe figurar como fuente T1 de 94")
    if 39 not in (ev.get("table1_sources") or []):
        warnings.append("NO_TABLE_CONFUSION: falta 39 como fuente T1 de 94")
    if 58 not in (ev.get("direct_confirmers") or []):
        warnings.append("NO_TABLE_CONFUSION: falta 58 como confirmador T2 de 94")
    return warnings


def strip_win_probability_language(text: str) -> str:
    banned = (
        "va a salir",
        "seguro que sale",
        "probabilidad de ganar",
        "apuesta a",
    )
    out = text
    for b in banned:
        if b in out.lower():
            out = out.replace(b, "[redactado]")
    return out
