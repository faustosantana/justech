"""Evidence Package — verified facts Huawei may read (and nothing else)."""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.lottery.ai.official_lottery_scope import (
    OFFICIAL_LOTTERY_SCOPE,
    official_lottery_names,
    scope_label_es,
)


class EvidencePackage(BaseModel):
    """Structured, verified evidence for Analyst Reasoning."""

    model_config = {"extra": "ignore"}

    question: str = ""
    resolved_intent: str | None = None
    subjects: list[str] = Field(default_factory=list)
    relation: str | None = None
    scope: str = "official_seven"
    official_lotteries: list[str] = Field(default_factory=lambda: list(OFFICIAL_LOTTERY_SCOPE))
    dates: list[str] = Field(default_factory=list)
    positions: list[str] = Field(default_factory=list)
    counts: dict[str, Any] = Field(default_factory=dict)
    occurrences: list[dict[str, Any]] = Field(default_factory=list)
    comparison_data: dict[str, Any] = Field(default_factory=dict)
    deterministic_relations: list[str] = Field(default_factory=list)
    source_rows: list[dict[str, Any]] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    known_facts: list[str] = Field(default_factory=list)
    forbidden_claims: list[str] = Field(default_factory=list)
    factual_answer: str = ""
    package_version: str = "2.1.0"
    # Optional derived contract for Studio / guard (legacy may ignore)
    response_contract: dict[str, Any] = Field(default_factory=dict)

    def evidence_hash(self) -> str:
        payload = self.model_dump(mode="json")
        raw = json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str)
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]

    def safe_interpretive_text(self, *, base_factual: str | None = None) -> str:
        """Deterministic rich fallback when Huawei is skipped/rejected."""
        total = self.counts.get("total")
        subjects = [str(s).lstrip("0") or "0" for s in self.subjects if str(s).strip()]
        pair = " y ".join(subjects[:2]) if len(subjects) >= 2 else (subjects[0] if subjects else "los números")
        factual = (base_factual or self.factual_answer or "").strip()
        if self.relation == "same_day" and total is not None:
            try:
                t = int(total)
            except (TypeError, ValueError):
                t = total
            body = (
                f"Dentro de las 7 loterías habilitadas, el {pair} han aparecido "
                f"en la misma fecha {t} veces.\n\n"
                "Eso no significa necesariamente que salieran en la misma lotería: "
                "la coincidencia se cuenta cuando ambos aparecen en sorteos del mismo "
                "día calendario dentro del alcance oficial.\n\n"
                "La cifra es histórica y descriptiva. Para entender mejor la relación, "
                "conviene revisar en cuáles loterías se repite más y cuáles fueron las "
                "coincidencias más recientes."
            )
            return body
        return factual or "No hay evidencia suficiente para ampliar la interpretación."

    def to_llm_payload(self) -> dict[str, Any]:
        """Compact payload for the model — no internals beyond verified fields."""
        from app.lottery.ai.analyst_reasoning.allowed_subjects import AllowedSubjectSet
        from app.lottery.ai.analyst_reasoning.response_dimensions import (
            enrich_response_contract,
            sanitize_factual_answer_for_contract,
        )

        allowed = AllowedSubjectSet.from_evidence_package(self)
        contract = dict(self.response_contract or {})
        if not contract.get("allowed_subjects"):
            contract["allowed_subjects"] = allowed.to_contract_list()
        contract.setdefault("allow_related_subjects", False)
        contract.setdefault("allowed_lotteries", list(self.official_lotteries))
        # Send only a few date anchors to the LLM — long date lists cause "N fechas" hallucinations.
        date_anchors = list(self.dates[:5])
        sample_n = len(date_anchors)
        contract["dates_are_sample"] = True
        contract["sample_date_count"] = sample_n
        contract["allowed_dates"] = date_anchors
        contract["sample_note"] = (
            "dates/occurrences/source_rows are a truncated SAMPLE; "
            "never report sample length as the total — use counts.total / canonical_count only."
        )
        if self.resolved_intent and "requested_operation" not in contract:
            contract["requested_operation"] = self.resolved_intent
        contract = enrich_response_contract(
            contract,
            counts=self.counts if isinstance(self.counts, dict) else {},
            resolved_intent=self.resolved_intent,
            relation=self.relation,
        )
        factual_for_llm = sanitize_factual_answer_for_contract(
            self.factual_answer,
            self.counts if isinstance(self.counts, dict) else {},
        )
        forbidden = list(self.forbidden_claims) + [
            "Usar el tamaño de dates/occurrences como si fuera counts.total.",
            "Decir '40 fechas' u otro tamaño de muestra como conteo de coincidencias.",
            "Usar cifras de factual_answer que no estén en response_contract.allowed_counts.",
            "Inventar desgloses por posición/lotería/fecha/sujeto no autorizados en allowed_dimensions.",
        ]
        return {
            "question": self.question,
            "resolved_intent": self.resolved_intent,
            "subjects": self.subjects,
            "relation": self.relation,
            "scope": self.scope,
            "official_lotteries": self.official_lotteries,
            "scope_label": scope_label_es(),
            "dates": date_anchors,
            "positions": self.positions[:24],
            "counts": self.counts,
            "occurrences": self.occurrences[:8],
            "comparison_data": self.comparison_data,
            "deterministic_relations": self.deterministic_relations,
            "source_rows": self.source_rows[:8],
            "limitations": self.limitations,
            "known_facts": self.known_facts,
            "forbidden_claims": forbidden,
            "factual_answer": factual_for_llm,
            "response_contract": contract,
        }


class EvidencePackageBuilder:
    """Build EvidencePackage from tool/structured payloads already verified by SQL."""

    @classmethod
    def build(
        cls,
        *,
        question: str,
        factual_answer: str,
        structured: dict[str, Any] | None = None,
        state: Any = None,
        hermes_decision: Any = None,
        research_meta: dict[str, Any] | None = None,
    ) -> EvidencePackage:
        structured = structured or {}
        data = structured.get("data") if isinstance(structured.get("data"), dict) else structured
        if not isinstance(data, dict):
            data = {}

        subjects = cls._subjects(question, state, hermes_decision, data)
        relation = (
            (getattr(hermes_decision, "inherited_relation", None) if hermes_decision else None)
            or getattr(state, "active_relation", None)
            or data.get("relation")
            or (research_meta or {}).get("relation")
        )
        dates = cls._dates(data)
        positions = cls._positions(data)
        counts = cls._counts(data, structured)
        occurrences = cls._occurrences(data)
        comparison = cls._comparison(data, structured)
        known = cls._known_facts(subjects, relation, counts, dates, data)
        limitations = cls._limitations(relation, counts, data)
        forbidden = [
            "Inventar fechas no listadas en dates/occurrences.",
            "Inventar o alterar conteos (counts).",
            "Inventar desgloses (p. ej. ambos en primera posición N veces) no presentes en counts.",
            "Afirmar predicciones garantizadas del próximo sorteo.",
            "Incluir loterías fuera de official_lotteries.",
            "Cambiar los subjects de la pregunta.",
            "Afirmar que coincidencia same-day implica misma lotería.",
            "Citar Haiti Bolet, King Lottery, Anguila u otras loterías externas.",
        ]
        if relation == "same_day":
            known.append(
                "Coincidencia same-day = ambos números aparecen en sorteos del mismo "
                f"día calendario dentro de {scope_label_es()}; no exige la misma lotería."
            )
        if counts.get("total") is not None:
            known.append(
                f"Único conteo canónico verificable en este paquete: counts.total={counts.get('total')}. "
                "No hay desglose por posición/primera posición en el paquete; no lo inventes."
            )

        intent = None
        if hermes_decision is not None:
            intent = getattr(hermes_decision, "turn_type", None)
        intent = intent or structured.get("type") or data.get("semantics")

        from app.lottery.ai.analyst_reasoning.allowed_subjects import AllowedSubjectSet

        allowed = AllowedSubjectSet.from_values(subjects)
        total_count = counts.get("total") if isinstance(counts, dict) else None
        from app.lottery.ai.analyst_reasoning.response_dimensions import enrich_response_contract

        response_contract = enrich_response_contract(
            {
                "allowed_subjects": allowed.to_contract_list(),
                "allowed_lotteries": list(official_lottery_names()),
                "allowed_dates": list(dates[:40]),
                "allow_related_subjects": False,
                "requested_operation": str(intent) if intent else (str(relation) if relation else "analysis"),
                "canonical_count": total_count,
                "dates_are_sample": True,
                "sample_date_count": min(40, len(dates)),
                "sample_note": (
                    "dates/occurrences are a truncated SAMPLE; use counts.total as the only coincidence total."
                ),
            },
            counts=counts if isinstance(counts, dict) else {},
            resolved_intent=str(intent) if intent else None,
            relation=str(relation) if relation else None,
        )

        return EvidencePackage(
            question=question or "",
            resolved_intent=str(intent) if intent else None,
            subjects=subjects,
            relation=str(relation) if relation else None,
            scope="official_seven",
            official_lotteries=official_lottery_names(),
            dates=dates,
            positions=positions,
            counts=counts,
            occurrences=occurrences,
            comparison_data=comparison,
            deterministic_relations=[
                x
                for x in [
                    f"relation={relation}" if relation else None,
                    "scope=official_seven",
                ]
                if x
            ],
            source_rows=occurrences[:20],
            limitations=limitations,
            known_facts=known,
            forbidden_claims=forbidden,
            factual_answer=(factual_answer or "")[:4000],
            response_contract=response_contract,
        )

    @staticmethod
    def _subjects(question: str, state: Any, hermes: Any, data: dict) -> list[str]:
        out: list[str] = []

        def _add(src) -> None:
            for n in src or []:
                s = str(n).strip()
                if s and s not in out and re.fullmatch(r"\d{1,3}", s):
                    out.append(s.zfill(2) if len(s) <= 2 else s)

        hermes_subs = list(getattr(hermes, "inherited_subjects", None) or []) if hermes else []
        # When Hermes already carries an explicit subject set for this turn, do NOT
        # union sticky active_numbers (prevents 35+54 leaking into a 78+14 package).
        if hermes_subs:
            _add(hermes_subs)
            _add(list(data.get("numbers") or []))
            if data.get("number"):
                _add([data["number"]])
        else:
            _add(list(getattr(state, "active_numbers", None) or []) if state else [])
            _add(list(data.get("numbers") or []))
            if data.get("number"):
                _add([data["number"]])
        if len(out) < 2:
            for m in re.finditer(r"\b(\d{1,2})\b", question or ""):
                s = m.group(1).zfill(2)
                if s not in out:
                    out.append(s)
                if len(out) >= 4:
                    break
        return out[:8]

    @staticmethod
    def _dates(data: dict) -> list[str]:
        dates: list[str] = []
        for key in ("dates", "items", "coincidences", "occurrences"):
            for it in data.get(key) or []:
                if isinstance(it, dict):
                    d = str(it.get("date") or it.get("draw_date") or "")[:10]
                else:
                    d = str(it)[:10]
                if d and re.match(r"\d{4}-\d{2}-\d{2}", d) and d not in dates:
                    dates.append(d)
        last = data.get("last") if isinstance(data.get("last"), dict) else {}
        d = str(last.get("date") or last.get("draw_date") or data.get("last_occurrence_date") or "")[:10]
        if d and re.match(r"\d{4}-\d{2}-\d{2}", d) and d not in dates:
            dates.insert(0, d)
        return dates[:60]

    @staticmethod
    def _positions(data: dict) -> list[str]:
        pos: list[str] = []
        last = data.get("last") if isinstance(data.get("last"), dict) else {}
        for e in last.get("appearances") or last.get("entries") or []:
            if not isinstance(e, dict):
                continue
            p = e.get("position_label") or e.get("position")
            if p is not None and str(p) not in pos:
                pos.append(str(p))
        for it in data.get("items") or data.get("occurrences") or []:
            if not isinstance(it, dict):
                continue
            p = it.get("position_label") or it.get("position")
            if p is not None and str(p) not in pos:
                pos.append(str(p))
            for e in it.get("appearances") or []:
                if isinstance(e, dict):
                    p2 = e.get("position_label") or e.get("position")
                    if p2 is not None and str(p2) not in pos:
                        pos.append(str(p2))
        return pos[:24]

    @staticmethod
    def _counts(data: dict, structured: dict) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for k in (
            "total",
            "count",
            "first_related",
            "other_only",
            "both_first",
            "total_all_positions",
        ):
            if data.get(k) is not None:
                out[k] = data.get(k)
            elif structured.get(k) is not None:
                out[k] = structured.get(k)
        sm = structured.get("summary") if isinstance(structured.get("summary"), dict) else {}
        for k, v in sm.items():
            if k in {"total", "count", "found"} and v is not None:
                out.setdefault(k, v)
        return out

    @staticmethod
    def _occurrences(data: dict) -> list[dict[str, Any]]:
        items = data.get("items") or data.get("dates") or data.get("coincidences") or []
        out: list[dict[str, Any]] = []
        for it in items[:20]:
            if isinstance(it, dict):
                row = {
                    "date": str(it.get("date") or it.get("draw_date") or "")[:10] or None,
                    "lottery": it.get("lottery"),
                    "appearances": it.get("appearances") or it.get("entries") or [],
                }
                if it.get("position") is not None:
                    row["position"] = it.get("position")
                out.append(row)
        last = data.get("last") if isinstance(data.get("last"), dict) else None
        if last and not out:
            out.append(
                {
                    "date": str(last.get("date") or "")[:10] or None,
                    "lottery": last.get("lottery"),
                    "appearances": last.get("appearances") or last.get("entries") or [],
                }
            )
        return out

    @staticmethod
    def _comparison(data: dict, structured: dict) -> dict[str, Any]:
        for key in ("comparison", "compare", "comparison_data"):
            if isinstance(data.get(key), dict):
                return dict(data[key])
            if isinstance(structured.get(key), dict):
                return dict(structured[key])
        return {}

    @staticmethod
    def _known_facts(
        subjects: list[str],
        relation: str | None,
        counts: dict[str, Any],
        dates: list[str],
        data: dict,
    ) -> list[str]:
        facts: list[str] = []
        if subjects:
            facts.append(f"Sujetos verificados: {', '.join(subjects)}.")
        if counts.get("total") is not None:
            facts.append(f"Total verificado: {counts['total']}.")
        if dates:
            facts.append(f"Fecha más reciente en evidencia: {dates[0]}.")
        lots = data.get("lotteries") or []
        if lots:
            facts.append(f"Loterías en resultado: {', '.join(str(x) for x in lots[:8])}.")
        facts.append(f"Alcance: {scope_label_es()}.")
        return facts

    @staticmethod
    def _limitations(relation: str | None, counts: dict[str, Any], data: dict) -> list[str]:
        lim = [
            "Los hechos son históricos y descriptivos, no predicciones.",
            f"El alcance es {scope_label_es()}, no el catálogo global de ~50 loterías.",
        ]
        total = counts.get("total")
        if total is not None and int(total) == 0:
            lim.append("No hay ocurrencias en la evidencia; no inventar ejemplos.")
        if total is not None and int(total) <= 4:
            lim.append("Muestra pequeña: describir con cautela, sin generalizar reglas.")
        if relation == "same_day":
            lim.append(
                "Same-day no implica misma lotería ni misma posición salvo que la evidencia lo diga."
            )
        return lim
