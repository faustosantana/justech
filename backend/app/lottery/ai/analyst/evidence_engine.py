"""Evidence Engine + Confidence Score (Fase B).

Every conclusion must cite cases, criterion, period, tools, and evidence level.
Confidence is qualitative (Alta/Media/Baja) — never invented percentages.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from app.lottery.ai.turn_policy import position_label_es, purpose_label_es


ConfidenceLevel = Literal["Alta", "Media", "Baja"]


@dataclass
class EvidencePackage:
    case_count: int | None = None
    criterion: str = ""
    period: str | None = None
    tools_used: list[str] = field(default_factory=list)
    evidence_level: ConfidenceLevel = "Baja"
    findings: list[str] = field(default_factory=list)
    comparisons: list[str] = field(default_factory=list)
    timeline: list[str] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)
    related_suggestions: list[str] = field(default_factory=list)
    raw_summaries: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "case_count": self.case_count,
            "criterion": self.criterion,
            "period": self.period,
            "tools_used": self.tools_used,
            "evidence_level": self.evidence_level,
            "confidence": self.evidence_level,
            "findings": self.findings,
            "comparisons": self.comparisons,
            "timeline": self.timeline,
            "limitations": self.limitations,
            "related_suggestions": self.related_suggestions,
        }


class EvidenceEngine:
    """Assemble evidence from tool results without inventing statistics."""

    @classmethod
    def assemble(
        cls,
        *,
        kind: str,
        tool_trace: list[dict[str, Any]],
        evidence_bundle: list[dict[str, Any]],
        context: dict[str, Any] | None = None,
        case_criteria: list[dict[str, str]] | None = None,
    ) -> EvidencePackage:
        ctx = context or {}
        tools = [
            str(t.get("tool"))
            for t in tool_trace
            if t.get("status") == "success" and t.get("tool")
        ]
        case_count: int | None = None
        findings: list[str] = []
        comparisons: list[str] = []
        timeline: list[str] = []
        raw: list[dict[str, Any]] = []
        has_occurrence_date = False

        for item in evidence_bundle:
            summary = item.get("summary") if isinstance(item.get("summary"), dict) else {}
            purpose = str(item.get("purpose") or "")
            purpose_label = purpose_label_es(purpose) if purpose else purpose_label_es(str(item.get("tool") or ""))
            raw.append({"purpose": item.get("purpose"), "tool": item.get("tool"), "keys": list(summary.keys())[:12]})
            cnt = cls._extract_count(summary)
            if cnt is not None:
                case_count = max(case_count or 0, cnt)
                findings.append(
                    f"{purpose_label}: {cnt} casos/registros consultados."
                )
            if summary.get("last_occurrence_date"):
                has_occurrence_date = True
                timeline.append(
                    f"Última ancla: {summary.get('last_occurrence_date')} "
                    f"({summary.get('lottery') or 'lotería consultada'})."
                )
                # Consistency: a real date cannot coexist with an unknown/zero count display
                if case_count is None:
                    case_count = max(1, int(summary.get("count") or summary.get("total") or 1))
                elif case_count == 0 and summary.get("found") is not False:
                    case_count = max(1, int(summary.get("count") or summary.get("total") or 1))
            if summary.get("number") is not None:
                findings.append(f"Número consultado: {summary.get('number')}.")
            if summary.get("primary") is not None:
                findings.append(
                    f"Motor (solo lectura): candidato principal reportado {summary.get('primary')}."
                )
            if purpose.startswith("compare_"):
                comparisons.append(
                    f"Comparación ejecutada: {purpose_label}."
                )

            semantics = str(summary.get("semantics") or "")
            # last_n timeline: date — lottery — position (never invent)
            if semantics == "last_n_occurrences":
                items = summary.get("items") or summary.get("occurrences") or []
                limit = int(summary.get("limit") or 10)
                if isinstance(items, list):
                    for row in items[: max(1, min(limit, 20))]:
                        if not isinstance(row, dict):
                            continue
                        d = row.get("date") or row.get("draw_date") or "—"
                        lot = row.get("lottery") or "—"
                        pos = row.get("position")
                        pos_s = (
                            position_label_es(pos)
                            if pos not in (None, "", "all")
                            else "posición no indicada"
                        )
                        timeline.append(f"{d} — {lot} — {pos_s}")

            # same-day coincidence: total + last date with human labels
            if semantics == "same_day_coincidence":
                total = summary.get("total")
                if total is None:
                    total = summary.get("count")
                last = summary.get("last_occurrence_date") or summary.get("last_date")
                label = purpose_label_es("same_day_coincidence")
                if total is not None:
                    findings.append(f"{label}: {total} coincidencia(s) encontrada(s).")
                    try:
                        case_count = max(case_count or 0, int(total))
                    except (TypeError, ValueError):
                        pass
                if last:
                    findings.append(f"Última {label}: {last}.")
                    has_occurrence_date = True

        # Never report 0 records when a last-occurrence date exists
        if has_occurrence_date and (case_count is None or case_count == 0):
            case_count = 1
        # Unknown count stays None (formatter omits the line) instead of fake 0
        if case_count == 0 and not has_occurrence_date and not findings:
            case_count = None

        criterion_bits = [c.get("criterion") for c in (case_criteria or []) if c.get("criterion")]
        criterion = "; ".join(criterion_bits) if criterion_bits else cls._default_criterion(kind)

        period = None
        if ctx.get("year_filter"):
            period = str(ctx["year_filter"])
        elif ctx.get("years"):
            period = "–".join(str(y) for y in ctx["years"][:4])
        elif ctx.get("active_date"):
            period = f"anclado a {ctx['active_date']}"

        consistency = sum(1 for t in tool_trace if t.get("status") == "success")
        failures = sum(1 for t in tool_trace if t.get("status") not in {"success", None})
        confidence = cls.score_confidence(
            case_count=case_count or 0,
            successful_tools=consistency,
            failed_tools=failures,
            findings=len(findings),
        )

        pkg = EvidencePackage(
            case_count=case_count,
            criterion=criterion,
            period=period,
            tools_used=list(dict.fromkeys(tools)),
            evidence_level=confidence,
            findings=findings[:12],
            comparisons=comparisons[:8],
            timeline=timeline[:12],
            limitations=[
                "El histórico describe eventos anteriores y no garantiza resultados futuros.",
                "El Research Engine no modifica Tabla 1/2, ranking ni Prompt Maestro.",
                "No se inventan porcentajes ni predicciones.",
            ],
            related_suggestions=cls._suggestions(kind, ctx),
            raw_summaries=raw[-12:],
        )
        return pkg

    @staticmethod
    def _extract_count(summary: dict[str, Any]) -> int | None:
        for key in (
            "count",
            "exact_cases",
            "evaluable_cases",
            "total",
            "occurrences",
            "matches",
            "case_count",
        ):
            val = summary.get(key)
            if isinstance(val, int):
                return val
            if isinstance(val, list):
                return len(val)
        return None

    @staticmethod
    def _default_criterion(kind: str) -> str:
        mapping = {
            "what_usually_happens_after": "apariciones del número + ventanas D+1/D+3/D+7",
            "compare_numbers": "ocurrencias, posiciones, frecuencias y ventanas temporales por número",
            "compare_lotteries": "perfiles de lotería, coincidencias y frecuencias",
            "case_search": "condiciones históricas equivalentes / similares / parciales",
            "temporal_windows": "ventanas calendario D+N vía herramientas históricas",
            "which_lottery_confirms_first": "comparación cross-lotería de confirmaciones",
            "which_confirms_most": "combinaciones de confirmadores y patrones históricos",
        }
        return mapping.get(kind, f"investigación '{kind}' sobre herramientas históricas autorizadas")

    @classmethod
    def score_confidence(
        cls,
        *,
        case_count: int,
        successful_tools: int,
        failed_tools: int,
        findings: int,
    ) -> ConfidenceLevel:
        """Qualitative confidence — no percentages."""
        if case_count >= 20 and successful_tools >= 4 and failed_tools == 0 and findings >= 3:
            return "Alta"
        if case_count >= 5 and successful_tools >= 2 and findings >= 1:
            return "Media"
        if successful_tools >= 3 and findings >= 2:
            return "Media"
        return "Baja"

    @staticmethod
    def _suggestions(kind: str, ctx: dict[str, Any]) -> list[str]:
        nums = ctx.get("numbers") or []
        suggestions = [
            "¿Quieres filtrar solo por una lotería?",
            "¿Restrinjo a primera posición?",
            "¿Comparo con otro número del contexto?",
        ]
        if nums:
            suggestions.insert(0, f"¿Analizo D+15/D+30 para el {nums[0]}?")
        if kind.startswith("compare"):
            suggestions.append("¿Muestro solo casos equivalentes de la comparación?")
        if kind in {"case_search", "equivalents_only"}:
            suggestions.append("¿Amplío a casos parcialmente similares?")
        return suggestions[:5]
