"""Assistant — preguntas sobre firma, sello y PDF final DGCP."""

from __future__ import annotations

import re
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.assistant import AssistantQueryResponse
from app.services.corporate_identity_service import CorporateIdentityService
from app.services.dgcp_bid_package_service import DGCPBidPackageService
from app.services.document_finalization_engine import DocumentFinalizationEngine
from app.services.document_finalization_rules import REQUIREMENTS_REQUIRING_FINALIZATION

FINALIZATION_SIGNALS = (
    "pdf final",
    "pdfs finales",
    "firmar",
    "firma",
    "sello",
    "sellado",
    "finaliz",
    "identidad corporativa",
    "firma_fausto",
    "sello justech",
)


class DocumentFinalizationQuestionService:
    def __init__(self, db: AsyncSession, tenant_id: uuid.UUID, *, user_id: uuid.UUID | None = None):
        self.db = db
        self.tenant_id = tenant_id
        self.user_id = user_id
        self.identity = CorporateIdentityService(db, tenant_id, user_id=user_id)
        self.bid = DGCPBidPackageService(db, tenant_id, user_id=user_id)
        self.engine = DocumentFinalizationEngine(db, tenant_id, user_id=user_id)

    @classmethod
    def matches(cls, question: str) -> bool:
        q = question.lower()
        return any(s in q for s in FINALIZATION_SIGNALS)

    async def answer(
        self,
        question: str,
        *,
        opportunity_id: uuid.UUID | None = None,
    ) -> AssistantQueryResponse | None:
        q = question.lower()

        def resp(answer: str, sources: list[str], query_type: str = "dgcp_finalization") -> AssistantQueryResponse:
            return AssistantQueryResponse(question=question, answer=answer, sources=sources, query_type=query_type)

        if any(p in q for p in ("sello", "stamp")) and any(
            p in q for p in ("justech", "just office", "plugsafe", "omni", "tenemos")
        ):
            overview = await self.identity.get_overview()
            lines = ["**Identidad corporativa — sellos**"]
            for stamp in overview.stamps:
                lines.append(f"- {stamp.company_label or stamp.company_key}: **{stamp.status}** ({stamp.filename})")
            if overview.missing:
                lines.append(f"Faltantes: {', '.join(overview.missing)}")
            return resp("\n".join(lines), ["corporate_identity"])

        if "firma" in q and ("fausto" in q or "tenemos" in q or "falta" in q):
            overview = await self.identity.get_overview()
            sig = overview.signature
            status = sig.status if sig else "faltante"
            return resp(f"Firma corporativa (`firma_fausto.png`): **{status}**.", ["corporate_identity"])

        if opportunity_id and any(p in q for p in ("faltan por firmar", "faltan por sellar", "pdf final", "pdfs finales", "listo para presentar")):
            pkg = await self.bid._get_package(opportunity_id)
            if not pkg:
                return resp(
                    "No hay análisis de requisitos para esta licitación. Ejecute «Analizar requisitos» primero.",
                    ["dgcp"],
                )
            pending = []
            finalized = []
            for item in pkg.checklist or []:
                key = item.get("requirement_key") or ""
                if key not in REQUIREMENTS_REQUIRING_FINALIZATION:
                    continue
                st = item.get("status", "faltante")
                if st in ("finalizado", "pdf_final_generado"):
                    finalized.append(f"{item.get('requirement')} ({st})")
                else:
                    pending.append(f"{item.get('requirement')} — {st}")

            if "genera" in q or "generar" in q:
                return resp(
                    "Use **Generar PDFs finales** en la pestaña Expediente o el botón por documento. "
                    f"Pendientes: {len(pending)} · Finalizados: {len(finalized)}.",
                    ["dgcp_finalization"],
                )

            lines = ["**Documentos SNCC / oferta — estado de finalización**"]
            lines.extend([f"- Pendiente: {p}" for p in pending[:12]] or ["- Ninguno pendiente"])
            lines.extend([f"- Finalizado: {f}" for f in finalized[:8]] or [])
            prep = (pkg.bid_package or {}).get("preparation_pct", 0)
            lines.append(f"Preparación expediente: **{prep}%** · Estado: **{pkg.expediente_status}**")
            return resp("\n".join(lines), ["dgcp_checklist"])

        form_match = re.search(r"sncc\.?f\.?0?(33|34|42|47)", q, re.I)
        if form_match and opportunity_id and ("genera" in q or "pdf" in q):
            key_map = {"33": "sncc_f033", "34": "sncc_f034", "42": "sncc_f042", "47": "sncc_f047"}
            req_key = key_map.get(form_match.group(1), "sncc_f042")
            return resp(
                f"Para generar el PDF final de **{req_key.upper()}**, abra la licitación → "
                "Checklist o Expediente → **Generar PDF final** (vista previa con firma y sello).",
                ["dgcp_finalization"],
            )

        if "oferta económica" in q or "oferta economica" in q:
            return resp(
                "Oferta económica: adjunte el PDF de cotización manualmente, luego use "
                "**Firmar y sellar → Generar PDF final** para crear `OFERTA_ECONOMICA_FINAL.pdf` en el expediente.",
                ["dgcp_finalization"],
            )

        return None
