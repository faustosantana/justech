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
        if attr in {
            "tabla1",
            "tabla2",
            "companions",
            "neighbors",
            "table_code",
            "strongest",
            "compare_neighbors",
            "compare_companions",
        }:
            return cls.answer_table_attribute(attr, subjects)
        return None

    @classmethod
    def answer_table_attribute(
        cls,
        attr: str,
        subjects: list[Any],
    ) -> str | None:
        """Short catalog answers for Tabla 1 / Tabla 2 (read-only; no Motor)."""
        from app.lottery.numeric_relations.catalog import build_catalog

        nums: list[int] = []
        for s in subjects or []:
            try:
                n = int(str(s).strip())
            except (TypeError, ValueError):
                continue
            if 1 <= n <= 100:
                nums.append(n)
        if not nums:
            return (
                "Necesito un número activo en la investigación "
                "(por ejemplo: «Analiza el 57») para consultar tablas."
            )
        cat = build_catalog()
        primary = nums[0]

        def _t1(n: int) -> tuple[int | None, list[int]]:
            code = cat.table1_number_to_code.get(n)
            if code is None:
                return None, []
            comps = [x for x in cat.get_table1_companions(code) if x != n]
            return code, comps

        def _t2(n: int) -> tuple[int | None, list[int]]:
            try:
                code = cat.get_table2_code_for_number(n)
            except KeyError:
                return None, []
            return code, cat.get_table2_neighbors(n, exclude_self=True)

        if attr == "table_code":
            c1, _ = _t1(primary)
            c2, _ = _t2(primary)
            bits = [f"Para el {primary}:"]
            if c1 is not None:
                bits.append(f"- Tabla 1 → código {c1:02d}.")
            if c2 is not None:
                bits.append(f"- Tabla 2 → código {c2:02d}.")
            return cls.compose(
                direct="\n".join(bits),
                next_step="¿Quieres sus compañeros (Tabla 1) o sus vecinos (Tabla 2)?",
            )

        if attr in {"tabla1", "companions"}:
            if len(nums) >= 2 and attr == "companions":
                lines = []
                for n in nums[:4]:
                    code, comps = _t1(n)
                    if code is None:
                        lines.append(f"- {n}: sin código Tabla 1.")
                    else:
                        lines.append(
                            f"- {n} (código {code:02d}): "
                            + (", ".join(str(x) for x in comps) if comps else "sin compañeros")
                        )
                return cls.compose(
                    direct="Comparación de compañeros (Tabla 1):",
                    evidence="\n".join(lines),
                    next_step="¿Quieres comparar también sus vecinos de Tabla 2?",
                )
            code, comps = _t1(primary)
            if code is None:
                return f"No encontré el {primary} en Tabla 1."
            comps_s = ", ".join(str(x) for x in comps) if comps else "ninguno adicional"
            return cls.compose(
                direct=(
                    f"En Tabla 1, el {primary} pertenece al código {code:02d}."
                ),
                evidence=f"Compañeros: {comps_s}.",
                next_step="¿Quieres también sus vecinos de Tabla 2?",
            )

        if attr in {"tabla2", "neighbors"}:
            if len(nums) >= 2 and attr == "neighbors":
                lines = []
                for n in nums[:4]:
                    code, neigh = _t2(n)
                    if code is None:
                        lines.append(f"- {n}: sin código Tabla 2.")
                    else:
                        lines.append(
                            f"- {n} (código {code:02d}): "
                            + (", ".join(str(x) for x in neigh) if neigh else "sin vecinos")
                        )
                return cls.compose(
                    direct="Comparación de vecinos (Tabla 2):",
                    evidence="\n".join(lines),
                    next_step="¿Quieres comparar también sus compañeros de Tabla 1?",
                )
            code, neigh = _t2(primary)
            if code is None:
                return f"No encontré el {primary} en Tabla 2."
            neigh_s = ", ".join(str(x) for x in neigh) if neigh else "ninguno adicional"
            return cls.compose(
                direct=(
                    f"En Tabla 2, el {primary} pertenece al código {code:02d}."
                ),
                evidence=f"Vecinos: {neigh_s}.",
                next_step="¿Quieres también sus compañeros de Tabla 1?",
            )

        if attr == "compare_companions" or (attr == "companions" and len(nums) >= 2):
            lines = []
            for n in nums[:4]:
                code, comps = _t1(n)
                if code is None:
                    lines.append(f"- {n}: sin código Tabla 1.")
                else:
                    lines.append(
                        f"- {n} (código {code:02d}): "
                        + (", ".join(str(x) for x in comps) if comps else "sin compañeros")
                    )
            return cls.compose(
                direct="Comparación de compañeros (Tabla 1):",
                evidence="\n".join(lines),
                next_step="¿Quieres comparar también sus vecinos de Tabla 2?",
            )

        if attr == "compare_neighbors" or (attr == "neighbors" and len(nums) >= 2):
            lines = []
            for n in nums[:4]:
                code, neigh = _t2(n)
                if code is None:
                    lines.append(f"- {n}: sin código Tabla 2.")
                else:
                    lines.append(
                        f"- {n} (código {code:02d}): "
                        + (", ".join(str(x) for x in neigh) if neigh else "sin vecinos")
                    )
            return cls.compose(
                direct="Comparación de vecinos (Tabla 2):",
                evidence="\n".join(lines),
                next_step="¿Quieres comparar también sus compañeros de Tabla 1?",
            )

        if attr == "strongest":
            # Descriptive only — no prediction. Prefer subject with larger companion+neighbor set.
            scored: list[tuple[int, int, int, int]] = []
            for n in nums[:4]:
                _, comps = _t1(n)
                _, neigh = _t2(n)
                scored.append((n, len(comps), len(neigh), len(comps) + len(neigh)))
            scored.sort(key=lambda t: (-t[3], -t[1], t[0]))
            top = scored[0]
            lines = [
                f"- {n}: {c} compañeros (T1), {v} vecinos (T2)"
                for n, c, v, _ in scored
            ]
            return cls.compose(
                direct=(
                    f"Por estructura de tablas (sin predicción), el {top[0]} "
                    f"tiene el grupo relacional más amplio entre los comparados."
                ),
                evidence="\n".join(lines),
                explanation=(
                    "Esto describe el tamaño de sus grupos en Tabla 1/2; "
                    "no implica mayor probabilidad de salida."
                ),
                next_step="Puedo detallar compañeros o vecinos de cualquiera de ellos.",
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
