"""DGCP Smart Matching — cruza requisitos con Corporate Knowledge + Documents (Fase 7.2/7.3)."""

from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document
from app.models.knowledge import KnowledgeAsset
from app.services.dgcp_document_matcher import DOC_TYPE_ALIASES, DGCPDocumentMatcher
from app.services.dgcp_compliance_engine import DELIVERABLE_REQUIREMENT_KEYS, OFFICIAL_KNOWLEDGE_FOLDERS
from app.services.document_extraction_service import DocumentExtractionService
from app.services.document_validity_analyzer import DocumentValidityAnalyzer
from app.services.knowledge_source_provider import get_knowledge_source_provider

REQ_TO_DOC_TYPE: dict[str, str] = {
    "rpe": "rpe",
    "certificacion_tss": "tss",
    "certificacion_dgii": "dgii",
    "registro_mercantil": "registro_mercantil",
    "certificacion_mipyme": "mipyme",
    "sncc_f033": "sncc_f033",
    "sncc_f034": "sncc_f042",
    "sncc_f042": "sncc_f042",
    "sncc_f047": "sncc_f047",
    "oferta_economica": "oferta_economica",
    "oferta_tecnica": "oferta_tecnica",
    "autorizacion_fabricante": "certificacion_fabricante",
    "ficha_tecnica": "ficha_tecnica",
    "carta_fabricante": "carta",
}


class DGCPSmartMatchingEngine:
    def __init__(self, db: AsyncSession, tenant_id: uuid.UUID, *, company_key: str = "justech"):
        self.db = db
        self.tenant_id = tenant_id
        self.company_key = company_key
        self.legacy_matcher = DGCPDocumentMatcher(db, tenant_id)
        self.validity_analyzer = DocumentValidityAnalyzer()
        self.extractor = DocumentExtractionService()
        self.source = get_knowledge_source_provider()

    async def match_all(self, requirements: list[ExtractedRequirement]) -> list[dict]:
        knowledge_assets = await self._load_knowledge_assets()
        documents = await self.legacy_matcher.load_documents()
        matches: list[dict] = []

        for req in requirements:
            match = await self._match_requirement(req, knowledge_assets, documents)
            matches.append(match)
        return matches

    async def _load_knowledge_assets(self) -> list[KnowledgeAsset]:
        result = await self.db.execute(
            select(KnowledgeAsset).where(
                KnowledgeAsset.tenant_id == self.tenant_id,
                KnowledgeAsset.is_active.is_(True),
                KnowledgeAsset.folder_category.in_(tuple(OFFICIAL_KNOWLEDGE_FOLDERS)),
            )
        )
        return list(result.scalars().all())

    async def _match_requirement(
        self,
        req: ExtractedRequirement,
        assets: list[KnowledgeAsset],
        documents: list[Document],
    ) -> dict:
        doc_type = REQ_TO_DOC_TYPE.get(req.key, req.key)

        if req.key in DELIVERABLE_REQUIREMENT_KEYS:
            template = self._find_template(doc_type, assets)
            if template:
                return {
                    "requirement_key": req.key,
                    "requirement_label": req.label,
                    "document_id": None,
                    "document_title": template.title,
                    "knowledge_asset_id": str(template.id),
                    "match_source": "knowledge_template",
                    "match_score": 75.0,
                    "status": "requiere_completado",
                    "valid_until": None,
                    "vigency_status": "no_aplica_vigencia",
                    "relative_path": template.relative_path,
                    "notes": f"Plantilla base — completar entregable: {req.label}",
                }
            return {
                "requirement_key": req.key,
                "requirement_label": req.label,
                "document_id": None,
                "document_title": None,
                "knowledge_asset_id": None,
                "match_source": None,
                "match_score": 0.0,
                "status": "faltante",
                "valid_until": None,
                "vigency_status": None,
                "relative_path": None,
                "notes": f"Entregable pendiente — subir o completar: {req.label}",
            }

        best_asset = self._best_knowledge_asset(doc_type, assets, req)
        if best_asset:
            text, content, pages = await self._asset_content(best_asset)
            status, valid_until, vigency_status, note, analysis = self._resolve_found_document(
                req,
                text=text,
                title=best_asset.title,
                filename=best_asset.filename,
                content=content,
                pages=pages,
                is_template=best_asset.folder_category.startswith("02_") or req.key.startswith("sncc_"),
                document_id=None,
            )
            return {
                "requirement_key": req.key,
                "requirement_label": req.label,
                "document_id": None,
                "document_title": best_asset.title,
                "knowledge_asset_id": str(best_asset.id),
                "match_source": "knowledge_repository",
                "match_score": 92.0,
                "status": status,
                "valid_until": valid_until.isoformat() if valid_until else None,
                "vigency_status": vigency_status,
                "relative_path": best_asset.relative_path,
                "notes": note or self._status_note(status, req, source="knowledge"),
                "validity_analysis": analysis.to_dict(),
            }

        doc, score, raw_status = self.legacy_matcher.match_requirement(req, documents)
        if doc:
            text = doc.extracted_text or ""
            content = await self._document_bytes(doc)
            status, valid_until, vigency_status, note, analysis = self._resolve_found_document(
                req,
                text=text,
                title=doc.title,
                filename=doc.filename,
                content=content,
                pages=None,
                is_template=req.key.startswith("sncc_"),
                fallback_status=raw_status,
                document_id=str(doc.id),
            )
            return {
                "requirement_key": req.key,
                "requirement_label": req.label,
                "document_id": str(doc.id),
                "document_title": doc.title,
                "knowledge_asset_id": None,
                "match_source": "document_repository",
                "match_score": score,
                "status": status,
                "valid_until": valid_until.isoformat() if valid_until else None,
                "vigency_status": vigency_status,
                "relative_path": None,
                "notes": note or self._status_note(status, req, source="documents"),
                "validity_analysis": analysis.to_dict(),
            }

        template = self._find_template(doc_type, assets)
        if template:
            return {
                "requirement_key": req.key,
                "requirement_label": req.label,
                "document_id": None,
                "document_title": template.title,
                "knowledge_asset_id": str(template.id),
                "match_source": "knowledge_template",
                "match_score": 75.0,
                "status": "requiere_completado",
                "valid_until": None,
                "vigency_status": "no_aplica_vigencia",
                "relative_path": template.relative_path,
                "notes": f"Plantilla encontrada — requiere completado: {template.relative_path}",
            }

        return {
            "requirement_key": req.key,
            "requirement_label": req.label,
            "document_id": None,
            "document_title": None,
            "knowledge_asset_id": None,
            "match_source": None,
            "match_score": 0.0,
            "status": "faltante",
            "valid_until": None,
            "vigency_status": None,
            "relative_path": None,
            "notes": f"Solicitar o registrar: {req.label}",
        }

    async def _asset_content(self, asset: KnowledgeAsset) -> tuple[str, bytes | None, list[str]]:
        text = (asset.extracted_text or "").strip()
        content: bytes | None = None
        pages: list[str] = []
        if self.source.is_available() and asset.relative_path:
            try:
                content = self.source.read_bytes(asset.relative_path)
                if not text and content:
                    extraction = self.extractor.extract(content, filename=asset.filename)
                    text = (extraction.text or "").strip()
                    pages = extraction.pages or []
            except Exception:
                content = None
        return text, content, pages

    async def _document_bytes(self, doc: Document) -> bytes | None:
        if not doc.storage_path:
            return None
        try:
            from pathlib import Path

            path = Path(doc.storage_path)
            if path.is_file():
                return path.read_bytes()
        except Exception:
            return None
        return None

    def _resolve_found_document(
        self,
        req: ExtractedRequirement,
        *,
        text: str,
        title: str,
        filename: str,
        content: bytes | None,
        pages: list[str] | None,
        is_template: bool,
        fallback_status: str | None = None,
        document_id: str | None = None,
    ) -> tuple[str, date | None, str, str | None, object]:
        if is_template or req.key.startswith("sncc_"):
            from app.services.document_validity_analyzer import DocumentValidityResult

            return (
                "requiere_completado",
                None,
                "no_aplica_vigencia",
                "Plantilla / formulario — requiere completado",
                DocumentValidityResult(document_name=title or filename, document_type=req.key),
            )

        if fallback_status == "incompleto":
            from app.services.document_validity_analyzer import DocumentValidityResult

            return (
                "requiere_completado",
                None,
                "no_aplica_vigencia",
                "Documento incompleto — revisar campos",
                DocumentValidityResult(document_name=title or filename, document_type=req.key),
            )

        status, valid_until, vigency_status, note, analysis = self.validity_analyzer.resolve_requirement_match(
            req.key,
            text=text,
            title=title,
            filename=filename,
            content=content if not text else None,
            document_id=document_id,
        )
        if pages and analysis.evidence_page is None and analysis.evidence_text:
            analysis.evidence_page = self.validity_analyzer._page_for_phrase(pages, analysis.evidence_text)
        return status, valid_until, vigency_status, note, analysis

    def _best_knowledge_asset(
        self,
        doc_type: str,
        assets: list[KnowledgeAsset],
        req: ExtractedRequirement,
    ) -> KnowledgeAsset | None:
        aliases = DOC_TYPE_ALIASES.get(req.key, (req.key.replace("_", " "),))
        candidates = [
            a for a in assets
            if a.document_type == doc_type
            or a.document_type == req.key
            or any(alias in a.filename.lower() for alias in aliases)
            or any(alias in (a.title or "").lower() for alias in aliases)
        ]
        if self.company_key:
            company_matches = [a for a in candidates if a.company_key == self.company_key]
            if company_matches:
                candidates = company_matches
        if not candidates:
            return None

        if self.validity_analyzer.requires_vigency_check(req.key):
            candidates.sort(key=lambda a: (a.analyzed_at or a.synced_at), reverse=True)
        else:
            candidates.sort(key=lambda a: a.filename)
        return candidates[0]

    @staticmethod
    def _find_template(doc_type: str, assets: list[KnowledgeAsset]) -> KnowledgeAsset | None:
        for asset in assets:
            if not asset.folder_category.startswith("02_"):
                continue
            if doc_type in asset.document_type or doc_type.replace("_", " ") in asset.filename.lower():
                return asset
        return None

    @staticmethod
    def _status_note(status: str, req: ExtractedRequirement, *, source: str) -> str | None:
        prefix = "Repositorio corporativo" if source == "knowledge" else "Repositorio documental"
        notes = {
            "faltante": f"Solicitar o registrar: {req.label}",
            "encontrado_vencido": f"Renovar documento: {req.label}",
            "requiere_completado": f"{prefix}: completar {req.label}",
            "requiere_revision": f"{prefix}: validar vigencia de {req.label}",
            "encontrado_sin_fecha": f"{prefix}: {req.label} encontrado — vigencia no verificada",
            "encontrado_sin_analizar": f"{prefix}: {req.label} encontrado — contenido pendiente de análisis",
            "encontrado_vigente": f"{prefix}: {req.label} — documento leído y vigente",
            "plantilla_disponible": f"Plantilla disponible para {req.label}",
        }
        return notes.get(status)
