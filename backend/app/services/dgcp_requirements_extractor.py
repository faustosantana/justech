"""Extracción de requisitos DGCP desde texto del proceso (Fase 7.1)."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date
from typing import Any

from app.models.dgcp_opportunity import DGCPOpportunity

DATE_RE = re.compile(
    r"\b(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})\b|\b(\d{4})-(\d{2})-(\d{2})\b"
)
SNCC_RE = re.compile(r"sncc\.?\s*f\.?\s*0?(33|34|42|47)", re.I)


@dataclass
class RequirementEvidence:
    requirement_key: str
    documento_origen: str
    pagina: int | None
    seccion: str | None
    fragmento: str
    confianza: str
    process_document_id: str | None = None


@dataclass
class ExtractedRequirement:
    key: str
    label: str
    tipo: str
    mandatory: bool = True
    subsanable: bool = False
    source: str = "extracted"
    matched_text: str | None = None
    evidence: list[RequirementEvidence] = field(default_factory=list)


@dataclass
class ExtractionResult:
    technical: list[ExtractedRequirement] = field(default_factory=list)
    legal: list[ExtractedRequirement] = field(default_factory=list)
    financial: list[ExtractedRequirement] = field(default_factory=list)
    administrative: list[ExtractedRequirement] = field(default_factory=list)
    mandatory_documents: list[ExtractedRequirement] = field(default_factory=list)
    subsanable_documents: list[ExtractedRequirement] = field(default_factory=list)
    critical_dates: list[dict[str, Any]] = field(default_factory=list)
    guarantees: list[str] = field(default_factory=list)
    samples: list[str] = field(default_factory=list)
    sncc_forms: list[str] = field(default_factory=list)
    certifications: list[str] = field(default_factory=list)
    combined_text: str = ""


REQUIREMENT_RULES: list[dict[str, Any]] = [
    {"key": "rpe", "label": "RPE vigente", "tipo": "legal", "doc": True, "patterns": ("rpe", "registro de proveedores", "proveedor del estado")},
    {"key": "certificacion_dgii", "label": "Certificación DGII", "tipo": "legal", "doc": True, "patterns": ("dgii", "impuestos internos", "certificación dgii", "certificacion dgii")},
    {"key": "certificacion_tss", "label": "Certificación TSS", "tipo": "legal", "doc": True, "patterns": ("tss", "seguro social", "certificación tss", "certificacion tss")},
    {"key": "registro_mercantil", "label": "Registro Mercantil", "tipo": "legal", "doc": True, "patterns": ("registro mercantil", "cámara de comercio", "camara de comercio")},
    {"key": "cedula_representante", "label": "Cédula representante legal", "tipo": "legal", "doc": True, "patterns": ("cédula", "cedula", "representante legal")},
    {"key": "poder_autorizacion", "label": "Poder / autorización", "tipo": "legal", "doc": True, "patterns": ("poder notarial", "autorización", "autorizacion")},
    {"key": "carta_presentacion", "label": "Carta de presentación", "tipo": "administrativo", "doc": True, "patterns": ("carta de presentación", "carta de presentacion")},
    {"key": "oferta_economica", "label": "Oferta económica", "tipo": "financiero", "doc": True, "patterns": ("oferta económica", "oferta economica", "propuesta económica")},
    {"key": "oferta_tecnica", "label": "Oferta técnica", "tipo": "tecnico", "doc": True, "patterns": ("oferta técnica", "oferta tecnica", "propuesta técnica")},
    {"key": "sncc_f033", "label": "SNCC F.033", "tipo": "administrativo", "doc": True, "patterns": ("sncc f.033", "sncc f033", "f.033", "f033")},
    {"key": "sncc_f034", "label": "SNCC F.034", "tipo": "administrativo", "doc": True, "patterns": ("sncc f.034", "sncc f034", "f.034", "f034")},
    {"key": "sncc_f042", "label": "SNCC F.042", "tipo": "administrativo", "doc": True, "patterns": ("sncc f.042", "sncc f042", "f.042", "f042")},
    {"key": "sncc_f047", "label": "SNCC F.047", "tipo": "administrativo", "doc": True, "patterns": ("sncc f.047", "sncc f047", "f.047", "f047")},
    {"key": "autorizacion_fabricante", "label": "Autorización fabricante", "tipo": "tecnico", "doc": True, "patterns": ("autorización del fabricante", "autorizacion del fabricante", "carta fabricante")},
    {"key": "ficha_tecnica", "label": "Fichas técnicas", "tipo": "tecnico", "doc": True, "patterns": ("ficha técnica", "ficha tecnica", "fichas técnicas")},
    {"key": "certificacion_mipyme", "label": "Certificación MIPYME", "tipo": "legal", "doc": True, "patterns": ("mipyme", "certificación mipyme")},
    {"key": "garantia_seriedad", "label": "Garantía de seriedad", "tipo": "financiero", "doc": True, "patterns": ("garantía de seriedad", "garantia de seriedad")},
    {"key": "estados_financieros", "label": "Estados financieros", "tipo": "financiero", "doc": True, "patterns": ("estados financieros", "balance general", "estado de resultados")},
    {"key": "especificaciones_tecnicas", "label": "Especificaciones técnicas", "tipo": "tecnico", "doc": False, "patterns": ("especificaciones técnicas", "especificacion tecnica", "requisitos técnicos")},
    {"key": "experiencia", "label": "Experiencia comprobable", "tipo": "tecnico", "doc": False, "patterns": ("experiencia comprobable", "experiencia en contratos")},
    {"key": "visita_tecnica", "label": "Visita técnica", "tipo": "tecnico", "doc": False, "patterns": ("visita técnica", "visita tecnica", "inspección", "inspeccion")},
    {"key": "criterios_evaluacion", "label": "Criterios de evaluación", "tipo": "administrativo", "doc": False, "patterns": ("criterio de evaluación", "criterios de evaluacion", "puntos de evaluación")},
    {"key": "descalificacion", "label": "Causales de descalificación", "tipo": "administrativo", "doc": False, "patterns": ("descalificación", "descalificacion", "causal de rechazo")},
    {"key": "vigencia_oferta", "label": "Vigencia de la oferta", "tipo": "administrativo", "doc": False, "patterns": ("vigencia de la oferta", "validez de la oferta")},
    {"key": "condiciones_pago", "label": "Condiciones de pago", "tipo": "financiero", "doc": False, "patterns": ("condiciones de pago", "forma de pago", "plazo de pago")},
    {"key": "tiempo_entrega", "label": "Tiempo de entrega", "tipo": "tecnico", "doc": False, "patterns": ("tiempo de entrega", "plazo de entrega", "días de entrega", "dias de entrega")},
]

DEFAULT_LICITACION_DOCS = [
    "rpe", "certificacion_tss", "certificacion_dgii", "registro_mercantil",
    "sncc_f042", "oferta_economica", "oferta_tecnica",
]


class DGCPRequirementsExtractor:
    def extract(
        self,
        opportunity: DGCPOpportunity,
        *,
        related_text: str = "",
        process_corpus: str = "",
        process_documents: list | None = None,
    ) -> ExtractionResult:
        portal_parts = self._portal_parts(opportunity, related_text)
        portal_combined = "\n".join(portal_parts).lower()

        if process_corpus.strip():
            combined = f"{process_corpus.lower()}\n{portal_combined}"
            primary_source = "process_documents"
        else:
            combined = portal_combined
            primary_source = "portal_dgcp"

        result = ExtractionResult(combined_text=combined)
        doc_lookup = {d.title: d for d in (process_documents or []) if hasattr(d, "title")}

        seen_keys: set[str] = set()
        evidence_records: list[dict] = []

        for rule in REQUIREMENT_RULES:
            matched = None
            fragment = None
            source_doc = None
            for pat in rule["patterns"]:
                idx = combined.find(pat)
                if idx >= 0:
                    matched = pat
                    fragment = combined[max(0, idx - 40): idx + len(pat) + 80].strip()
                    source_doc = self._find_source_doc(fragment or pat, doc_lookup, process_corpus)
                    break
            if not matched and rule["key"] in DEFAULT_LICITACION_DOCS and not combined.strip():
                matched = "default_licitacion"
            if not matched:
                continue
            if rule["key"] in seen_keys:
                continue
            seen_keys.add(rule["key"])

            confianza = "alta" if source_doc and primary_source == "process_documents" else (
                "media" if matched != "default_licitacion" else "baja"
            )
            ev = RequirementEvidence(
                requirement_key=rule["key"],
                documento_origen=source_doc.title if source_doc else (
                    "Pliego/TDR del proceso" if primary_source == "process_documents" else "Portal DGCP"
                ),
                pagina=self._guess_page(source_doc, fragment) if source_doc else None,
                seccion=source_doc.doc_role.replace("_", " ").title() if source_doc else "Requisitos",
                fragmento=(fragment or matched)[:300],
                confianza=confianza,
                process_document_id=str(source_doc.id) if source_doc else None,
            )
            evidence_records.append(ev.__dict__)

            req = ExtractedRequirement(
                key=rule["key"],
                label=rule["label"],
                tipo=rule["tipo"],
                mandatory=True,
                subsanable=rule.get("subsanable", False),
                matched_text=matched if matched != "default_licitacion" else None,
                source=primary_source if matched != "default_licitacion" else "default",
                evidence=[ev],
            )
            tipo = rule["tipo"]
            if tipo == "tecnico":
                result.technical.append(req)
            elif tipo == "legal":
                result.legal.append(req)
            elif tipo == "financiero":
                result.financial.append(req)
            else:
                result.administrative.append(req)
            if rule.get("doc"):
                result.mandatory_documents.append(req)

        result.evidence_records = evidence_records  # type: ignore[attr-defined]

        self._append_heuristics(combined, result, opportunity)

        for key in DEFAULT_LICITACION_DOCS:
            if key in seen_keys:
                continue
            rule = next((r for r in REQUIREMENT_RULES if r["key"] == key), None)
            if not rule:
                continue
            seen_keys.add(key)
            req = ExtractedRequirement(
                key=rule["key"],
                label=rule["label"],
                tipo=rule["tipo"],
                mandatory=True,
                source="baseline_licitacion",
            )
            result.mandatory_documents.append(req)
            tipo = rule["tipo"]
            if tipo == "tecnico":
                result.technical.append(req)
            elif tipo == "legal":
                result.legal.append(req)
            elif tipo == "financiero":
                result.financial.append(req)
            else:
                result.administrative.append(req)

        return result

    @staticmethod
    def _portal_parts(opportunity: DGCPOpportunity, related_text: str) -> list[str]:
        parts = [
            opportunity.title or "",
            opportunity.description or "",
            opportunity.objeto_proceso or "",
            opportunity.modalidad or "",
            opportunity.institution or "",
            related_text,
        ]
        full_info = opportunity.full_info or {}
        if isinstance(full_info, dict):
            for val in full_info.values():
                if isinstance(val, str):
                    parts.append(val)
                elif isinstance(val, list):
                    parts.extend(str(v) for v in val if v)
        raw = opportunity.raw_payload or {}
        if isinstance(raw, dict):
            for key in ("descripcion", "articulos", "pliego", "documentos", "requisitos"):
                val = raw.get(key)
                if isinstance(val, str):
                    parts.append(val)
                elif isinstance(val, list):
                    parts.extend(str(v) for v in val)
        return parts

    @staticmethod
    def _find_source_doc(fragment: str, doc_lookup: dict, corpus: str) -> Any | None:
        if not corpus:
            return None
        for title, doc in doc_lookup.items():
            marker = f"=== {title}"
            if marker in corpus and fragment and fragment in corpus:
                return doc
        for doc in doc_lookup.values():
            if getattr(doc, "doc_role", "") in ("pliego", "tdr", "ficha_tecnica", "especificaciones"):
                return doc
        return next(iter(doc_lookup.values()), None)

    @staticmethod
    def _guess_page(doc, fragment: str | None) -> int | None:
        text = getattr(doc, "extracted_text", "") or ""
        if not text or not fragment:
            return None
        pos = text.lower().find((fragment or "")[:40].lower())
        if pos < 0:
            return None
        return max(1, pos // 3000 + 1)

    def _append_heuristics(self, combined: str, result: ExtractionResult, opportunity: DGCPOpportunity) -> None:
        for m in SNCC_RE.finditer(combined):
            form = f"SNCC.F.{m.group(1)}"
            if form not in result.sncc_forms:
                result.sncc_forms.append(form)

        if "garantía" in combined or "garantia" in combined:
            if "seriedad" in combined:
                result.guarantees.append("Garantía de seriedad de oferta")
            if "cumplimiento" in combined:
                result.guarantees.append("Garantía de cumplimiento de contrato")
            if not result.guarantees:
                result.guarantees.append("Garantía requerida según pliego")

        if "muestra" in combined:
            result.samples.append("Muestras físicas solicitadas en pliego")

        for cert_key in ("tss", "dgii", "rpe", "mipyme"):
            if cert_key in combined:
                label = next(
                    (r["label"] for r in REQUIREMENT_RULES if cert_key in r["key"]),
                    cert_key.upper(),
                )
                if label not in result.certifications:
                    result.certifications.append(label)

        if opportunity.deadline:
            result.critical_dates.append({
                "label": "Fecha límite de presentación",
                "date": str(opportunity.deadline),
                "type": "deadline",
            })

        for match in DATE_RE.finditer(combined):
            result.critical_dates.append({
                "label": "Fecha detectada en pliego",
                "date": match.group(0),
                "type": "detected",
            })
