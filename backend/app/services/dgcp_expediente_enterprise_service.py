"""Expediente enterprise — matriz, trazabilidad, score, Q&A y previsualización."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.dgcp_bid_package import DGCPBidPackage
from app.models.dgcp_opportunity import DGCPOpportunity
from app.services.dgcp_bid_package_service import (
    REQUIREMENT_UX_STATUS_MAP,
    DGCPBidPackageService,
)


SCORE_AREAS = (
    ("documentacion", "Documentación"),
    ("experiencia", "Experiencia"),
    ("personal", "Personal"),
    ("oferta_tecnica", "Oferta técnica"),
    ("oferta_economica", "Oferta económica"),
    ("garantias", "Garantías"),
)

COMPLIANT_UX = frozenset({"Aprobado", "Completado"})


class DGCPExpedienteEnterpriseService:
    def __init__(self, db: AsyncSession, tenant_id: uuid.UUID, user_id: uuid.UUID | None = None):
        self.db = db
        self.tenant_id = tenant_id
        self.user_id = user_id
        self.bid = DGCPBidPackageService(db, tenant_id, user_id=user_id)

    async def get_compliance_matrix(self, opportunity_id: uuid.UUID) -> dict:
        opp, pkg = await self._require_pkg(opportunity_id)
        rows = self._matrix_rows(pkg)
        return {
            "opportunity_id": str(opportunity_id),
            "opportunity_code": opp.code,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "total": len(rows),
            "columns": [
                "Requisito",
                "Estado",
                "Responsable",
                "Documento asociado",
                "Cumple",
                "Riesgo",
                "Observaciones IA",
            ],
            "rows": rows,
        }

    async def export_compliance_matrix_excel(self, opportunity_id: uuid.UUID) -> tuple[bytes, str]:
        from openpyxl import Workbook

        matrix = await self.get_compliance_matrix(opportunity_id)
        wb = Workbook()
        ws = wb.active
        ws.title = "Matriz cumplimiento"
        ws.append(matrix["columns"])
        for row in matrix["rows"]:
            ws.append(
                [
                    row.get("requisito"),
                    row.get("estado"),
                    row.get("responsable"),
                    row.get("documento_asociado"),
                    row.get("cumple"),
                    row.get("riesgo"),
                    row.get("observaciones_ia"),
                ]
            )
        buf = BytesIO()
        wb.save(buf)
        code = matrix["opportunity_code"].replace("/", "_")
        return buf.getvalue(), f"matriz_cumplimiento_{code}.xlsx"

    async def export_compliance_matrix_pdf(self, opportunity_id: uuid.UUID) -> tuple[bytes, str]:
        from reportlab.lib.pagesizes import letter, landscape
        from reportlab.lib.units import inch
        from reportlab.pdfgen import canvas

        matrix = await self.get_compliance_matrix(opportunity_id)
        buf = BytesIO()
        c = canvas.Canvas(buf, pagesize=landscape(letter))
        width, height = landscape(letter)
        y = height - 0.6 * inch

        def line(text: str, *, size: int = 9, bold: bool = False) -> None:
            nonlocal y
            if y < 0.6 * inch:
                c.showPage()
                y = height - 0.6 * inch
            c.setFont("Helvetica-Bold" if bold else "Helvetica", size)
            c.drawString(0.5 * inch, y, str(text)[:140])
            y -= 12

        line(f"Matriz de cumplimiento — {matrix['opportunity_code']}", bold=True, size=12)
        line(f"Generado: {matrix['generated_at']} · Total: {matrix['total']}")
        y -= 4
        for row in matrix["rows"][:80]:
            line(
                f"• {row.get('requisito')} | {row.get('estado')} | "
                f"{row.get('cumple')} | {row.get('riesgo') or '—'}"
            )
            obs = row.get("observaciones_ia") or ""
            if obs:
                line(f"  IA: {obs[:120]}", size=8)
        c.save()
        code = matrix["opportunity_code"].replace("/", "_")
        return buf.getvalue(), f"matriz_cumplimiento_{code}.pdf"

    async def get_requirement_evidence(
        self,
        opportunity_id: uuid.UUID,
        item_id: uuid.UUID,
    ) -> dict:
        opp, pkg = await self._require_pkg(opportunity_id)
        item = self._find_item(pkg, item_id)
        evidence = self._evidence_for_item(pkg, item)
        return {
            "opportunity_id": str(opportunity_id),
            "opportunity_code": opp.code,
            "checklist_item_id": str(item_id),
            "requirement_key": item.get("requirement_key"),
            "requirement": item.get("requirement"),
            "evidencia": evidence,
            "tiene_evidencia": bool(
                evidence.get("texto_original")
                or evidence.get("documento_origen")
                or evidence.get("pagina") is not None
            ),
        }

    async def ask_requirement_ai(
        self,
        opportunity_id: uuid.UUID,
        item_id: uuid.UUID,
        question: str,
    ) -> dict:
        q = (question or "").strip()
        if not q:
            raise ValueError("Escriba una pregunta sobre el requisito")
        opp, pkg = await self._require_pkg(opportunity_id)
        item = self._find_item(pkg, item_id)
        evidence = self._evidence_for_item(pkg, item)
        enriched = self.bid._enrich_requirement_item(item)
        dash = await self.bid.get_expediente_dashboard(opportunity_id)
        score = self._compute_score(pkg)

        ctx_bits = [
            f"Proceso: {opp.code} — {opp.title}",
            f"Requisito: {item.get('requirement')} ({item.get('requirement_key')})",
            f"Estado: {enriched.get('estado')} · Cumple: {self._cumple_label(item)}",
            f"Documento asociado: {item.get('document_title') or 'ninguno'}",
            f"Responsable: {item.get('assignee') or 'sin asignar'}",
            f"Riesgo: {item.get('risk') or '—'}",
            f"Observaciones IA: {enriched.get('observaciones_ia') or '—'}",
            f"Evidencia pliego — doc: {evidence.get('documento_origen') or '—'}; "
            f"página: {evidence.get('pagina') if evidence.get('pagina') is not None else '—'}; "
            f"sección: {evidence.get('parrafo') or '—'}; "
            f"texto: «{(evidence.get('texto_original') or '')[:400]}»",
            f"Score expediente: {score['score_total']}%",
            f"Preparación: {dash.get('preparation_pct', 0)}%",
        ]
        answer = self._answer_from_context(q, item, evidence, enriched, score, dash)
        return {
            "opportunity_id": str(opportunity_id),
            "checklist_item_id": str(item_id),
            "requirement_key": item.get("requirement_key"),
            "question": q,
            "answer": answer,
            "context_used": ctx_bits,
            "sources": ["expediente", "checklist", "requirement_evidence"],
            "answered_at": datetime.now(timezone.utc).isoformat(),
        }

    async def get_expediente_score(self, opportunity_id: uuid.UUID) -> dict:
        opp, pkg = await self._require_pkg(opportunity_id)
        score = self._compute_score(pkg)
        score["opportunity_id"] = str(opportunity_id)
        score["opportunity_code"] = opp.code
        return score

    async def get_expediente_preview(self, opportunity_id: uuid.UUID) -> dict:
        opp, pkg = await self._require_pkg(opportunity_id)
        base_path = pkg.expediente_path
        files: list[dict[str, Any]] = []
        if base_path and Path(base_path).exists():
            root = Path(base_path)
            for path in sorted(root.rglob("*")):
                if not path.is_file():
                    continue
                rel = str(path.relative_to(root))
                ext = path.suffix.lower()
                kind = "other"
                if ext == ".pdf":
                    kind = "pdf"
                elif ext in (".doc", ".docx"):
                    kind = "word"
                elif ext in (".xls", ".xlsx"):
                    kind = "excel"
                elif ext == ".zip":
                    kind = "zip"
                elif ext in (".json", ".md", ".txt"):
                    kind = "text"
                files.append(
                    {
                        "path": rel,
                        "name": path.name,
                        "kind": kind,
                        "size_bytes": path.stat().st_size,
                        "preview_url": (
                            f"/api/v1/dgcp/opportunities/{opportunity_id}/expediente/preview/file"
                            f"?path={rel}"
                        ),
                    }
                )
        else:
            # Vista previa planificada (aún no preparado)
            from app.services.dgcp_expediente_service import EXPEDIENTE_FOLDERS

            for folder in EXPEDIENTE_FOLDERS:
                files.append(
                    {
                        "path": f"{folder}/",
                        "name": folder,
                        "kind": "folder",
                        "size_bytes": 0,
                        "preview_url": None,
                        "planned": True,
                    }
                )
            files.extend(
                [
                    {
                        "path": "manifest.json",
                        "name": "manifest.json",
                        "kind": "text",
                        "planned": True,
                        "preview_url": None,
                        "size_bytes": 0,
                    },
                    {
                        "path": "00_Informacion_General/indice_expediente.pdf",
                        "name": "indice_expediente (planificado)",
                        "kind": "pdf",
                        "planned": True,
                        "preview_url": None,
                        "size_bytes": 0,
                    },
                    {
                        "path": "12_Revision/reporte_estado_expediente.pdf",
                        "name": "reporte_estado_expediente.pdf",
                        "kind": "pdf",
                        "planned": True,
                        "preview_url": None,
                        "size_bytes": 0,
                    },
                    {
                        "path": "12_Revision/validaciones_ia.json",
                        "name": "validaciones_ia.json",
                        "kind": "text",
                        "planned": True,
                        "preview_url": None,
                        "size_bytes": 0,
                    },
                ]
            )

        zip_name = f"{opp.code.replace('/', '_')}_expediente.zip"
        return {
            "opportunity_id": str(opportunity_id),
            "opportunity_code": opp.code,
            "prepared": bool(base_path and Path(base_path).exists()),
            "expediente_path": base_path,
            "zip_name": zip_name,
            "zip_available": bool(base_path and (Path(base_path).parent / zip_name).exists()),
            "files": files,
            "counts": {
                "pdf": sum(1 for f in files if f.get("kind") == "pdf"),
                "word": sum(1 for f in files if f.get("kind") == "word"),
                "excel": sum(1 for f in files if f.get("kind") == "excel"),
                "zip": sum(1 for f in files if f.get("kind") == "zip"),
                "total": len(files),
            },
            "note": (
                "Estructura real del expediente preparado."
                if base_path and Path(base_path).exists()
                else "Vista previa planificada — ejecute «Preparar Expediente» para materializar archivos."
            ),
        }

    async def read_preview_file(
        self,
        opportunity_id: uuid.UUID,
        relative_path: str,
    ) -> tuple[bytes, str, str]:
        _, pkg = await self._require_pkg(opportunity_id)
        if not pkg.expediente_path:
            raise ValueError("Prepare el expediente antes de previsualizar archivos")
        root = Path(pkg.expediente_path).resolve()
        target = (root / relative_path).resolve()
        if not str(target).startswith(str(root)) or not target.is_file():
            raise ValueError("Archivo no encontrado en el expediente")
        data = target.read_bytes()
        ext = target.suffix.lower()
        mime = "application/octet-stream"
        if ext == ".pdf":
            mime = "application/pdf"
        elif ext == ".docx":
            mime = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        elif ext == ".xlsx":
            mime = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        elif ext == ".json":
            mime = "application/json"
        elif ext in (".md", ".txt"):
            mime = "text/plain; charset=utf-8"
        return data, mime, target.name

    async def _require_pkg(
        self, opportunity_id: uuid.UUID
    ) -> tuple[DGCPOpportunity, DGCPBidPackage]:
        opp = await self.bid._get_opportunity(opportunity_id)
        if not opp:
            raise ValueError("Licitación no encontrada")
        pkg = await self.bid._get_package(opportunity_id)
        if not pkg:
            raise ValueError("Ejecute el análisis de requisitos primero")
        return opp, pkg

    @staticmethod
    def _find_item(pkg: DGCPBidPackage, item_id: uuid.UUID) -> dict:
        for item in pkg.checklist or []:
            if str(item.get("id")) == str(item_id):
                return item
        raise ValueError("Requisito no encontrado en el expediente")

    def _matrix_rows(self, pkg: DGCPBidPackage) -> list[dict]:
        rows = []
        for item in pkg.checklist or []:
            enriched = self.bid._enrich_requirement_item(item)
            av = item.get("ai_validation") if isinstance(item.get("ai_validation"), dict) else {}
            cumple = self._cumple_label(item)
            rows.append(
                {
                    "id": str(item.get("id")),
                    "requirement_key": item.get("requirement_key"),
                    "requisito": item.get("requirement") or item.get("requirement_key"),
                    "estado": enriched.get("estado") or REQUIREMENT_UX_STATUS_MAP.get(
                        str(item.get("status") or "pendiente"), "Pendiente"
                    ),
                    "responsable": item.get("assignee") or "—",
                    "documento_asociado": item.get("document_title") or "—",
                    "cumple": cumple,
                    "riesgo": item.get("risk") or av.get("riesgo") or "—",
                    "observaciones_ia": enriched.get("observaciones_ia")
                    or av.get("observaciones")
                    or item.get("ia_observations")
                    or "—",
                    "source_page": item.get("source_page"),
                    "source_document": item.get("source_document"),
                }
            )
        return rows

    @staticmethod
    def _cumple_label(item: dict) -> str:
        av = item.get("ai_validation") if isinstance(item.get("ai_validation"), dict) else None
        if av and av.get("cumple") is True:
            return "Cumple"
        if av and av.get("cumple") is False:
            return "No cumple"
        status = str(item.get("status") or "")
        ux = REQUIREMENT_UX_STATUS_MAP.get(status, "")
        if status in ("cumple", "encontrado_vigente", "validado_manual", "finalizado", "pdf_final_generado"):
            return "Cumple"
        if status in ("no_cumple", "vencido", "encontrado_vencido"):
            return "No cumple"
        if ux in COMPLIANT_UX:
            return "Cumple"
        if item.get("document_title") or item.get("document_id") or item.get("knowledge_asset_id"):
            return "Parcial"
        return "Pendiente"

    def _evidence_for_item(self, pkg: DGCPBidPackage, item: dict) -> dict:
        key = str(item.get("requirement_key") or "")
        evidence_list = list(pkg.requirement_evidence or [])
        match = next(
            (e for e in evidence_list if str(e.get("requirement_key") or "") == key),
            None,
        )
        if not match:
            # fallback a campos del ítem
            return {
                "pagina": item.get("source_page"),
                "documento_origen": item.get("source_document") or item.get("match_source"),
                "parrafo": item.get("source_section"),
                "texto_original": item.get("evidence_fragment"),
                "confianza": item.get("evidence_confidence"),
                "process_document_id": item.get("process_document_id"),
            }
        return {
            "pagina": match.get("pagina"),
            "documento_origen": match.get("documento_origen"),
            "parrafo": match.get("seccion"),
            "texto_original": match.get("fragmento"),
            "confianza": match.get("confianza"),
            "process_document_id": match.get("process_document_id"),
        }

    def _compute_score(self, pkg: DGCPBidPackage) -> dict:
        checklist = list(pkg.checklist or [])
        buckets: dict[str, list[dict]] = {k: [] for k, _ in SCORE_AREAS}
        for item in checklist:
            area = self._score_area_for_item(item)
            buckets.setdefault(area, []).append(item)

        desglose = []
        gaps: list[str] = []
        values: list[float] = []
        for key, label in SCORE_AREAS:
            items = buckets.get(key) or []
            if not items:
                desglose.append(
                    {
                        "key": key,
                        "label": label,
                        "pct": None,
                        "detail": "Sin requisitos clasificados en esta área",
                    }
                )
                continue
            ok = sum(
                1
                for i in items
                if self._cumple_label(i) == "Cumple"
                or REQUIREMENT_UX_STATUS_MAP.get(str(i.get("status") or ""), "") in COMPLIANT_UX
            )
            pct = round(100.0 * ok / len(items), 1)
            values.append(pct)
            detail = f"{ok}/{len(items)} requisitos cumplidos"
            if pct < 100:
                pending = [
                    i.get("requirement") or i.get("requirement_key")
                    for i in items
                    if self._cumple_label(i) != "Cumple"
                ][:3]
                if pending:
                    gaps.append(f"{label}: faltan/pendientes — {', '.join(str(p) for p in pending)}")
            desglose.append({"key": key, "label": label, "pct": pct, "detail": detail})

        total = round(sum(values) / len(values), 1) if values else float(
            (pkg.bid_package or {}).get("preparation_pct") or 0
        )
        if total >= 100:
            why = "El score es 100%: todas las áreas evaluadas cumplen sus requisitos."
        elif not gaps:
            why = (
                f"El score es {total}% porque hay áreas sin requisitos clasificados "
                "o con cumplimiento parcial."
            )
        else:
            why = f"El score no es 100% ({total}%) porque: " + "; ".join(gaps[:6])

        return {
            "score_total": total,
            "desglose": desglose,
            "explicacion": why,
            "gaps": gaps,
            "computed_at": datetime.now(timezone.utc).isoformat(),
        }

    def _score_area_for_item(self, item: dict) -> str:
        sec = self.bid._section_for_requirement(item)
        if sec in ("experiencia",):
            return "experiencia"
        if sec in ("personal",):
            return "personal"
        if sec in ("oferta_tecnica",):
            return "oferta_tecnica"
        if sec in ("oferta_economica",):
            return "oferta_economica"
        if sec in ("garantias",):
            return "garantias"
        if sec in ("certificaciones", "documentos_requeridos", "requisitos", "anexos", "cronograma"):
            return "documentacion"
        return "documentacion"

    def _answer_from_context(
        self,
        question: str,
        item: dict,
        evidence: dict,
        enriched: dict,
        score: dict,
        dash: dict,
    ) -> str:
        q = question.lower()
        name = item.get("requirement") or item.get("requirement_key")
        parts: list[str] = []

        if any(k in q for k in ("evidencia", "página", "pagina", "pliego", "origen", "dónde", "donde")):
            if evidence.get("texto_original") or evidence.get("documento_origen"):
                parts.append(
                    f"Para «{name}», la evidencia del pliego está en "
                    f"{evidence.get('documento_origen') or 'documento origen no identificado'}"
                    + (
                        f", página {evidence.get('pagina')}"
                        if evidence.get("pagina") is not None
                        else ""
                    )
                    + (
                        f", sección «{evidence.get('parrafo')}»"
                        if evidence.get("parrafo")
                        else ""
                    )
                    + f". Texto: «{(evidence.get('texto_original') or '')[:280]}»."
                )
            else:
                parts.append(
                    f"No hay fragmento trazable del pliego para «{name}». "
                    "Reanalice el proceso con los adjuntos ingestados."
                )

        if any(k in q for k in ("cumple", "cumpl", "estado", "listo", "falta")):
            parts.append(
                f"Estado actual: {enriched.get('estado')}. Cumplimiento: {self._cumple_label(item)}. "
                f"Documento asociado: {item.get('document_title') or 'ninguno'}. "
                f"Riesgo: {item.get('risk') or 'sin riesgo registrado'}."
            )

        if any(k in q for k in ("responsable", "quién", "quien", "asign")):
            parts.append(
                f"Responsable: {item.get('assignee') or 'sin asignar'}. "
                f"Fecha límite: {item.get('due_date') or item.get('valid_until') or 'no definida'}."
            )

        if any(k in q for k in ("score", "calidad", "porcentaje", "%")):
            parts.append(score.get("explicacion") or f"Score del expediente: {score.get('score_total')}%.")

        if any(k in q for k in ("recomend", "qué hago", "que hago", "siguiente", "acción", "accion")):
            action = item.get("recommended_action") or enriched.get("observaciones_ia")
            parts.append(
                action
                or "Revise el documento asociado, complete observaciones y vuelva a validar el requisito."
            )

        if not parts:
            parts.append(
                f"Sobre «{name}»: estado {enriched.get('estado')}, "
                f"cumple={self._cumple_label(item)}, "
                f"doc={item.get('document_title') or '—'}. "
                f"{enriched.get('observaciones_ia') or ''} "
                f"Preparación del expediente: {dash.get('preparation_pct', 0)}%."
            )
            if evidence.get("texto_original"):
                parts.append(f"Evidencia: «{evidence['texto_original'][:200]}».")

        return " ".join(p.strip() for p in parts if p).strip()
