"""Assistant — expediente real DGCP (Fase 3 / 3.5)."""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.assistant import AssistantQueryResponse
from app.services.real_dgcp_expediente_builder import RealDGCPExpedienteBuilder

REAL_EXPEDIENTE_SIGNALS = (
    "expediente real",
    "expediente dgcp",
    "paquete dgcp",
    "listo para subir",
    "listo para presentar",
    "genera el expediente",
    "generar expediente",
    "descarga el expediente",
    "manifest",
    "reporte preparacion",
    "reporte de preparación",
    "qué falta",
    "que falta",
    "por qué no está lista",
    "por que no esta lista",
    "documentos en revisión",
    "documentos en revision",
    "preparar paquete",
)


class RealExpedienteQuestionService:
    def __init__(self, db: AsyncSession, tenant_id: uuid.UUID, *, user_id: uuid.UUID | None = None):
        self.db = db
        self.tenant_id = tenant_id
        self.user_id = user_id
        self.builder = RealDGCPExpedienteBuilder(db, tenant_id, user_id=user_id)

    @classmethod
    def matches(cls, question: str) -> bool:
        q = question.lower()
        if any(s in q for s in REAL_EXPEDIENTE_SIGNALS):
            return True
        if "expediente" in q and any(
            w in q for w in ("falta", "subir", "descarg", "genera", "revisión", "revision", "manifest", "paquete")
        ):
            return True
        if "expediente" in q and "listo" in q and any(w in q for w in ("subir", "presentar", "revisión", "revision")):
            return True
        return False

    async def answer(
        self,
        question: str,
        *,
        opportunity_id: uuid.UUID | None = None,
    ) -> AssistantQueryResponse | None:
        if not opportunity_id:
            return AssistantQueryResponse(
                question=question,
                answer="Abra una licitación DGCP para consultar el expediente real.",
                sources=["dgcp_real_expediente"],
                query_type="dgcp_real_expediente",
            )

        q = question.lower()

        def resp(answer: str) -> AssistantQueryResponse:
            return AssistantQueryResponse(
                question=question,
                answer=answer,
                sources=["dgcp_real_expediente", "manifest.json"],
                query_type="dgcp_real_expediente",
            )

        try:
            status = await self.builder.get_status(opportunity_id)
            manifest = {}
            try:
                _, pkg = await self.builder._load_package(opportunity_id)
                manifest = self.builder.get_manifest(pkg)
            except ValueError:
                pass
        except ValueError as exc:
            return resp(str(exc))

        if any(p in q for p in ("genera", "generar")) and "expediente" in q:
            return resp(
                f"Use **Generar Expediente Real** o **Preparar Paquete DGCP** en la pestaña Expediente. "
                f"Estado actual: **{status.status}** · Preparación: **{status.preparation_pct:.0f}%**."
            )

        if "descarg" in q and "expediente" in q:
            if status.can_download:
                return resp(
                    f"Expediente disponible (**{status.zip_filename or 'ZIP'}**). "
                    "Use **Descargar Expediente ZIP** en la pestaña Expediente."
                )
            return resp("Aún no hay expediente generado. Pulse **Generar Expediente Real** primero.")

        if "listo para subir" in q or "listo para presentar" in q:
            ready = status.ready_to_upload or manifest.get("ready_to_upload") or []
            if not ready:
                return resp(
                    f"No hay documentos en **08_Listo_Para_Subir**. "
                    f"Estado: **{status.status}** · En revisión: {len(status.requires_review)}."
                )
            lines = [f"- {r.get('name', r.get('file', '—'))}" for r in ready[:15]]
            return resp(
                f"**{len(ready)} documento(s) listos para subir:**\n" + "\n".join(lines)
            )

        if any(p in q for p in ("qué falta", "que falta", "no está lista", "no esta lista")):
            missing = status.missing or manifest.get("missing") or []
            expired = status.expired or manifest.get("expired") or []
            review = status.requires_review or manifest.get("requires_review") or []
            lines = [
                f"Estado: **{status.status}** · Preparación: **{status.preparation_pct:.0f}%**",
                f"Faltantes: **{len(missing)}**",
                f"Vencidos: **{len(expired)}**",
                f"En revisión: **{len(review)}**",
            ]
            if missing:
                lines.append("**Faltantes:**")
                lines.extend([f"- {m.get('name', m)}" for m in missing[:10]])
            if expired:
                lines.append("**Vencidos:**")
                lines.extend([f"- {e.get('name', e)}" for e in expired[:8]])
            if review:
                lines.append("**Revisión:**")
                lines.extend([f"- {r.get('name', r)}" for r in review[:8]])
            return resp("\n".join(lines))

        if "revisión" in q or "revision" in q:
            review = status.requires_review or manifest.get("requires_review") or []
            if not review:
                return resp("No hay documentos pendientes en **07_Revision**.")
            lines = [f"- {r.get('name', '—')}: {r.get('reason', r.get('notes', ''))}" for r in review[:12]]
            return resp("**Documentos en revisión:**\n" + "\n".join(lines))

        if "manifest" in q:
            if not manifest:
                return resp("Manifest no disponible — genere el expediente real primero.")
            return resp(
                f"Manifest — proceso **{manifest.get('process_code', '—')}** · "
                f"estado **{manifest.get('status', status.status)}** · "
                f"{len(manifest.get('files') or [])} archivos · "
                f"{len(manifest.get('missing') or [])} faltantes."
            )

        return resp(
            f"Expediente real — **{status.status}** · {status.preparation_pct:.0f}% preparado · "
            f"{len(status.ready_to_upload)} listos para subir · "
            f"{len(status.missing)} faltantes. "
            "JAIOS no sube automáticamente al portal DGCP."
        )
