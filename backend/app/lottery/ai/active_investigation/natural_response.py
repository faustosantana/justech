"""NaturalResponseGenerator — analyst-style answers without internal jargon."""

from __future__ import annotations

import re
from typing import Any

from app.lottery.ai.active_investigation.hermes_decision_engine import HermesDecision
from app.lottery.ai.active_investigation.session import ActiveInvestigationSession
from app.lottery.ai.turn_policy import position_label_es

_INTERNAL_JARGON = re.compile(
    r"\b(metric|research|subject|planner|tool_trace|same_day|active_filters|"
    r"follow_up_kind|ResearchPlan|QuestionClassifier|HermesDecision)\b",
    re.I,
)


class NaturalResponseGenerator:
    """Four layers: direct · evidence · brief explanation · useful next step."""

    @classmethod
    def answer_attribute_from_evidence(
        cls,
        decision: HermesDecision,
        investigation: ActiveInvestigationSession,
    ) -> str | None:
        attr = decision.requested_attribute
        ev = investigation.evidence or {}
        last = investigation.last_event or ev.get("last") or {}
        subjects = decision.inherited_subjects or investigation.subjects or []
        label = " y ".join(str(s) for s in subjects[:2]) if subjects else "esos números"

        if attr == "lotteries":
            return cls._lotteries_answer(label, last, ev)
        if attr in {"positions", "order"}:
            return cls._positions_answer(label, last)
        if attr == "date":
            date_s = str(last.get("date") or last.get("draw_date") or investigation.date_anchor or "")[:10]
            if not date_s:
                return None
            return cls.compose(
                direct=f"Esa coincidencia entre {label} fue el {date_s}.",
                evidence=cls._event_evidence_lines(last),
                explanation=(
                    "Me refiero al evento de coincidencia que acabamos de revisar "
                    "(misma fecha en el histórico)."
                ),
                next_step="Puedo detallar loterías, posiciones o las coincidencias anteriores.",
            )
        if attr == "count":
            total = ev.get("total")
            if total is None:
                return None
            return cls.compose(
                direct=f"{label} coincidieron el mismo día en {total} ocasión(es) en el histórico disponible.",
                evidence=cls._event_evidence_lines(last) if last else "",
                explanation="El conteo corresponde a fechas donde ambos números aparecieron el mismo día.",
                next_step="Puedo listar las más recientes o filtrar por lotería o posición.",
            )
        if attr in {"explain", "details"}:
            if not last and not investigation.summary:
                return None
            date_s = str(last.get("date") or investigation.date_anchor or "—")[:10]
            return cls.compose(
                direct=f"Sobre la coincidencia de {label} del {date_s}:",
                evidence=cls._event_evidence_lines(last) or (investigation.summary or ""),
                explanation=(
                    "Los considero una coincidencia porque ambos aparecieron en sorteos "
                    "de la misma fecha, aunque no necesariamente en la misma lotería."
                ),
                next_step="Puedo mostrarte las tres coincidencias anteriores o filtrar el alcance.",
            )
        return None

    @classmethod
    def _lotteries_answer(cls, label: str, last: dict[str, Any], ev: dict[str, Any]) -> str | None:
        appearances = list(last.get("appearances") or last.get("entries") or [])
        lots: list[str] = []
        lines: list[str] = []
        for e in appearances:
            if not isinstance(e, dict):
                continue
            lot = str(e.get("lottery") or last.get("lottery") or "").strip()
            num = e.get("number")
            pos = position_label_es(e.get("position_label") or e.get("position"))
            if lot and lot not in lots:
                lots.append(lot)
            if lot and num is not None:
                lines.append(f"- el {num} en {lot} ({pos})")
        if not lots:
            lots = [str(x) for x in (ev.get("lotteries") or []) if x]
            if last.get("lottery"):
                lots = list(dict.fromkeys([str(last["lottery"]), *lots]))
        if not lots:
            return None
        date_s = str(last.get("date") or last.get("draw_date") or "")[:10]
        direct = (
            f"En la coincidencia de {label}"
            + (f" del {date_s}" if date_s else "")
            + f", participaron: {', '.join(lots)}."
        )
        return cls.compose(
            direct=direct,
            evidence="\n".join(lines) if lines else f"Loterías: {', '.join(lots)}.",
            explanation=(
                "Cada número puede salir en una lotería distinta el mismo día; "
                "eso sigue contando como coincidencia por fecha."
            ),
            next_step="¿Quieres las posiciones de ese día o las tres coincidencias anteriores?",
        )

    @classmethod
    def _positions_answer(cls, label: str, last: dict[str, Any]) -> str | None:
        appearances = list(last.get("appearances") or last.get("entries") or [])
        if not appearances:
            return None
        date_s = str(last.get("date") or last.get("draw_date") or "")[:10]
        lines = []
        for e in appearances[:6]:
            if not isinstance(e, dict):
                continue
            num = e.get("number")
            lot = e.get("lottery") or last.get("lottery") or "lotería"
            pos = position_label_es(e.get("position_label") or e.get("position"))
            lines.append(f"- el {num} en {lot}, {pos}")
        direct = (
            f"En la coincidencia de {label}"
            + (f" del {date_s}" if date_s else "")
            + ", las posiciones fueron:"
        )
        return cls.compose(
            direct=direct,
            evidence="\n".join(lines),
            explanation="Las posiciones corresponden a ese evento concreto, no al filtro general de búsqueda.",
            next_step="Puedo filtrar solo primera posición o listar coincidencias anteriores.",
        )

    @classmethod
    def _event_evidence_lines(cls, last: dict[str, Any]) -> str:
        if not last:
            return ""
        appearances = list(last.get("appearances") or last.get("entries") or [])
        date_s = str(last.get("date") or last.get("draw_date") or "")[:10]
        lines = []
        if date_s:
            lines.append(f"Fecha: {date_s}.")
        for e in appearances[:6]:
            if not isinstance(e, dict):
                continue
            num = e.get("number")
            lot = e.get("lottery") or last.get("lottery") or "lotería"
            pos = position_label_es(e.get("position_label") or e.get("position"))
            lines.append(f"- el {num} en {lot}, {pos}.")
        if not appearances and last.get("lottery"):
            lines.append(f"Lotería registrada: {last.get('lottery')}.")
        return "\n".join(lines)

    @classmethod
    def compose(
        cls,
        *,
        direct: str,
        evidence: str = "",
        explanation: str = "",
        next_step: str = "",
    ) -> str:
        parts = [direct.strip()]
        if evidence and evidence.strip():
            parts.append(evidence.strip())
        if explanation and explanation.strip():
            parts.append(explanation.strip())
        if next_step and next_step.strip():
            parts.append(next_step.strip())
        text = "\n\n".join(p for p in parts if p)
        return cls.sanitize(text)

    @classmethod
    def enhance_factual_template(
        cls,
        template: str,
        *,
        investigation: ActiveInvestigationSession | None = None,
        next_step: str | None = None,
    ) -> str:
        """Keep factual body; add a short next-step when missing."""
        text = cls.sanitize(template or "")
        if not text:
            return text
        if next_step and next_step not in text:
            # Avoid stacking next-steps if template already offers one
            if not re.search(r"\b(puedo|si quieres|¿quieres)\b", text, re.I):
                text = text.rstrip() + "\n\n" + next_step
        if investigation and investigation.relation == "same_day" and investigation.subjects:
            # Ensure compound subjects remain visible when template is thin
            pass
        return text

    @classmethod
    def partial_failure(
        cls,
        *,
        confirmed: str,
        missing: str,
        offer_retry: bool = True,
    ) -> str:
        bits = [confirmed.strip()]
        if missing:
            bits.append(missing.strip())
        if offer_retry:
            bits.append("¿Quieres que lo intente de nuevo?")
        return cls.sanitize("\n\n".join(b for b in bits if b))

    @classmethod
    def sanitize(cls, text: str) -> str:
        out = _INTERNAL_JARGON.sub("", text or "")
        out = re.sub(r"[ \t]{2,}", " ", out)
        out = re.sub(r"\n{3,}", "\n\n", out)
        return out.strip()
