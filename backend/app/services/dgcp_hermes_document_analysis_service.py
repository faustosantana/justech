"""Análisis documental Hermes/LLM — extracción profunda de requisitos (Fase 5)."""

from __future__ import annotations

import logging
import re
import uuid
from datetime import datetime, timezone
from typing import Any

from app.config import settings
from app.models.dgcp_opportunity import DGCPOpportunity
from app.models.dgcp_process_document import DGCPProcessDocument
from app.schemas.hermes import HermesAnalysisResult
from app.services.dgcp_requirements_extractor import (
    REQUIREMENT_RULES,
    ExtractedRequirement,
    ExtractionResult,
    RequirementEvidence,
)
from app.services.hermes_client import HermesClient

logger = logging.getLogger(__name__)

SNCC_PATTERN = re.compile(r"sncc\s*f\.?\s*0?(\d{2,3})", re.I)


class DGCPHermesDocumentAnalysisService:
    """Enriquece extracción heurística con Hermes cuando hay corpus de proceso."""

    def __init__(self, *, client: HermesClient | None = None):
        self.client = client or HermesClient()

    @staticmethod
    def enabled() -> bool:
        return bool(settings.dgcp_hermes_document_analysis and settings.hermes_enabled)

    async def enrich_extraction(
        self,
        opportunity: DGCPOpportunity,
        extraction: ExtractionResult,
        *,
        process_corpus: str,
        process_documents: list[DGCPProcessDocument] | None = None,
    ) -> tuple[ExtractionResult, dict[str, Any]]:
        meta: dict[str, Any] = {
            "status": "skipped",
            "reason": None,
            "confidence": 0.0,
            "analyzed_at": datetime.now(timezone.utc).isoformat(),
            "fallback_used": True,
        }
        if not self.enabled():
            meta["reason"] = "feature_disabled"
            meta["message"] = "Análisis Hermes deshabilitado; extracción heurística."
            return extraction, meta
        if not (process_corpus or "").strip():
            meta["reason"] = "no_process_corpus"
            meta["message"] = "Sin texto de pliego indexado; ejecute ingesta de documentos del proceso."
            return extraction, meta
        if not self.client.is_available():
            meta["reason"] = "hermes_unavailable"
            meta["status"] = "failed"
            meta["message"] = "Hermes no disponible; se aplicó extracción heurística."
            return extraction, meta

        tender = await self._analyze_tender(opportunity, extraction, process_corpus)
        if not tender:
            meta["status"] = "failed"
            meta["reason"] = "hermes_timeout_or_error"
            meta["message"] = "Hermes no respondió a tiempo; se aplicó extracción heurística."
            return extraction, meta

        doc_insights = await self._analyze_priority_documents(process_documents or [])
        merged = self._merge_into_extraction(
            extraction,
            tender,
            process_documents=process_documents or [],
            doc_insights=doc_insights,
        )
        meta.update({
            "status": "completed",
            "confidence": tender.confidence,
            "summary": tender.summary,
            "required_documents": tender.required_documents,
            "missing_documents": tender.missing_documents,
            "next_actions": tender.next_actions,
            "risks": tender.risks,
            "documents_analyzed": len(doc_insights),
            "llm_enriched": bool(tender.metadata.get("llm_enriched")),
            "fallback_used": False,
            "message": "Análisis documental Hermes completado.",
        })
        return merged, meta

    async def _analyze_tender(
        self,
        opportunity: DGCPOpportunity,
        extraction: ExtractionResult,
        process_corpus: str,
    ) -> HermesAnalysisResult | None:
        requirements: list[dict[str, Any]] = []
        for bucket in (
            extraction.mandatory_documents,
            extraction.technical,
            extraction.legal,
            extraction.financial,
            extraction.administrative,
        ):
            for item in bucket:
                requirements.append({
                    "key": item.key,
                    "label": item.label,
                    "tipo": item.tipo,
                    "mandatory": item.mandatory,
                })
        return await self.client.analyze_tender(
            process_code=opportunity.code,
            title=opportunity.title or "",
            institution=opportunity.institution or "",
            description=opportunity.description,
            objeto_proceso=opportunity.objeto_proceso,
            amount=str(opportunity.amount),
            deadline=opportunity.deadline.isoformat() if opportunity.deadline else None,
            documents_text=process_corpus[:100_000],
            requirements=requirements,
        )

    async def _analyze_priority_documents(
        self,
        process_documents: list[DGCPProcessDocument],
    ) -> list[dict[str, Any]]:
        insights: list[dict[str, Any]] = []
        priority_roles = {"pliego", "tdr", "especificaciones", "ficha_tecnica", "invitacion", "bases"}
        candidates = [
            d for d in process_documents
            if d.extracted_text and d.doc_role in priority_roles
        ][:3]
        for doc in candidates:
            result = await self.client.analyze_document(
                title=doc.title,
                content=doc.extracted_text[:40_000],
                mime_type="text/plain",
                context={"doc_role": doc.doc_role, "process_document_id": str(doc.id)},
            )
            if result:
                insights.append({
                    "process_document_id": str(doc.id),
                    "title": doc.title,
                    "doc_role": doc.doc_role,
                    "summary": result.summary,
                    "required_documents": result.required_documents,
                    "confidence": result.confidence,
                })
        return insights

    def _merge_into_extraction(
        self,
        extraction: ExtractionResult,
        tender: HermesAnalysisResult,
        *,
        process_documents: list[DGCPProcessDocument],
        doc_insights: list[dict[str, Any]],
    ) -> ExtractionResult:
        seen = self._collect_seen_keys(extraction)
        primary_doc = process_documents[0] if process_documents else None

        labels = list(tender.required_documents or [])
        for insight in doc_insights:
            labels.extend(insight.get("required_documents") or [])

        for raw_label in labels:
            rule = self._match_rule(str(raw_label))
            if not rule:
                custom = self._custom_requirement(str(raw_label), primary_doc, tender.confidence)
                if custom.key not in seen:
                    self._append_requirement(extraction, custom)
                    seen.add(custom.key)
                continue
            if rule["key"] in seen:
                continue
            req = ExtractedRequirement(
                key=rule["key"],
                label=rule["label"],
                tipo=rule["tipo"],
                mandatory=True,
                source="hermes_llm",
                matched_text=raw_label[:200],
                evidence=[
                    RequirementEvidence(
                        requirement_key=rule["key"],
                        documento_origen=primary_doc.title if primary_doc else "Análisis Hermes",
                        pagina=None,
                        seccion="Requisitos detectados por IA",
                        fragmento=(tender.summary or raw_label)[:300],
                        confianza="alta" if tender.confidence >= 0.7 else "media",
                        process_document_id=str(primary_doc.id) if primary_doc else None,
                    )
                ],
            )
            self._append_requirement(extraction, req)
            seen.add(rule["key"])

        for action in tender.next_actions or []:
            if action and action not in extraction.guarantees:
                extraction.guarantees.append(action)

        sncc_forms = list(extraction.sncc_forms)
        for label in labels:
            m = SNCC_PATTERN.search(str(label))
            if m:
                form = f"SNCC.F{int(m.group(1)):03d}"
                if form not in sncc_forms:
                    sncc_forms.append(form)
        extraction.sncc_forms = sncc_forms
        return extraction

    @staticmethod
    def _collect_seen_keys(extraction: ExtractionResult) -> set[str]:
        keys: set[str] = set()
        for bucket in (
            extraction.mandatory_documents,
            extraction.technical,
            extraction.legal,
            extraction.financial,
            extraction.administrative,
        ):
            keys.update(r.key for r in bucket)
        return keys

    @staticmethod
    def _match_rule(label: str) -> dict[str, Any] | None:
        low = label.lower().strip()
        if not low:
            return None
        for rule in REQUIREMENT_RULES:
            if rule["label"].lower() in low:
                return rule
            if any(pat in low for pat in rule["patterns"]):
                return rule
        return None

    @staticmethod
    def _custom_requirement(label: str, primary_doc: DGCPProcessDocument | None, confidence: float) -> ExtractedRequirement:
        slug = re.sub(r"[^a-z0-9]+", "_", label.lower())[:48].strip("_") or "requisito_ia"
        key = f"hermes_{slug}"
        return ExtractedRequirement(
            key=key,
            label=label[:200],
            tipo="administrativo",
            mandatory=True,
            source="hermes_llm",
            matched_text=label[:200],
            evidence=[
                RequirementEvidence(
                    requirement_key=key,
                    documento_origen=primary_doc.title if primary_doc else "Análisis Hermes",
                    pagina=None,
                    seccion="Requisito IA",
                    fragmento=label[:300],
                    confianza="alta" if confidence >= 0.7 else "media",
                    process_document_id=str(primary_doc.id) if primary_doc else None,
                )
            ],
        )

    @staticmethod
    def _append_requirement(extraction: ExtractionResult, req: ExtractedRequirement) -> None:
        tipo = req.tipo
        if tipo == "tecnico":
            extraction.technical.append(req)
        elif tipo == "legal":
            extraction.legal.append(req)
        elif tipo == "financiero":
            extraction.financial.append(req)
        else:
            extraction.administrative.append(req)
        extraction.mandatory_documents.append(req)
