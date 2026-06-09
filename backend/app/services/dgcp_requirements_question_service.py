"""Consultas Assistant sobre requisitos DGCP por licitación (Fase 7.1 / 7.3)."""

from __future__ import annotations

import re
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.assistant import AssistantQueryResponse
from app.schemas.dgcp_bid import DGCPUserInputRequest
from app.services.assistant_context_policy import is_dgcp_record_question
from app.services.business_answer_builder import build_business_answer
from app.services.business_intent_router import BusinessIntentRouter
from app.services.dgcp_bid_package_service import DGCPBidPackageService


class DgcpRequirementsQuestionService:
    def __init__(self, db: AsyncSession, tenant_id: uuid.UUID, user_id: uuid.UUID | None = None):
        self.svc = DGCPBidPackageService(db, tenant_id, user_id)

    async def answer(self, question: str, opportunity_id: uuid.UUID) -> AssistantQueryResponse | None:
        q = question.strip()
        lowered = q.lower()

        live = await self._try_apply_live_input(q, opportunity_id)
        if live:
            return live

        classified = BusinessIntentRouter.classify(q)
        if not is_dgcp_record_question(q, classified):
            return None

        try:
            pkg = await self.svc.get_bid_package(opportunity_id)
            checklist = await self.svc.get_checklist(opportunity_id)
            requirements = await self.svc.get_requirements(opportunity_id)
            exp_status = await self.svc.get_expediente_status(opportunity_id)
            pkg_row = await self.svc._get_package(opportunity_id)
            evidence = list(pkg_row.requirement_evidence or []) if pkg_row else []
        except ValueError as exc:
            return AssistantQueryResponse(
                question=q,
                answer=str(exc),
                sources=["dgcp"],
                query_type="dgcp_requirements_query",
            )

        if any(k in lowered for k in ("lista para presentar", "listo para presentar", "está lista", "esta lista")):
            status = exp_status.expediente_status
            if status == "expediente_listo_para_revision":
                summary = (
                    f"El expediente {pkg.opportunity_code} está listo para revisión final "
                    f"({pkg.preparation_pct:.0f}% preparado). La presentación en DGCP permanece deshabilitada."
                )
            elif status == "expediente_listo_para_presentar":
                summary = f"Expediente marcado listo para presentar ({pkg.preparation_pct:.0f}%)."
            else:
                summary = (
                    f"Aún no está listo para presentar — estado: {status.replace('_', ' ')}. "
                    f"Preparación {pkg.preparation_pct:.0f}%, "
                    f"{pkg.pending_documents} pendiente(s), {pkg.expired_documents} vencido(s)."
                )
            return self._structured(
                q,
                summary,
                metrics=[
                    {"label": "Estado", "value": status.replace("_", " ")},
                    {"label": "Preparación", "value": f"{pkg.preparation_pct:.0f}%"},
                ],
            )

        if "visita" in lowered and ("técnica" in lowered or "tecnica" in lowered):
            visita = next((r for r in requirements.technical if r.key == "visita_tecnica"), None)
            if visita:
                ev = visita.evidence[0] if visita.evidence else None
                summary = f"Sí — el proceso requiere visita técnica."
                if ev:
                    summary += f" Evidencia: «{ev.fragmento[:120]}…» ({ev.documento_origen})."
            else:
                summary = "No se detectó visita técnica obligatoria en pliego/TDR ni descripción del proceso."
            return self._structured(q, summary)

        if any(k in lowered for k in ("criterio", "evaluación", "evaluacion", "puntuación", "puntuacion")):
            criterio = next((r for r in requirements.administrative if r.key == "criterios_evaluacion"), None)
            if criterio and criterio.evidence:
                ev = criterio.evidence[0]
                summary = f"Criterios de evaluación detectados. Evidencia: «{ev.fragmento[:160]}…» ({ev.documento_origen})."
            else:
                summary = "No se encontraron criterios de evaluación explícitos en los documentos analizados."
            return self._structured(q, summary)

        if "pliego" in lowered and "tdr" not in lowered:
            pliego_ev = [e for e in evidence if "pliego" in str(e.get("documento_origen", "")).lower()]
            docs = [d.label for d in requirements.mandatory_documents[:8]]
            if pliego_ev:
                summary = (
                    f"Requisitos extraídos del pliego ({len(pliego_ev)} evidencia(s)): "
                    + ", ".join(docs[:6])
                    + ("…" if len(docs) > 6 else "")
                )
                rows = [[e.get("documento_origen"), e.get("fragmento", "")[:80]] for e in pliego_ev[:5]]
                return self._structured(
                    q,
                    summary,
                    tables=[{"title": "Evidencia pliego", "columns": ["Documento", "Fragmento"], "rows": rows}],
                )
            summary = "No hay evidencia directa del pliego; revise la pestaña Documentos del Proceso e ingeste adjuntos."
            return self._structured(q, summary)

        if "tdr" in lowered or "términos de referencia" in lowered or "terminos de referencia" in lowered:
            tdr_ev = [
                e for e in evidence
                if "tdr" in str(e.get("documento_origen", "")).lower()
                or e.get("seccion", "").lower().startswith("tdr")
            ]
            tech = [r.label for r in requirements.technical[:6]]
            summary = f"Requisitos técnicos del TDR/proceso: {', '.join(tech) if tech else 'sin detalle técnico extraído'}."
            if tdr_ev:
                summary += f" {len(tdr_ev)} fragmento(s) con trazabilidad documental."
            return self._structured(q, summary)

        if "dgii vigente" in lowered or "tenemos dgii" in lowered:
            dgii = next((i for i in checklist.items if "dgii" in i.requirement_key), None)
            if dgii and dgii.status == "encontrado":
                summary = f"DGII vigente — {dgii.document_title or 'documento registrado'}."
            elif dgii and dgii.status == "vencido":
                summary = f"DGII vencida — renovar ({dgii.valid_until or 'fecha desconocida'})."
            else:
                summary = "No se encontró certificación DGII vigente en el repositorio corporativo."
            return self._structured(q, summary)

        if any(k in lowered for k in ("porcentaje", "por ciento", "listo", "preparación", "preparacion", "expediente")):
            summary = (
                f"Expediente {pkg.opportunity_code} — {pkg.preparation_pct:.0f}% preparado "
                f"({pkg.compliant_count or 0}/{pkg.mandatory_requirements or checklist.mandatory_total} "
                f"requisitos cumplidos). "
                f"{pkg.pending_documents} faltante(s), {pkg.expired_documents} vencido(s), "
                f"{pkg.forms_to_complete} por completar."
            )
            metrics = [
                {"label": "Preparación", "value": f"{pkg.preparation_pct:.0f}%"},
                {"label": "Encontrados", "value": str(pkg.found_documents)},
                {"label": "Pendientes", "value": str(pkg.pending_documents)},
                {"label": "Vencidos", "value": str(pkg.expired_documents)},
            ]
            return self._structured(q, summary, metrics)

        if any(k in lowered for k in ("faltan", "pendiente", "faltante", "completar esta licitación", "falta para completar")):
            missing = pkg.missing + pkg.to_complete
            if not missing:
                summary = "No hay requisitos pendientes según el análisis actual."
            else:
                summary = f"Faltan {len(missing)} requisito(s): " + ", ".join(missing[:6])
            rows = [[i.requirement, i.status, i.recommended_action or "—"] for i in checklist.items if i.status != "encontrado"][:10]
            return self._structured(
                q,
                summary,
                tables=[{"title": "Requisitos pendientes", "columns": ["Requisito", "Estado", "Acción"], "rows": rows}],
            )

        if "vencid" in lowered or "tss vigente" in lowered or "tenemos tss" in lowered:
            expired = [i for i in checklist.items if i.status == "vencido"]
            tss = next((i for i in checklist.items if "tss" in i.requirement_key), None)
            if tss:
                if tss.status == "encontrado":
                    summary = f"TSS vigente — documento: {tss.document_title or 'registrado'}."
                elif tss.status == "vencido":
                    summary = f"TSS vencida — renovar antes del cierre ({tss.valid_until or 'fecha desconocida'})."
                else:
                    summary = "No se encontró certificación TSS vigente en el repositorio."
            elif expired:
                summary = f"Hay {len(expired)} documento(s) vencido(s): " + ", ".join(i.requirement for i in expired[:5])
            else:
                summary = "No se detectaron documentos vencidos en el checklist."
            return self._structured(q, summary)

        if "sncc" in lowered or "formulario" in lowered:
            forms = requirements.sncc_forms or [i.form_type for i in checklist.items if i.form_type]
            if forms:
                summary = f"Formularios SNCC requeridos: {', '.join(forms)}. Use Autollenado para vista previa y generación controlada."
            else:
                summary = "No se detectaron formularios SNCC específicos; revise SNCC F.042 y F.047 por defecto."
            return self._structured(q, summary)

        if "checklist" in lowered or "prepárame" in lowered or "preparame" in lowered:
            rows = [
                [i.requirement, i.tipo, "Sí" if i.mandatory else "No", i.status]
                for i in checklist.items[:12]
            ]
            summary = f"Checklist de {pkg.opportunity_code}: {checklist.total} requisito(s), {checklist.ready_count} listo(s)."
            return self._structured(
                q,
                summary,
                metrics=[{"label": "Preparación", "value": f"{pkg.preparation_pct:.0f}%"}],
                tables=[{"title": "Checklist", "columns": ["Requisito", "Tipo", "Obligatorio", "Estado"], "rows": rows}],
            )

        return None

    async def _try_apply_live_input(self, question: str, opportunity_id: uuid.UUID) -> AssistantQueryResponse | None:
        lowered = question.lower()
        payload: dict[str, str] = {}
        extra: dict[str, str] = {}

        amount_match = re.search(r"rd\$?\s*([\d,\.]+)", question, re.I)
        if amount_match:
            payload["monto"] = f"RD${amount_match.group(1)}"
        elif "monto" in lowered:
            generic = re.search(r"([\d,\.]+)", question)
            if generic:
                payload["monto"] = f"RD${generic.group(1)}"

        fabricante_match = re.search(r"fabricante\s+(?:es\s+)?(.+)", question, re.I)
        if fabricante_match:
            payload["fabricante"] = fabricante_match.group(1).strip().rstrip(".")

        plazo_match = re.search(
            r"(?:plazo|entrega)\s+(?:de\s+)?(?:entrega\s+)?(?:es\s+)?(\d+\s*d[ií]as?)",
            question,
            re.I,
        )
        if plazo_match:
            payload["plazo_entrega"] = plazo_match.group(1)

        garantia_match = re.search(r"garant[ií]a\s+(?:de\s+)?(.+)", question, re.I)
        if garantia_match:
            payload["garantia"] = garantia_match.group(1).strip().rstrip(".")

        if "completa" in lowered and "sncc" in lowered:
            extra["sncc_requested"] = "SNCC.F042"

        if not payload and not extra:
            return None

        try:
            req = DGCPUserInputRequest(
                fabricante=payload.get("fabricante"),
                plazo_entrega=payload.get("plazo_entrega"),
                garantia=payload.get("garantia"),
                monto=payload.get("monto"),
                extra=extra,
            )
            await self.svc.apply_user_input(opportunity_id, req)
            pkg = await self.svc.get_bid_package(opportunity_id)
        except ValueError as exc:
            return AssistantQueryResponse(
                question=question,
                answer=str(exc),
                sources=["dgcp"],
                query_type="dgcp_requirements_query",
            )

        parts = [f"{k}={v}" for k, v in payload.items()]
        if extra:
            parts.extend(f"{k}={v}" for k, v in extra.items())
        summary = (
            f"Actualicé el expediente con: {', '.join(parts)}. "
            f"Preparación recalculada: {pkg.preparation_pct:.0f}%."
        )
        return self._structured(
            question,
            summary,
            metrics=[{"label": "Preparación", "value": f"{pkg.preparation_pct:.0f}%"}],
        )

    @staticmethod
    def _structured(
        question: str,
        summary: str,
        metrics: list[dict] | None = None,
        tables: list[dict] | None = None,
    ) -> AssistantQueryResponse:
        structured = build_business_answer(
            intent="dgcp_requirements_query",
            source="dgcp",
            summary=summary,
            metrics=metrics or [],
            tables=tables or [],
        )
        return AssistantQueryResponse(
            question=question,
            answer=summary,
            sources=["dgcp"],
            query_type="dgcp_requirements_query",
            structured_data=structured,
        )
