"""Pipeline canónico por etapas — análisis profundo de pliego (29 campos).

Extiende el flujo de DGCPBidPackageService.analyze; no es un pipeline paralelo.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
import time
import uuid
from datetime import datetime, timezone
from typing import Any

from app.models.dgcp_bid_package import DGCPBidPackage
from app.models.dgcp_opportunity import DGCPOpportunity
from app.models.dgcp_process_document import DGCPProcessDocument
from app.schemas.dgcp_pliego_analysis import (
    FIELD_LABELS,
    PLIEGO_FIELD_KEYS,
    PROMPT_VERSION,
    SCHEMA_VERSION,
    PliegoAnalysisMeta,
    PliegoAnalysisResult,
    PliegoAnalysisStatus,
    PliegoAnalysisVersionSummary,
    PliegoDecisionSuggested,
    PliegoDocumentInput,
    PliegoEvidence,
    PliegoFieldResult,
    PliegoStageResult,
)

logger = logging.getLogger(__name__)

CHARS_PER_PAGE_FALLBACK = 3000
MAX_FRAGMENT = 240
MAX_CORPUS_FOR_LLM = 90_000
LLM_TIMEOUT_HINT = 120
MAX_LLM_RETRIES = 2

STAGE_ORDER = (
    "A_ingestion",
    "B_classification",
    "C_datos_generales",
    "D_requisitos_legales_admin",
    "E_requisitos_tecnicos",
    "F_requisitos_financieros",
    "G_documentos_formularios",
    "H_cronograma_pagos_garantias",
    "I_criterios_riesgos",
    "J_pendientes_preguntas",
    "K_recomendaciones_decision",
    "L_consolidacion",
)

REQUIRED_STAGES = STAGE_ORDER

SYSTEM_PROMPT = f"""Eres un analista senior de licitaciones públicas de República Dominicana (DGCP).
Extrae solo hechos presentes en el texto. No inventes páginas ni montos.
Responde ÚNICAMENTE JSON válido según el esquema pedido.
Versión de prompt: {PROMPT_VERSION}. Schema: {SCHEMA_VERSION}.
Cada hallazgo debe incluir evidence con document_id, document_name, page (int o null),
section, fragment (máx 200 chars) y confidence (0-1).
Si no hay dato: found=false, value="No identificado", review_required=true.
"""


def _prompt_hash() -> str:
    return hashlib.sha256(f"{PROMPT_VERSION}|{SCHEMA_VERSION}|{SYSTEM_PROMPT}".encode()).hexdigest()[:16]


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _short(text: str | None, n: int = MAX_FRAGMENT) -> str:
    if not text:
        return ""
    t = re.sub(r"\s+", " ", str(text)).strip()
    return t if len(t) <= n else t[: n - 1] + "…"


def _hash_text(text: str | None) -> str | None:
    if not text:
        return None
    return hashlib.sha256(text.encode("utf-8", errors="ignore")).hexdigest()


class DGCPPliegoDeepAnalysisService:
    """Construye y versiona el análisis canónico de 29 campos."""

    def __init__(self, db, tenant_id: uuid.UUID, user_id: uuid.UUID | None = None):
        self.db = db
        self.tenant_id = tenant_id
        self.user_id = user_id

    async def get_current(self, opportunity_id: uuid.UUID) -> PliegoAnalysisResult | None:
        pkg = await self._get_package(opportunity_id)
        if not pkg:
            return None
        raw = (pkg.manifest or {}).get("pliego_analysis")
        if not raw:
            return None
        try:
            result = PliegoAnalysisResult.model_validate(raw)
            result.ensure_complete_fields()
            return result
        except Exception:
            logger.exception("pliego_analysis corrupt opportunity=%s", opportunity_id)
            return None

    async def list_versions(self, opportunity_id: uuid.UUID) -> list[PliegoAnalysisVersionSummary]:
        pkg = await self._get_package(opportunity_id)
        if not pkg:
            return []
        versions = (pkg.manifest or {}).get("pliego_analysis_versions") or []
        out: list[PliegoAnalysisVersionSummary] = []
        for item in versions:
            try:
                out.append(PliegoAnalysisVersionSummary.model_validate(item))
            except Exception:
                continue
        return out

    async def run(
        self,
        opportunity: DGCPOpportunity,
        *,
        process_documents: list[DGCPProcessDocument],
        process_corpus: str,
        extraction: Any | None = None,
        hermes_meta: dict[str, Any] | None = None,
        requirement_evidence: list[dict] | None = None,
        checklist: list[dict] | None = None,
        risks: list[dict] | None = None,
        force: bool = False,
    ) -> PliegoAnalysisResult:
        started = time.monotonic()
        hermes_meta = hermes_meta or {}
        stages: list[PliegoStageResult] = []
        failed_stages: list[str] = []

        pkg = await self._get_package(opportunity.id)
        next_version = 1
        if pkg:
            current = (pkg.manifest or {}).get("pliego_analysis") or {}
            next_version = int(current.get("version") or 0) + 1
            if not force and current.get("status") in ("completed", "partial", "review_required"):
                # Reanalysis only when force=True; otherwise still refresh if missing fields
                fields = current.get("fields") or {}
                if all(k in fields for k in PLIEGO_FIELD_KEYS):
                    try:
                        return PliegoAnalysisResult.model_validate(current)
                    except Exception:
                        pass

        result = PliegoAnalysisResult(
            opportunity_id=opportunity.id,
            status=PliegoAnalysisStatus.EXTRACTING,
            version=next_version,
            created_at=_now(),
            meta=PliegoAnalysisMeta(
                prompt_hash=_prompt_hash(),
                user_id=str(self.user_id) if self.user_id else None,
                hermes_status=hermes_meta.get("status"),
            ),
        )

        # A — ingestión
        t0 = time.monotonic()
        try:
            docs, segments, doc_hashes = self._stage_ingestion(process_documents)
            result.documents = docs
            result.meta.document_hashes = doc_hashes
            result.status = PliegoAnalysisStatus.ANALYZING
            stages.append(PliegoStageResult(
                stage="A_ingestion",
                status="completed",
                message=f"{len(docs)} documento(s), {len(segments)} segmento(s)",
                duration_ms=int((time.monotonic() - t0) * 1000),
            ))
        except Exception as exc:
            failed_stages.append("A_ingestion")
            stages.append(PliegoStageResult(
                stage="A_ingestion", status="failed", error=str(exc),
                duration_ms=int((time.monotonic() - t0) * 1000),
            ))
            docs, segments = [], []

        # B — clasificación (ya en doc_role)
        t0 = time.monotonic()
        try:
            classified = self._stage_classification(docs)
            stages.append(PliegoStageResult(
                stage="B_classification",
                status="completed",
                message=f"Roles: {', '.join(sorted(classified.keys())) or 'ninguno'}",
                duration_ms=int((time.monotonic() - t0) * 1000),
            ))
        except Exception as exc:
            failed_stages.append("B_classification")
            stages.append(PliegoStageResult(
                stage="B_classification", status="failed", error=str(exc),
                duration_ms=int((time.monotonic() - t0) * 1000),
            ))

        fields: dict[str, PliegoFieldResult] = {}
        evidence_index = self._index_evidence(requirement_evidence or [], process_documents)

        # C–K deterministic + optional LLM overlay
        stage_runners = [
            ("C_datos_generales", self._fill_datos_generales),
            ("D_requisitos_legales_admin", self._fill_requisitos_legales_admin),
            ("E_requisitos_tecnicos", self._fill_requisitos_tecnicos),
            ("F_requisitos_financieros", self._fill_requisitos_financieros),
            ("G_documentos_formularios", self._fill_documentos_formularios),
            ("H_cronograma_pagos_garantias", self._fill_cronograma_pagos),
            ("I_criterios_riesgos", self._fill_criterios_riesgos),
            ("J_pendientes_preguntas", self._fill_pendientes_preguntas),
            ("K_recomendaciones_decision", self._fill_recomendaciones_decision),
        ]
        ctx = {
            "opportunity": opportunity,
            "docs": docs,
            "segments": segments,
            "corpus": process_corpus or "",
            "extraction": extraction,
            "hermes_meta": hermes_meta,
            "evidence_index": evidence_index,
            "checklist": checklist or [],
            "risks": risks or [],
        }
        for stage_name, fn in stage_runners:
            t0 = time.monotonic()
            try:
                partial = fn(ctx, fields)
                fields.update(partial)
                stages.append(PliegoStageResult(
                    stage=stage_name,
                    status="completed",
                    message=f"{len(partial)} campo(s)",
                    duration_ms=int((time.monotonic() - t0) * 1000),
                ))
            except Exception as exc:
                logger.exception("pliego stage failed %s", stage_name)
                failed_stages.append(stage_name)
                stages.append(PliegoStageResult(
                    stage=stage_name,
                    status="failed",
                    error=str(exc)[:300],
                    duration_ms=int((time.monotonic() - t0) * 1000),
                ))

        # LLM enrichment (best-effort, no crash)
        t0 = time.monotonic()
        llm_fields, llm_meta = await self._llm_enrich_stages(ctx, fields)
        if llm_fields:
            for k, v in llm_fields.items():
                if k in fields and fields[k].found and not v.found:
                    continue
                if k in fields and fields[k].manual_override:
                    continue
                fields[k] = self._merge_field(fields.get(k), v)
            result.meta.llm_enriched = True
            result.meta.model = llm_meta.get("model")
            result.meta.tokens_in = llm_meta.get("tokens_in")
            result.meta.tokens_out = llm_meta.get("tokens_out")
            stages.append(PliegoStageResult(
                stage="llm_enrichment",
                status="completed" if llm_meta.get("ok") else "partial",
                message=llm_meta.get("message", ""),
                duration_ms=int((time.monotonic() - t0) * 1000),
                error=llm_meta.get("error"),
            ))
            if not llm_meta.get("ok"):
                failed_stages.append("llm_enrichment")
        else:
            stages.append(PliegoStageResult(
                stage="llm_enrichment",
                status="skipped",
                message=llm_meta.get("message") or "LLM no usado; mapeo determinístico",
                duration_ms=int((time.monotonic() - t0) * 1000),
            ))

        # L — consolidación
        t0 = time.monotonic()
        result.status = PliegoAnalysisStatus.CONSOLIDATING
        try:
            fields, contradictions, validation_errors = self._consolidate(
                fields, segments=segments, docs=docs, opportunity=opportunity
            )
            result.meta.contradictions = contradictions
            result.meta.validation_errors = validation_errors
            stages.append(PliegoStageResult(
                stage="L_consolidacion",
                status="partial" if validation_errors else "completed",
                message=f"contradicciones={len(contradictions)} validación={len(validation_errors)}",
                duration_ms=int((time.monotonic() - t0) * 1000),
            ))
        except Exception as exc:
            failed_stages.append("L_consolidacion")
            stages.append(PliegoStageResult(
                stage="L_consolidacion", status="failed", error=str(exc),
                duration_ms=int((time.monotonic() - t0) * 1000),
            ))

        # Ensure all 29
        for key in PLIEGO_FIELD_KEYS:
            if key not in fields:
                fields[key] = self._not_found(key, notes="Etapa no produjo el campo")

        result.fields = fields
        result.stages = stages
        result.meta.failed_stages = failed_stages
        result.meta.duration_ms = int((time.monotonic() - started) * 1000)
        result.decision = self._decision_from_field(fields.get("decision_sugerida"))

        if failed_stages and any(s in REQUIRED_STAGES for s in failed_stages):
            result.status = PliegoAnalysisStatus.PARTIAL
        elif any(f.review_required for f in fields.values()):
            # still completed if all stages ok — review_required is expected for missing data
            missing_critical = [
                k for k in ("objeto_contratacion", "fecha_limite", "documentos_solicitados")
                if not fields[k].found
            ]
            result.status = (
                PliegoAnalysisStatus.REVIEW_REQUIRED
                if missing_critical
                else PliegoAnalysisStatus.COMPLETED
            )
        else:
            result.status = PliegoAnalysisStatus.COMPLETED

        if any(s.status == "failed" for s in stages if s.stage.startswith(("A_", "L_"))):
            if result.status == PliegoAnalysisStatus.COMPLETED:
                result.status = PliegoAnalysisStatus.PARTIAL

        if not any(d.extracted_text_present for d in result.documents):
            result.status = PliegoAnalysisStatus.REVIEW_REQUIRED
            result.meta.validation_errors = list(result.meta.validation_errors) + [
                "Sin texto de pliego/anexos; cargue o reingeste documentos del proceso para evidencia por página."
            ]

        await self._persist(opportunity.id, result)
        return result

    async def retry_stage(
        self,
        opportunity: DGCPOpportunity,
        stage: str,
        **kwargs: Any,
    ) -> PliegoAnalysisResult:
        """Reejecuta análisis completo (etapas son interdependientes); marca force."""
        return await self.run(opportunity, force=True, **kwargs)

    async def apply_field_review(
        self,
        opportunity_id: uuid.UUID,
        field_key: str,
        *,
        reviewed: bool = True,
        comment: str | None = None,
        corrected_value: Any = None,
        corrected_items: list[Any] | None = None,
    ) -> PliegoAnalysisResult:
        current = await self.get_current(opportunity_id)
        if not current:
            raise ValueError("No hay análisis de pliego para revisar")
        if field_key not in PLIEGO_FIELD_KEYS:
            raise ValueError(f"Campo inválido: {field_key}")
        field = current.fields[field_key]
        field.reviewed = reviewed
        if comment is not None:
            field.comment = comment
        if corrected_value is not None:
            field.value = corrected_value
            field.found = corrected_value not in (None, "", "No identificado")
            field.manual_override = True
            field.review_required = False
        if corrected_items is not None:
            field.items = corrected_items
            field.found = bool(corrected_items)
            field.manual_override = True
            field.review_required = False
        current.fields[field_key] = field
        await self._persist(opportunity_id, current, bump_version=False)
        return current

    # ── stages ──────────────────────────────────────────────────────────

    def _stage_ingestion(
        self, process_documents: list[DGCPProcessDocument]
    ) -> tuple[list[PliegoDocumentInput], list[dict], list[str]]:
        docs: list[PliegoDocumentInput] = []
        segments: list[dict] = []
        hashes: list[str] = []
        seen_hashes: dict[str, str] = {}

        for doc in process_documents:
            meta = dict(doc.metadata_ or {})
            text = doc.extracted_text or ""
            ch = meta.get("content_hash") or _hash_text(text) or _hash_text(doc.title) or str(doc.id)
            duplicate_of = None
            if ch in seen_hashes:
                duplicate_of = seen_hashes[ch]
            else:
                seen_hashes[ch] = str(doc.id)
            hashes.append(ch)

            pages_list = meta.get("pages_text") or meta.get("pages")
            page_count = meta.get("page_count")
            ocr_used = bool(meta.get("ocr_used"))
            ocr_conf = meta.get("ocr_confidence")
            if isinstance(pages_list, list) and pages_list and all(isinstance(p, str) for p in pages_list):
                page_count = page_count or len(pages_list)
            elif text:
                page_count = page_count or max(1, (len(text) + CHARS_PER_PAGE_FALLBACK - 1) // CHARS_PER_PAGE_FALLBACK)

            errors = []
            if meta.get("extraction_error"):
                errors.append(str(meta["extraction_error"]))
            if not text and doc.ingestion_status not in ("analyzed",):
                errors.append("Sin texto extraído")

            docs.append(PliegoDocumentInput(
                document_id=str(doc.id),
                name=doc.title,
                doc_type=doc.doc_role or "general",
                content_hash=ch,
                pages=page_count,
                extracted_text_present=bool(text.strip()),
                extraction_status=doc.ingestion_status or "pending",
                extraction_errors=errors,
                ocr_used=ocr_used,
                ocr_confidence=float(ocr_conf) if ocr_conf is not None else None,
                analyzed_at=doc.analyzed_at,
                duplicate_of=duplicate_of,
            ))

            if duplicate_of or not text.strip():
                continue

            if isinstance(pages_list, list) and pages_list and all(isinstance(p, str) for p in pages_list):
                for i, page_text in enumerate(pages_list, start=1):
                    if not page_text.strip():
                        continue
                    section = self._guess_section(page_text)
                    segments.append({
                        "document_id": str(doc.id),
                        "document_name": doc.title,
                        "page": i,
                        "page_identified": True,
                        "section": section,
                        "position": i,
                        "text": page_text,
                    })
            else:
                # Fallback: estimate pages by char windows; mark lower confidence
                for i, start in enumerate(range(0, len(text), CHARS_PER_PAGE_FALLBACK), start=1):
                    chunk = text[start : start + CHARS_PER_PAGE_FALLBACK]
                    segments.append({
                        "document_id": str(doc.id),
                        "document_name": doc.title,
                        "page": i,
                        "page_identified": False,
                        "section": self._guess_section(chunk),
                        "position": i,
                        "text": chunk,
                    })
        return docs, segments, hashes

    def _stage_classification(self, docs: list[PliegoDocumentInput]) -> dict[str, list[str]]:
        by_role: dict[str, list[str]] = {}
        for d in docs:
            if d.duplicate_of:
                continue
            by_role.setdefault(d.doc_type, []).append(d.document_id)
        return by_role

    def _fill_datos_generales(self, ctx: dict, fields: dict) -> dict[str, PliegoFieldResult]:
        opp: DGCPOpportunity = ctx["opportunity"]
        hermes = ctx["hermes_meta"]
        out: dict[str, PliegoFieldResult] = {}

        summary = hermes.get("summary") or opp.description or opp.objeto_proceso
        out["resumen_ejecutivo"] = self._scalar_field(
            "resumen_ejecutivo",
            summary,
            evidence=self._find_evidence(ctx, keywords=["objeto", "proceso", "contratación"], prefer_roles=("pliego", "tdr")),
            source_hint=opp.code,
        )

        out["objeto_contratacion"] = self._scalar_field(
            "objeto_contratacion",
            opp.objeto_proceso or opp.title,
            evidence=self._find_evidence(ctx, keywords=["objeto", "adquisición"], prefer_roles=("pliego",)),
        )
        out["institucion"] = self._scalar_field(
            "institucion",
            opp.institution,
            evidence=self._find_evidence(ctx, keywords=["institución", "unidad de compra", opp.institution or ""], prefer_roles=("pliego",)),
        )
        modalidad = getattr(opp, "modality", None) or getattr(opp, "modalidad", None) or hermes.get("detected_type")
        out["modalidad"] = self._scalar_field(
            "modalidad",
            modalidad,
            evidence=self._find_evidence(ctx, keywords=["modalidad", "compra menor", "licitación"], prefer_roles=("pliego",)),
        )
        amount = str(opp.amount) if opp.amount is not None else None
        out["monto_estimado"] = self._scalar_field(
            "monto_estimado",
            amount,
            evidence=self._find_evidence(ctx, keywords=["monto", "presupuesto", "RD$"], prefer_roles=("pliego",)),
        )
        deadline = opp.deadline.isoformat() if opp.deadline else None
        out["fecha_limite"] = self._scalar_field(
            "fecha_limite",
            deadline,
            evidence=self._find_evidence(ctx, keywords=["fecha límite", "cierre", "apertura"], prefer_roles=("pliego", "cronograma")),
        )
        return out

    def _fill_requisitos_legales_admin(self, ctx: dict, _fields: dict) -> dict[str, PliegoFieldResult]:
        extraction = ctx.get("extraction")
        out: dict[str, PliegoFieldResult] = {}
        out["requisitos_legales"] = self._list_from_extraction(
            "requisitos_legales", extraction, "legal", ctx
        )
        out["requisitos_administrativos"] = self._list_from_extraction(
            "requisitos_administrativos", extraction, "administrative", ctx
        )
        out["experiencia_requerida"] = self._items_from_keywords(
            "experiencia_requerida",
            ctx,
            keywords=["experiencia", "años de experiencia", "contratos similares"],
        )
        return out

    def _fill_requisitos_tecnicos(self, ctx: dict, _fields: dict) -> dict[str, PliegoFieldResult]:
        extraction = ctx.get("extraction")
        return {
            "requisitos_tecnicos": self._list_from_extraction(
                "requisitos_tecnicos", extraction, "technical", ctx
            )
        }

    def _fill_requisitos_financieros(self, ctx: dict, _fields: dict) -> dict[str, PliegoFieldResult]:
        extraction = ctx.get("extraction")
        return {
            "requisitos_financieros": self._list_from_extraction(
                "requisitos_financieros", extraction, "financial", ctx
            )
        }

    def _fill_documentos_formularios(self, ctx: dict, _fields: dict) -> dict[str, PliegoFieldResult]:
        hermes = ctx["hermes_meta"]
        extraction = ctx.get("extraction")
        docs_items: list[dict] = []
        seen: set[str] = set()

        def _add(name: str, category: str, evidence: list[PliegoEvidence], mandatory: bool = True):
            norm = self._normalize_doc_name(name)
            if not norm or norm.lower() in seen:
                return
            seen.add(norm.lower())
            docs_items.append({
                "nombre": norm,
                "categoria": category,
                "obligatorio": mandatory,
                "condicion": None,
                "fuente": evidence[0].document_name if evidence else None,
                "pagina": evidence[0].page if evidence else None,
                "estado": "pendiente",
                "match_corporativo": None,
                "vigencia": None,
                "responsable": None,
                "fecha_limite": None,
                "observacion": None,
                "evidence": [e.model_dump() for e in evidence[:2]],
            })

        for label in hermes.get("required_documents") or []:
            ev = self._find_evidence(ctx, keywords=[str(label)[:40]], prefer_roles=("pliego", "tdr", "anexo"))
            _add(str(label), "documento", ev)

        if extraction:
            for bucket_name, cat in (
                ("mandatory_documents", "documento"),
                ("administrative", "administrativo"),
                ("legal", "legal"),
                ("financial", "financiero"),
                ("technical", "tecnico"),
            ):
                for item in getattr(extraction, bucket_name, None) or []:
                    label = getattr(item, "label", None) or getattr(item, "key", "")
                    evs = []
                    for e in getattr(item, "evidence", None) or []:
                        evs.append(PliegoEvidence(
                            document_id=getattr(e, "process_document_id", None),
                            document_name=getattr(e, "documento_origen", "") or "",
                            page=getattr(e, "pagina", None),
                            section=getattr(e, "seccion", None),
                            fragment=_short(getattr(e, "fragmento", None)),
                            confidence=0.75 if getattr(e, "confianza", "") == "alta" else 0.55,
                            page_identified=getattr(e, "pagina", None) is not None,
                        ))
                    if not evs:
                        evs = self._find_evidence(ctx, keywords=[str(label)[:40]])
                    _add(str(label), cat, evs)

        for item in ctx.get("checklist") or []:
            if item.get("requirement"):
                _add(
                    item["requirement"],
                    item.get("tipo") or "documento",
                    self._find_evidence(ctx, keywords=[str(item["requirement"])[:40]]),
                    mandatory=bool(item.get("mandatory", True)),
                )

        out: dict[str, PliegoFieldResult] = {}
        out["documentos_solicitados"] = PliegoFieldResult(
            key="documentos_solicitados",
            value=f"{len(docs_items)} documento(s)" if docs_items else "No identificado",
            items=docs_items,
            found=bool(docs_items),
            confidence=0.7 if docs_items else 0.2,
            evidence=[PliegoEvidence.model_validate(d["evidence"][0]) for d in docs_items if d.get("evidence")][:8],
            source_documents=list({d["fuente"] for d in docs_items if d.get("fuente")}),
            review_required=not bool(docs_items),
        )
        out["formularios_requeridos"] = self._items_from_keywords(
            "formularios_requeridos", ctx, keywords=["SNCC", "formulario", "OF-01", "F.033", "F.034"]
        )
        out["certificaciones_requeridas"] = self._items_from_keywords(
            "certificaciones_requeridas",
            ctx,
            keywords=["certificación", "RNC", "TSS", "DGII", "MIPYME", "registro de proveedores"],
        )
        out["muestras_requeridas"] = self._items_from_keywords(
            "muestras_requeridas", ctx, keywords=["muestra", "catálogo", "prototipo"]
        )
        out["visita_tecnica"] = self._items_from_keywords(
            "visita_tecnica", ctx, keywords=["visita técnica", "visita de obra", "inspección previa"]
        )
        return out

    def _fill_cronograma_pagos(self, ctx: dict, _fields: dict) -> dict[str, PliegoFieldResult]:
        return {
            "cronograma": self._items_from_keywords(
                "cronograma", ctx, keywords=["cronograma", "calendario", "hitos", "fecha de"]
            ),
            "lugar_entrega": self._items_from_keywords(
                "lugar_entrega", ctx, keywords=["lugar de entrega", "domicilio", "almacén", "dirección de entrega"]
            ),
            "plazo_entrega": self._items_from_keywords(
                "plazo_entrega", ctx, keywords=["plazo de entrega", "días hábiles", "días calendario"]
            ),
            "condiciones_pago": self._items_from_keywords(
                "condiciones_pago", ctx, keywords=["forma de pago", "condiciones de pago", "anticipo"]
            ),
            "garantias": self._items_from_keywords(
                "garantias", ctx, keywords=["garantía", "fianza", "seriedad de oferta", "fiel cumplimiento"]
            ),
        }

    def _fill_criterios_riesgos(self, ctx: dict, _fields: dict) -> dict[str, PliegoFieldResult]:
        risks_items: list[dict] = []
        for r in ctx.get("risks") or []:
            if isinstance(r, dict):
                risks_items.append({
                    "categoria": r.get("categoria") or r.get("category") or "proceso",
                    "severidad": r.get("nivel") or r.get("severidad") or "medio",
                    "probabilidad": r.get("probabilidad") or "media",
                    "impacto": r.get("impacto") or r.get("descripcion") or "",
                    "evidencia": r.get("evidencia"),
                    "mitigacion": r.get("mitigacion") or r.get("mitigation"),
                    "descripcion": r.get("descripcion") or str(r),
                })
            elif isinstance(r, str) and r.strip():
                risks_items.append({
                    "categoria": "proceso",
                    "severidad": "medio",
                    "probabilidad": "media",
                    "impacto": r.strip(),
                    "descripcion": r.strip(),
                    "mitigacion": None,
                })
        for hr in (ctx["hermes_meta"].get("risks") or []):
            if isinstance(hr, dict) and hr.get("descripcion"):
                risks_items.append({
                    "categoria": hr.get("categoria") or "hermes",
                    "severidad": hr.get("nivel") or "medio",
                    "probabilidad": "media",
                    "impacto": hr["descripcion"],
                    "descripcion": hr["descripcion"],
                    "mitigacion": hr.get("mitigacion"),
                })
            elif isinstance(hr, str):
                risks_items.append({
                    "categoria": "hermes",
                    "severidad": "medio",
                    "probabilidad": "media",
                    "impacto": hr,
                    "descripcion": hr,
                })

        # Dedup by description
        seen = set()
        deduped = []
        for item in risks_items:
            key = (item.get("descripcion") or "")[:120].lower()
            if key in seen:
                continue
            seen.add(key)
            deduped.append(item)

        return {
            "criterios_evaluacion": self._items_from_keywords(
                "criterios_evaluacion",
                ctx,
                keywords=["criterio de evaluación", "puntaje", "evaluación técnica", "precio"],
            ),
            "causas_descalificacion": self._items_from_keywords(
                "causas_descalificacion",
                ctx,
                keywords=["descalificación", "desierto", "rechazo", "no se considerará"],
            ),
            "riesgos": PliegoFieldResult(
                key="riesgos",
                value=f"{len(deduped)} riesgo(s)" if deduped else "No identificado",
                items=deduped,
                found=bool(deduped),
                confidence=0.65 if deduped else 0.2,
                evidence=self._find_evidence(ctx, keywords=["riesgo", "plazo", "garantía"]),
                review_required=not bool(deduped),
                notes="" if deduped else "Sin riesgos explícitos; revisar plazo y requisitos.",
            ),
        }

    def _fill_pendientes_preguntas(self, ctx: dict, fields: dict) -> dict[str, PliegoFieldResult]:
        pendientes: list[dict] = []
        # From checklist incomplete
        for item in ctx.get("checklist") or []:
            status = (item.get("status") or item.get("estado") or "").lower()
            if status in ("pending", "pendiente", "faltante", "incomplete", "incompleto", ""):
                if item.get("mandatory") is False:
                    continue
                req = item.get("requirement") or item.get("label")
                if not req:
                    continue
                pendientes.append({
                    "descripcion": f"Completar: {req}",
                    "prioridad": "alta" if item.get("mandatory", True) else "media",
                    "fecha": None,
                    "responsable_sugerido": "Operaciones / Licitaciones",
                    "fuente": "checklist",
                    "accion": f"Gestionar documento o requisito «{req}»",
                })
        for miss in ctx["hermes_meta"].get("missing_documents") or []:
            pendientes.append({
                "descripcion": f"Documento faltante: {miss}",
                "prioridad": "alta",
                "fecha": None,
                "responsable_sugerido": "Documentación",
                "fuente": "hermes",
                "accion": f"Obtener o generar «{miss}»",
            })

        # Unfound critical fields become pendientes
        for key in ("fecha_limite", "garantias", "documentos_solicitados", "criterios_evaluacion"):
            f = fields.get(key)
            if f and not f.found:
                pendientes.append({
                    "descripcion": f"Confirmar manualmente: {FIELD_LABELS[key]}",
                    "prioridad": "media",
                    "fecha": None,
                    "responsable_sugerido": "Analista",
                    "fuente": "pliego_analysis",
                    "accion": f"Revisar pliego para localizar «{FIELD_LABELS[key]}»",
                })

        preguntas: list[str] = []
        for key, f in fields.items():
            if f and not f.found and key in (
                "condiciones_pago", "garantias", "visita_tecnica", "muestras_requeridas", "plazo_entrega"
            ):
                preguntas.append(
                    f"¿Pueden confirmar {FIELD_LABELS[key].lower()} aplicable a este proceso?"
                )
        if not preguntas:
            preguntas.append(
                "¿Existen enmiendas o circulares vigentes no publicadas en el portal?"
            )

        return {
            "pendientes": PliegoFieldResult(
                key="pendientes",
                value=f"{len(pendientes)} pendiente(s)" if pendientes else "No identificado",
                items=pendientes[:40],
                found=bool(pendientes),
                confidence=0.7 if pendientes else 0.25,
                review_required=True,
            ),
            "preguntas_institucion": PliegoFieldResult(
                key="preguntas_institucion",
                value=f"{len(preguntas)} pregunta(s)",
                items=preguntas,
                found=bool(preguntas),
                confidence=0.6,
                review_required=True,
            ),
        }

    def _fill_recomendaciones_decision(self, ctx: dict, fields: dict) -> dict[str, PliegoFieldResult]:
        hermes = ctx["hermes_meta"]
        opp: DGCPOpportunity = ctx["opportunity"]
        actions = list(hermes.get("next_actions") or [])
        # Specific, evidence-based recommendations
        recs: list[dict] = []
        for a in actions:
            if not str(a).strip():
                continue
            recs.append({
                "accion": str(a).strip(),
                "prioridad": "alta",
                "base": "hermes",
                "relacion": opp.code,
            })
        docs_field = fields.get("documentos_solicitados")
        if docs_field and docs_field.items:
            pending_docs = [d for d in docs_field.items if d.get("estado") == "pendiente"]
            if pending_docs:
                recs.append({
                    "accion": f"Priorizar {min(5, len(pending_docs))} documento(s) obligatorios del pliego antes del cierre",
                    "prioridad": "alta",
                    "base": "documentos_solicitados",
                    "relacion": opp.code,
                })
        if opp.deadline:
            days = (opp.deadline - datetime.now(timezone.utc).date()).days
            if days <= 10:
                recs.append({
                    "accion": f"Acelerar preparación: quedan {days} día(s) hasta la fecha límite",
                    "prioridad": "critica",
                    "base": "fecha_limite",
                    "relacion": opp.code,
                })
        if not recs:
            recs.append({
                "accion": "Revisar evidencias de requisitos críticos y validar checklist antes de ofertar",
                "prioridad": "media",
                "base": "default",
                "relacion": opp.code,
            })

        # Decision
        positives: list[str] = []
        negatives: list[str] = []
        if docs_field and docs_field.found:
            positives.append(f"Se identificaron {len(docs_field.items)} documentos/requisitos del pliego")
        if fields.get("objeto_contratacion") and fields["objeto_contratacion"].found:
            positives.append("Objeto de contratación identificado")
        risks_f = fields.get("riesgos")
        if risks_f and risks_f.items:
            high = [r for r in risks_f.items if str(r.get("severidad", "")).lower() in ("alto", "alta", "critica", "crítico")]
            if high:
                negatives.append(f"{len(high)} riesgo(s) de severidad alta")
            else:
                negatives.append(f"{len(risks_f.items)} riesgo(s) identificados para mitigar")
        if fields.get("fecha_limite") and not fields["fecha_limite"].found:
            negatives.append("Fecha límite no confirmada en documentos")

        decision = "revisar"
        if len(negatives) >= 3:
            decision = "no_participar"
        elif positives and len(negatives) <= 1:
            decision = "participar"
        hermes_rec = (hermes.get("recommendation") or "").lower()
        if hermes_rec in ("participar", "go", "si", "sí"):
            decision = "participar"
        elif hermes_rec in ("no_participar", "no", "descartar"):
            decision = "no_participar"
        elif hermes_rec in ("revisar", "review"):
            decision = "revisar"

        conf = float(hermes.get("confidence") or 0.5)
        if not ctx.get("corpus"):
            conf = min(conf, 0.35)
            decision = "revisar"
            negatives.append("Sin corpus de pliego suficiente")

        decision_obj = PliegoDecisionSuggested(
            decision=decision,  # type: ignore[arg-type]
            reason=(
                f"Evaluación automática del proceso {opp.code}: "
                f"{len(positives)} factor(es) positivo(s), {len(negatives)} negativo(s)."
            ),
            positive_factors=positives,
            negative_factors=negatives,
            main_risks=[str(r.get("descripcion") or r.get("impacto") or "") for r in (risks_f.items if risks_f else [])][:5],
            critical_pendientes=[
                p.get("descripcion", "") for p in (fields.get("pendientes").items if fields.get("pendientes") else [])
                if p.get("prioridad") in ("alta", "critica")
            ][:5],
            confidence=conf,
            evidence=self._find_evidence(ctx, keywords=["objeto", "plazo"], prefer_roles=("pliego",)),
            irreversible=False,
        )

        return {
            "recomendaciones": PliegoFieldResult(
                key="recomendaciones",
                value=f"{len(recs)} recomendación(es)",
                items=recs,
                found=bool(recs),
                confidence=0.65,
                review_required=True,
                notes="Recomendaciones accionables; no sustituyen criterio humano.",
            ),
            "decision_sugerida": PliegoFieldResult(
                key="decision_sugerida",
                value=decision_obj.decision,
                items=[decision_obj.model_dump()],
                found=True,
                confidence=conf,
                evidence=decision_obj.evidence,
                review_required=True,
                notes="Sugerencia no irreversible. Requiere validación humana.",
            ),
            "nivel_confianza": PliegoFieldResult(
                key="nivel_confianza",
                value=round(conf, 3),
                items=[{
                    "overall": conf,
                    "llm_enriched": bool(hermes.get("status") == "completed"),
                    "documents_with_text": sum(1 for d in ctx["docs"] if d.extracted_text_present),
                    "documents_total": len(ctx["docs"]),
                }],
                found=True,
                confidence=conf,
                review_required=conf < 0.6,
            ),
        }

    # ── LLM ─────────────────────────────────────────────────────────────

    async def _llm_enrich_stages(
        self, ctx: dict, fields: dict[str, PliegoFieldResult]
    ) -> tuple[dict[str, PliegoFieldResult], dict[str, Any]]:
        meta: dict[str, Any] = {"ok": False, "message": ""}
        try:
            from app.services.hermes_client import HermesClient
        except Exception:
            meta["message"] = "HermesClient no disponible"
            return {}, meta

        client = HermesClient()
        if not client.is_available():
            meta["message"] = "Hermes no disponible"
            return {}, meta

        corpus = (ctx.get("corpus") or "")[:MAX_CORPUS_FOR_LLM]
        if len(corpus.strip()) < 80:
            meta["message"] = "Corpus insuficiente para LLM"
            return {}, meta

        opp: DGCPOpportunity = ctx["opportunity"]
        doc_index = [
            {"document_id": d.document_id, "name": d.name, "type": d.doc_type, "pages": d.pages}
            for d in ctx["docs"] if not d.duplicate_of
        ]
        question = {
            "task": "Completar campos de análisis de pliego DGCP",
            "process_code": opp.code,
            "title": opp.title,
            "institution": opp.institution,
            "documents": doc_index,
            "existing_found_keys": [k for k, v in fields.items() if v.found],
            "fields_needed": list(PLIEGO_FIELD_KEYS),
            "output_schema": {
                "fields": {
                    "<key>": {
                        "value": "...",
                        "items": [],
                        "found": True,
                        "confidence": 0.0,
                        "evidence": [{
                            "document_id": "...",
                            "document_name": "...",
                            "page": 1,
                            "section": "...",
                            "fragment": "...",
                            "confidence": 0.0,
                        }],
                        "notes": "",
                    }
                }
            },
            "documents_text": corpus,
        }
        last_err = None
        raw = None
        for attempt in range(MAX_LLM_RETRIES + 1):
            try:
                raw = await client.chat(
                    system_prompt=SYSTEM_PROMPT,
                    messages=[{"role": "user", "content": json.dumps(question, ensure_ascii=False)[:110_000]}],
                    temperature=0.1,
                )
                if raw:
                    break
            except Exception as exc:
                last_err = str(exc)
                logger.warning("pliego LLM attempt %s failed: %s", attempt, exc)
        if not raw:
            meta["message"] = "LLM sin respuesta"
            meta["error"] = last_err
            return {}, meta

        content = ""
        if isinstance(raw, dict):
            content = (
                raw.get("content")
                or raw.get("message")
                or raw.get("text")
                or (raw.get("choices") or [{}])[0].get("message", {}).get("content")
                or ""
            )
            if not content and "fields" in raw:
                content = json.dumps(raw)
            meta["model"] = raw.get("model") or (raw.get("metadata") or {}).get("model")
            usage = raw.get("usage") or {}
            meta["tokens_in"] = usage.get("prompt_tokens") or usage.get("input_tokens")
            meta["tokens_out"] = usage.get("completion_tokens") or usage.get("output_tokens")

        parsed = self._extract_json(content if isinstance(content, str) else json.dumps(content))
        if not parsed or "fields" not in parsed:
            meta["message"] = "LLM no devolvió fields JSON"
            return {}, meta

        valid_doc_ids = {d.document_id for d in ctx["docs"]}
        page_max = {
            d.document_id: d.pages or 10_000 for d in ctx["docs"]
        }
        out: dict[str, PliegoFieldResult] = {}
        for key, payload in (parsed.get("fields") or {}).items():
            if key not in PLIEGO_FIELD_KEYS or not isinstance(payload, dict):
                continue
            evidence = []
            for e in payload.get("evidence") or []:
                if not isinstance(e, dict):
                    continue
                doc_id = e.get("document_id")
                page = e.get("page")
                page_ok = True
                if doc_id and doc_id not in valid_doc_ids:
                    doc_id = None
                    page_ok = False
                if page is not None:
                    try:
                        page = int(page)
                    except Exception:
                        page = None
                        page_ok = False
                    if page is not None and doc_id and page > (page_max.get(doc_id) or 10_000):
                        page = None
                        page_ok = False
                evidence.append(PliegoEvidence(
                    document_id=doc_id,
                    document_name=str(e.get("document_name") or ""),
                    page=page,
                    section=e.get("section"),
                    fragment=_short(e.get("fragment")),
                    confidence=float(e.get("confidence") or 0.5),
                    page_identified=page_ok and page is not None,
                    review_required=not (page_ok and page is not None),
                ))
            found = bool(payload.get("found"))
            value = payload.get("value", "No identificado")
            items = payload.get("items") or []
            out[key] = PliegoFieldResult(
                key=key,
                value=value if found else "No identificado",
                items=items if isinstance(items, list) else [],
                found=found,
                confidence=float(payload.get("confidence") or (0.6 if found else 0.2)),
                evidence=evidence,
                source_documents=list({
                    e.document_name for e in evidence if e.document_name
                }),
                review_required=not found or any(e.review_required for e in evidence),
                notes=str(payload.get("notes") or "")[:500],
            )
        meta["ok"] = True
        meta["message"] = f"LLM enriqueció {len(out)} campo(s)"
        return out, meta

    # ── consolidación / validación ──────────────────────────────────────

    def _consolidate(
        self,
        fields: dict[str, PliegoFieldResult],
        *,
        segments: list[dict],
        docs: list[PliegoDocumentInput],
        opportunity: DGCPOpportunity,
    ) -> tuple[dict[str, PliegoFieldResult], list[str], list[str]]:
        contradictions: list[str] = []
        validation_errors: list[str] = []
        doc_ids = {d.document_id for d in docs}
        page_max = {d.document_id: d.pages or 1 for d in docs}

        # Dedup documentos_solicitados
        docs_field = fields.get("documentos_solicitados")
        if docs_field and docs_field.items:
            seen: dict[str, dict] = {}
            for item in docs_field.items:
                if not isinstance(item, dict):
                    continue
                key = self._normalize_doc_name(str(item.get("nombre") or "")).lower()
                if not key:
                    continue
                if key in seen:
                    # keep richer
                    if len(json.dumps(item, default=str)) > len(json.dumps(seen[key], default=str)):
                        seen[key] = item
                else:
                    seen[key] = item
            docs_field.items = list(seen.values())
            docs_field.value = f"{len(docs_field.items)} documento(s)"
            docs_field.found = bool(docs_field.items)
            fields["documentos_solicitados"] = docs_field

        # Validate evidence pages / document ownership
        for key, field in fields.items():
            cleaned = []
            for ev in field.evidence:
                if ev.document_id and ev.document_id not in doc_ids:
                    validation_errors.append(f"{key}: evidencia de documento desconocido")
                    ev = ev.model_copy(update={
                        "document_id": None,
                        "review_required": True,
                        "confidence": min(ev.confidence, 0.4),
                    })
                if ev.page is not None and ev.document_id:
                    mx = page_max.get(ev.document_id)
                    if mx and ev.page > mx:
                        validation_errors.append(f"{key}: página {ev.page} inválida (max {mx})")
                        ev = ev.model_copy(update={
                            "page": None,
                            "page_identified": False,
                            "review_required": True,
                            "confidence": min(ev.confidence, 0.4),
                        })
                cleaned.append(ev)
            field.evidence = cleaned
            if field.found and not field.evidence and key not in ("nivel_confianza", "decision_sugerida", "pendientes", "preguntas_institucion", "recomendaciones"):
                field.notes = (field.notes + " Sin evidencia de página; revisión manual.").strip()
                field.review_required = True
                field.confidence = min(field.confidence, 0.5)
            fields[key] = field

        # Contradictions: amount vs text, deadline vs opportunity
        monto = fields.get("monto_estimado")
        if monto and monto.found and opportunity.amount is not None:
            try:
                digits = re.sub(r"[^\d.]", "", str(monto.value))
                if digits and abs(float(digits) - float(opportunity.amount)) / max(float(opportunity.amount), 1) > 0.25:
                    contradictions.append("Monto del análisis difiere >25% del monto registrado en la oportunidad")
                    monto.notes = (monto.notes + " Posible contradicción con ficha DGCP.").strip()
                    monto.review_required = True
                    fields["monto_estimado"] = monto
            except Exception:
                pass

        fecha = fields.get("fecha_limite")
        if fecha and fecha.found and opportunity.deadline:
            if str(opportunity.deadline) not in str(fecha.value):
                # soft contradiction only if both look like dates and differ
                if re.search(r"\d{4}", str(fecha.value)):
                    contradictions.append("Fecha límite del análisis no coincide exactamente con la ficha")
                    fecha.review_required = True
                    fields["fecha_limite"] = fecha

        # Ensure pendientes for unfound
        pend = fields.get("pendientes") or self._not_found("pendientes")
        items = list(pend.items or [])
        existing_desc = {str(i.get("descripcion", "")).lower() for i in items if isinstance(i, dict)}
        for key, field in fields.items():
            if not field.found and key not in ("pendientes", "preguntas_institucion", "nivel_confianza"):
                desc = f"Confirmar: {FIELD_LABELS.get(key, key)}"
                if desc.lower() not in existing_desc:
                    items.append({
                        "descripcion": desc,
                        "prioridad": "baja",
                        "fecha": None,
                        "responsable_sugerido": "Analista",
                        "fuente": "consolidacion",
                        "accion": f"Localizar {FIELD_LABELS.get(key, key)} en el expediente",
                    })
        pend.items = items
        pend.found = bool(items)
        pend.value = f"{len(items)} pendiente(s)" if items else "No identificado"
        fields["pendientes"] = pend

        # All 29 must exist
        for key in PLIEGO_FIELD_KEYS:
            if key not in fields:
                fields[key] = self._not_found(key)
                validation_errors.append(f"Campo omitido y rellenado: {key}")

        return fields, contradictions, validation_errors

    # ── helpers ─────────────────────────────────────────────────────────

    def _not_found(self, key: str, notes: str = "") -> PliegoFieldResult:
        return PliegoFieldResult(
            key=key,
            label=FIELD_LABELS.get(key, key),
            value="No identificado",
            found=False,
            confidence=0.15,
            review_required=True,
            notes=notes or "No identificado en el corpus analizado.",
        )

    def _scalar_field(
        self,
        key: str,
        value: Any,
        *,
        evidence: list[PliegoEvidence] | None = None,
        source_hint: str | None = None,
    ) -> PliegoFieldResult:
        found = value not in (None, "", [], {}, "None")
        ev = evidence or []
        return PliegoFieldResult(
            key=key,
            value=value if found else "No identificado",
            found=found,
            confidence=0.8 if found and ev else (0.55 if found else 0.2),
            evidence=ev[:5],
            source_documents=list({e.document_name for e in ev if e.document_name})
            or ([source_hint] if source_hint and found else []),
            review_required=not found or any(not e.page_identified for e in ev),
        )

    def _list_from_extraction(
        self, key: str, extraction: Any, bucket: str, ctx: dict
    ) -> PliegoFieldResult:
        items: list[Any] = []
        evidence: list[PliegoEvidence] = []
        if extraction:
            for item in getattr(extraction, bucket, None) or []:
                label = getattr(item, "label", None) or getattr(item, "key", None)
                if not label:
                    continue
                items.append({
                    "key": getattr(item, "key", None),
                    "label": label,
                    "mandatory": getattr(item, "mandatory", True),
                    "source": getattr(item, "source", None),
                })
                for e in getattr(item, "evidence", None) or []:
                    evidence.append(PliegoEvidence(
                        document_id=getattr(e, "process_document_id", None),
                        document_name=getattr(e, "documento_origen", "") or "",
                        page=getattr(e, "pagina", None),
                        section=getattr(e, "seccion", None),
                        fragment=_short(getattr(e, "fragmento", None)),
                        confidence=0.7,
                        page_identified=getattr(e, "pagina", None) is not None,
                    ))
        if not items:
            return self._items_from_keywords(key, ctx, keywords=[key.replace("_", " ")])
        return PliegoFieldResult(
            key=key,
            value=f"{len(items)} ítem(s)",
            items=items,
            found=True,
            confidence=0.7,
            evidence=evidence[:8],
            source_documents=list({e.document_name for e in evidence if e.document_name}),
            review_required=any(not e.page_identified for e in evidence) or not evidence,
        )

    def _items_from_keywords(
        self, key: str, ctx: dict, *, keywords: list[str]
    ) -> PliegoFieldResult:
        hits: list[dict] = []
        evidence = self._find_evidence(ctx, keywords=keywords, limit=6)
        for ev in evidence:
            hits.append({
                "texto": ev.fragment,
                "pagina": ev.page,
                "documento": ev.document_name,
                "seccion": ev.section,
            })
        # Also pull from evidence_index
        for kw in keywords:
            for ev in ctx.get("evidence_index", {}).get(kw.lower(), [])[:2]:
                if ev not in evidence:
                    evidence.append(ev)
        found = bool(hits or evidence)
        return PliegoFieldResult(
            key=key,
            value=f"{len(hits)} hallazgo(s)" if hits else ("No identificado"),
            items=hits,
            found=found and bool(hits),
            confidence=0.6 if hits else 0.2,
            evidence=evidence[:8],
            source_documents=list({e.document_name for e in evidence if e.document_name}),
            review_required=not hits,
            notes="" if hits else "No identificado en el corpus; revisión manual.",
        )

    def _find_evidence(
        self,
        ctx: dict,
        *,
        keywords: list[str],
        prefer_roles: tuple[str, ...] = (),
        limit: int = 4,
    ) -> list[PliegoEvidence]:
        kws = [k.lower() for k in keywords if k and str(k).strip()]
        if not kws:
            return []
        scored: list[tuple[float, PliegoEvidence]] = []
        role_bonus_docs = {
            d.document_id for d in ctx.get("docs") or []
            if d.doc_type in prefer_roles
        }
        for seg in ctx.get("segments") or []:
            text_l = (seg.get("text") or "").lower()
            if not any(k in text_l for k in kws if len(k) > 2):
                continue
            # locate fragment around first keyword
            frag = ""
            for k in kws:
                idx = text_l.find(k)
                if idx >= 0:
                    start = max(0, idx - 60)
                    frag = _short(seg["text"][start : start + 200])
                    break
            if not frag:
                frag = _short(seg.get("text"))
            conf = 0.55
            if seg.get("page_identified"):
                conf += 0.15
            if seg.get("document_id") in role_bonus_docs:
                conf += 0.1
            scored.append((conf, PliegoEvidence(
                document_id=seg.get("document_id"),
                document_name=seg.get("document_name") or "",
                page=seg.get("page"),
                section=seg.get("section"),
                fragment=frag,
                confidence=min(conf, 0.95),
                page_identified=bool(seg.get("page_identified")),
                review_required=not bool(seg.get("page_identified")),
            )))
        scored.sort(key=lambda x: x[0], reverse=True)
        # unique by doc+page
        seen = set()
        out: list[PliegoEvidence] = []
        for _, ev in scored:
            mark = (ev.document_id, ev.page, ev.fragment[:40])
            if mark in seen:
                continue
            seen.add(mark)
            out.append(ev)
            if len(out) >= limit:
                break
        return out

    def _index_evidence(
        self, records: list[dict], docs: list[DGCPProcessDocument]
    ) -> dict[str, list[PliegoEvidence]]:
        by_kw: dict[str, list[PliegoEvidence]] = {}
        title_by_id = {str(d.id): d.title for d in docs}
        for rec in records:
            key = (rec.get("requirement_key") or "").lower()
            ev = PliegoEvidence(
                document_id=rec.get("process_document_id"),
                document_name=rec.get("documento_origen") or title_by_id.get(str(rec.get("process_document_id") or ""), ""),
                page=rec.get("pagina"),
                section=rec.get("seccion"),
                fragment=_short(rec.get("fragmento")),
                confidence=0.7 if rec.get("confianza") == "alta" else 0.5,
                page_identified=rec.get("pagina") is not None,
            )
            by_kw.setdefault(key, []).append(ev)
        return by_kw

    def _guess_section(self, text: str) -> str | None:
        head = (text or "")[:400]
        m = re.search(
            r"(?im)^(?:artículo|art\.|sección|capitulo|capítulo|anexo|cláusula)\s+[\w.\-]+.*$",
            head,
        )
        if m:
            return _short(m.group(0), 80)
        first = head.strip().split("\n", 1)[0].strip()
        return _short(first, 80) if first else None

    def _normalize_doc_name(self, name: str) -> str:
        n = re.sub(r"\s+", " ", name or "").strip()
        n = re.sub(r"^(copia de|documento|archivo)\s+", "", n, flags=re.I)
        return n[:200]

    def _merge_field(
        self, base: PliegoFieldResult | None, overlay: PliegoFieldResult
    ) -> PliegoFieldResult:
        if not base:
            return overlay
        if base.manual_override:
            return base
        if overlay.found and (not base.found or overlay.confidence >= base.confidence):
            # keep base evidence if overlay lacks pages
            if not overlay.evidence and base.evidence:
                overlay.evidence = base.evidence
            if base.items and not overlay.items:
                overlay.items = base.items
            return overlay
        if base.found:
            return base
        return overlay

    def _decision_from_field(self, field: PliegoFieldResult | None) -> PliegoDecisionSuggested | None:
        if not field or not field.items:
            return None
        raw = field.items[0]
        if isinstance(raw, dict):
            try:
                return PliegoDecisionSuggested.model_validate(raw)
            except Exception:
                pass
        return PliegoDecisionSuggested(
            decision=str(field.value) if field.value in ("participar", "revisar", "no_participar") else "revisar",
            reason=field.notes or "",
            confidence=field.confidence,
        )

    @staticmethod
    def _extract_json(text: str) -> dict | None:
        if not text:
            return None
        text = text.strip()
        try:
            return json.loads(text)
        except Exception:
            pass
        m = re.search(r"\{[\s\S]*\}", text)
        if not m:
            return None
        try:
            return json.loads(m.group(0))
        except Exception:
            return None

    async def _get_package(self, opportunity_id: uuid.UUID) -> DGCPBidPackage | None:
        from sqlalchemy import select

        result = await self.db.execute(
            select(DGCPBidPackage).where(
                DGCPBidPackage.tenant_id == self.tenant_id,
                DGCPBidPackage.opportunity_id == opportunity_id,
            )
        )
        return result.scalar_one_or_none()

    async def _persist(
        self,
        opportunity_id: uuid.UUID,
        result: PliegoAnalysisResult,
        *,
        bump_version: bool = True,
    ) -> None:
        pkg = await self._get_package(opportunity_id)
        if not pkg:
            pkg = DGCPBidPackage(tenant_id=self.tenant_id, opportunity_id=opportunity_id)
            self.db.add(pkg)
            await self.db.flush()

        manifest = dict(pkg.manifest or {})
        payload = result.model_dump(mode="json")
        versions = list(manifest.get("pliego_analysis_versions") or [])
        if bump_version:
            versions.append({
                "version": result.version,
                "status": result.status.value if hasattr(result.status, "value") else result.status,
                "created_at": (result.created_at or _now()).isoformat(),
                "prompt_hash": result.meta.prompt_hash,
                "model": result.meta.model,
                "document_hashes": result.meta.document_hashes,
                "duration_ms": result.meta.duration_ms,
                "user_id": result.meta.user_id,
                "snapshot": payload,
            })
            # keep last 10 full snapshots
            versions = versions[-10:]
        manifest["pliego_analysis"] = payload
        manifest["pliego_analysis_versions"] = versions
        pkg.manifest = manifest
        await self.db.flush()
