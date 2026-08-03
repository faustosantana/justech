"""Bid Copilot Enterprise — competitividad, adjudicación, comité, plan y dashboard gerencial.

Todas las métricas se derivan del checklist, evidencias, validación y datos DGCP reales.
No genera scores aleatorios ni conclusiones inventadas.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.dgcp_bid_package import DGCPBidPackage
from app.models.dgcp_opportunity import DGCPOpportunity
from app.services.dgcp_bid_package_service import (
    REQUIREMENT_UX_STATUS_MAP,
    DGCPBidPackageService,
)
from app.services.dgcp_expediente_enterprise_service import (
    COMPLIANT_UX,
    DGCPExpedienteEnterpriseService,
)


ADJUDICATION_CATEGORIES = (
    ("cumplimiento_documental", "Cumplimiento documental"),
    ("experiencia_similar", "Experiencia similar"),
    ("capacidad_tecnica", "Capacidad técnica"),
    ("certificaciones", "Certificaciones"),
    ("personal", "Personal"),
    ("oferta_economica", "Oferta económica"),
    ("garantias", "Garantías"),
    ("cronograma", "Cumplimiento del cronograma"),
)


class DGCPBidCopilotService:
    def __init__(self, db: AsyncSession, tenant_id: uuid.UUID, user_id: uuid.UUID | None = None):
        self.db = db
        self.tenant_id = tenant_id
        self.user_id = user_id
        self.bid = DGCPBidPackageService(db, tenant_id, user_id=user_id)
        self.enterprise = DGCPExpedienteEnterpriseService(db, tenant_id, user_id=user_id)

    async def get_copilot(self, opportunity_id: uuid.UUID) -> dict:
        # Histórico primero: si la tabla falta, rollback limpia la txn
        # antes de cargar el expediente y persistir resultados.
        hist_cache = await self._historical_cache_summary(opportunity_id)

        opp, pkg = await self._require_pkg(opportunity_id)
        checklist = list(pkg.checklist or [])
        enriched = [self.bid._enrich_requirement_item(i) for i in checklist]
        quality = self.enterprise._compute_score(pkg)
        final_val = self.bid._compute_final_validation(opp, pkg)
        similar = await self._similar_count(opportunity_id)

        competitiveness = self._competitiveness(
            opp, enriched, quality, final_val, similar, hist_cache
        )
        adjudication = self._adjudication_score(
            opp, pkg, enriched, quality, similar, hist_cache
        )
        action_plan = self._action_plan(opp, enriched)
        risks = self._risk_matrix(opp, pkg, enriched, final_val)
        executive = self._executive_summary(
            opp, pkg, quality, final_val, adjudication, competitiveness, risks
        )
        committee_preview = self._committee_simulation(
            opp, pkg, enriched, final_val, quality, adjudication
        )

        payload = {
            "opportunity_id": str(opportunity_id),
            "opportunity_code": opp.code,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "competitividad": competitiveness,
            "score_adjudicacion": adjudication,
            "plan_accion": action_plan,
            "matriz_riesgos": risks,
            "resumen_ejecutivo": executive,
            "simulacion_comite": committee_preview,
            "fuentes": [
                "checklist",
                "requirement_evidence",
                "bid_package",
                "final_validation",
                "historical_similar_cache" if hist_cache.get("available") else "sin_historico",
            ],
        }
        # Persistir en manifest para trazabilidad (sin inventar)
        manifest = dict(pkg.manifest or {})
        manifest["bid_copilot"] = {
            "generated_at": payload["generated_at"],
            "score_adjudicacion": adjudication.get("score_general"),
            "recomendacion": executive.get("recomendacion"),
        }
        pkg.manifest = manifest
        await self.db.commit()
        return payload

    async def simulate_committee(self, opportunity_id: uuid.UUID) -> dict:
        data = await self.get_copilot(opportunity_id)
        sim = data["simulacion_comite"]
        sim["simulated_at"] = datetime.now(timezone.utc).isoformat()
        sim["mode"] = "comite_evaluador"
        return sim

    async def get_executive_dashboard(self) -> dict:
        """Dashboard gerencial multi-expediente — datos reales del tenant."""
        base = DGCPOpportunity.tenant_id == self.tenant_id
        active_statuses = (
            "interested",
            "preparing",
            "to_bid",
            "pending_documents",
            "ready_to_submit",
            "submitted",
            "under_evaluation",
            "analyzing",
            "qualified",
            "to_review",
        )
        opps = list(
            (
                await self.db.execute(
                    select(DGCPOpportunity).where(
                        base,
                        DGCPOpportunity.status.in_(active_statuses + ("won", "awarded", "lost")),
                    )
                )
            ).scalars().all()
        )
        pkgs = {
            str(p.opportunity_id): p
            for p in (
                await self.db.execute(
                    select(DGCPBidPackage).where(DGCPBidPackage.tenant_id == self.tenant_id)
                )
            ).scalars().all()
        }

        activos = [o for o in opps if o.status in active_statuses]
        listos = 0
        riesgos_criticos = 0
        por_vencer = 0
        valor_total = Decimal("0")
        scores: list[float] = []
        por_responsable: dict[str, dict[str, int]] = {}
        costos_estimados = Decimal("0")
        today = date.today()

        for opp in activos:
            valor_total += Decimal(str(opp.amount or 0))
            pkg = pkgs.get(str(opp.id))
            if pkg:
                bid = pkg.bid_package or {}
                prep = float(bid.get("preparation_pct") or 0)
                if prep >= 90 or (pkg.expediente_status or "").startswith("expediente_listo"):
                    listos += 1
                # score adjudicación ligero desde calidad enterprise
                try:
                    sc = self.enterprise._compute_score(pkg)
                    scores.append(float(sc.get("score_total") or prep))
                except Exception:
                    scores.append(prep)
                for item in pkg.checklist or []:
                    risk = str(item.get("risk") or "").lower()
                    if "alto" in risk or item.get("status") in ("vencido", "no_cumple", "encontrado_vencido"):
                        riesgos_criticos += 1
                    assignee = (item.get("assignee") or "Sin asignar").strip() or "Sin asignar"
                    bucket = por_responsable.setdefault(
                        assignee, {"pendientes": 0, "completados": 0, "total": 0}
                    )
                    bucket["total"] += 1
                    ux = REQUIREMENT_UX_STATUS_MAP.get(str(item.get("status") or ""), "Pendiente")
                    if ux in COMPLIANT_UX:
                        bucket["completados"] += 1
                    else:
                        bucket["pendientes"] += 1
                # costo estimado = monto * (1 - prep/100) como esfuerzo restante documental (no inventado de precio)
                costos_estimados += Decimal(str(opp.amount or 0)) * Decimal(str(max(0, 100 - prep) / 100.0))
            if opp.deadline and 0 <= (opp.deadline - today).days <= 14:
                por_vencer += 1

        avg_prob = round(sum(scores) / len(scores), 1) if scores else 0.0

        return {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "expedientes_activos": len(activos),
            "expedientes_listos": listos,
            "riesgos_criticos": riesgos_criticos,
            "licitaciones_por_vencer": por_vencer,
            "valor_economico_total": str(valor_total),
            "probabilidad_promedio_adjudicacion": avg_prob,
            "costos_estimados_restantes": str(costos_estimados.quantize(Decimal("0.01"))),
            "estado_por_responsable": [
                {"responsable": k, **v} for k, v in sorted(por_responsable.items())
            ],
            "notas": [
                "Costos estimados = valor del proceso × % documental pendiente (proxy operativo, no cotización).",
                "Probabilidad promedio = media de scores de calidad/expediente de procesos activos.",
            ],
        }

    async def _require_pkg(
        self, opportunity_id: uuid.UUID
    ) -> tuple[DGCPOpportunity, DGCPBidPackage]:
        return await self.enterprise._require_pkg(opportunity_id)

    async def _similar_count(self, opportunity_id: uuid.UUID) -> int:
        opp = await self.bid._get_opportunity(opportunity_id)
        if not opp:
            return 0
        return len(opp.similar_history or [])

    async def _historical_cache_summary(self, opportunity_id: uuid.UUID) -> dict:
        try:
            from app.models.dgcp_historical_similar_cache import (
                DGCPProcessHistoricalSimilarResult,
            )

            row = (
                await self.db.execute(
                    select(DGCPProcessHistoricalSimilarResult).where(
                        DGCPProcessHistoricalSimilarResult.opportunity_id == opportunity_id,
                        DGCPProcessHistoricalSimilarResult.tenant_id == self.tenant_id,
                    )
                )
            ).scalar_one_or_none()
            if not row:
                return {"available": False, "matches": 0}
            results = row.results if isinstance(row.results, dict) else {}
            matches = results.get("matches") or results.get("items") or []
            if not isinstance(matches, list):
                matches = []
            total = results.get("total_matches")
            n = int(total) if isinstance(total, (int, float)) else len(matches)
            return {
                "available": True,
                "matches": n,
                "status": row.status,
                "message": row.error_message,
            }
        except Exception:
            # PostgreSQL aborta la txn en el primer error; hay que rollback
            # antes de seguir escribiendo (p. ej. manifest bid_copilot).
            try:
                await self.db.rollback()
            except Exception:
                pass
            return {"available": False, "matches": 0}

    def _competitiveness(
        self,
        opp: DGCPOpportunity,
        enriched: list[dict],
        quality: dict,
        final_val: dict,
        similar: int,
        hist: dict,
    ) -> dict:
        fortalezas: list[dict] = []
        debilidades: list[dict] = []
        criticos: list[dict] = []
        riesgos_descal: list[dict] = []
        opcionales_alto_valor: list[dict] = []
        ventajas: list[dict] = []

        for item in enriched:
            name = item.get("nombre") or item.get("requirement")
            cumple = self.enterprise._cumple_label(item)
            mandatory = bool(item.get("mandatory", True))
            if cumple == "Cumple" and mandatory:
                fortalezas.append(
                    {
                        "item": name,
                        "explicacion": f"Requisito obligatorio cumplido ({item.get('estado')})"
                        + (f" con documento «{item.get('documento_asociado')}»" if item.get("documento_asociado") else ""),
                    }
                )
            if cumple != "Cumple" and mandatory:
                debilidades.append(
                    {
                        "item": name,
                        "explicacion": f"Obligatorio en estado «{item.get('estado')}» — {item.get('observaciones_ia') or 'sin evidencia suficiente'}",
                    }
                )
                criticos.append(
                    {
                        "item": name,
                        "explicacion": "Crítico para presentación: sin cumplimiento puede impedir la oferta.",
                    }
                )
            if item.get("status") in ("vencido", "encontrado_vencido", "no_cumple"):
                riesgos_descal.append(
                    {
                        "item": name,
                        "explicacion": f"Estado «{item.get('status')}» — riesgo de descalificación documental.",
                    }
                )
            if not mandatory and cumple != "Cumple":
                opcionales_alto_valor.append(
                    {
                        "item": name,
                        "explicacion": "Opcional pendiente: puede mejorar puntaje si el pliego otorga puntos adicionales.",
                    }
                )

        if similar > 0 or hist.get("matches", 0) > 0:
            n = max(similar, int(hist.get("matches") or 0))
            ventajas.append(
                {
                    "item": "Experiencia / histórico similar",
                    "explicacion": f"Hay {n} referencia(s) de procesos/adjudicaciones similares registradas en JAIOS.",
                }
            )
        if opp.company and opp.company != "unclassified":
            ventajas.append(
                {
                    "item": f"Clasificación {opp.company}",
                    "explicacion": f"Proceso clasificado a {opp.company} (confianza {opp.confidence_score}%).",
                }
            )
        modality = (opp.modalidad or "").lower()
        if "mipyme" in modality or (opp.full_info or {}).get("dirigido_mipymes") == "Si":
            ventajas.append(
                {
                    "item": "Ventaja MIPYME",
                    "explicacion": "El proceso indica orientación MIPYME según datos DGCP.",
                }
            )

        return {
            "fortalezas": fortalezas[:20],
            "debilidades": debilidades[:20],
            "requisitos_criticos": criticos[:20],
            "riesgos_descalificacion": riesgos_descal[:15],
            "opcionales_alto_valor": opcionales_alto_valor[:10],
            "ventajas_competitivas": ventajas[:10],
            "calidad_expediente_pct": quality.get("score_total"),
            "listo_para_presentar": final_val.get("listo_para_presentar"),
        }

    def _adjudication_score(
        self,
        opp: DGCPOpportunity,
        pkg: DGCPBidPackage,
        enriched: list[dict],
        quality: dict,
        similar: int,
        hist: dict,
    ) -> dict:
        buckets: dict[str, list[dict]] = {k: [] for k, _ in ADJUDICATION_CATEGORIES}
        for item in enriched:
            key = self._adjudication_bucket(item)
            buckets[key].append(item)

        desglose = []
        values: list[float] = []
        explanations: list[str] = []

        for key, label in ADJUDICATION_CATEGORIES:
            items = buckets.get(key) or []
            if key == "experiencia_similar":
                # Basado en histórico real, no en ítems vacíos
                n = max(similar, int(hist.get("matches") or 0))
                if n >= 5:
                    pct = 85.0
                    detail = f"{n} similares en histórico/caché"
                elif n >= 1:
                    pct = 55.0 + min(25.0, n * 5)
                    detail = f"{n} similar(es) encontrado(s)"
                else:
                    pct = 15.0
                    detail = "Sin adjudicaciones/procesos similares indexados"
                    explanations.append("Experiencia similar baja: no hay histórico suficiente en JAIOS.")
                desglose.append({"key": key, "label": label, "pct": round(pct, 1), "detail": detail})
                values.append(pct)
                continue

            if key == "cronograma":
                if not opp.deadline:
                    pct = 40.0
                    detail = "Sin fecha de cierre en la oportunidad"
                    explanations.append("Cronograma incompleto: falta deadline del proceso.")
                else:
                    days = (opp.deadline - date.today()).days
                    if days < 0:
                        pct = 5.0
                        detail = "Proceso vencido"
                        explanations.append("El plazo de presentación ya venció.")
                    elif days <= 3:
                        pct = 25.0
                        detail = f"{days} día(s) restantes"
                        explanations.append("Plazo crítico para completar el expediente.")
                    elif days <= 10:
                        pct = 55.0
                        detail = f"{days} días restantes"
                    else:
                        pct = 80.0
                        detail = f"{days} días restantes"
                desglose.append({"key": key, "label": label, "pct": round(pct, 1), "detail": detail})
                values.append(pct)
                continue

            if not items:
                # Sin requisitos clasificados: no inventar 100 — marcar N/D con peso bajo
                desglose.append(
                    {
                        "key": key,
                        "label": label,
                        "pct": None,
                        "detail": "Sin requisitos clasificados en checklist para esta categoría",
                    }
                )
                continue

            ok = sum(1 for i in items if self.enterprise._cumple_label(i) == "Cumple")
            pct = round(100.0 * ok / len(items), 1)
            detail = f"{ok}/{len(items)} requisitos cumplidos"
            if pct < 100:
                pending = [i.get("nombre") or i.get("requirement") for i in items if self.enterprise._cumple_label(i) != "Cumple"]
                explanations.append(f"{label}: pendiente(s) {', '.join(str(p) for p in pending[:3])}")
            desglose.append({"key": key, "label": label, "pct": pct, "detail": detail})
            values.append(pct)

        score = round(sum(values) / len(values), 1) if values else float(quality.get("score_total") or 0)
        if not explanations and score < 100:
            explanations.append(
                f"Score {score}%: promedio de categorías con datos reales; categorías sin ítems no inflan el total."
            )
        if score >= 100:
            explanations = ["Score 100%: todas las categorías evaluadas con datos cumplen."]

        return {
            "score_general": score,
            "desglose": desglose,
            "explicacion_ia": " ".join(explanations) if explanations else f"Score de adjudicación {score}% basado en expediente y histórico disponibles.",
            "similar_matches": max(similar, int(hist.get("matches") or 0)),
            "calidad_expediente_pct": quality.get("score_total"),
        }

    def _adjudication_bucket(self, item: dict) -> str:
        sec = self.bid._section_for_requirement(item)
        key = str(item.get("requirement_key") or "").lower()
        if sec == "experiencia" or "experiencia" in key:
            return "experiencia_similar"
        if sec == "personal" or "personal" in key or "cv" in key:
            return "personal"
        if sec == "oferta_tecnica" or "tecnica" in key:
            return "capacidad_tecnica"
        if sec == "oferta_economica" or "econom" in key or "precio" in key:
            return "oferta_economica"
        if sec == "garantias" or "garantia" in key or "fianza" in key:
            return "garantias"
        if sec == "certificaciones" or any(t in key for t in ("tss", "dgii", "mipyme", "rpe", "certific")):
            return "certificaciones"
        if sec == "cronograma":
            return "cronograma"
        return "cumplimiento_documental"

    def _committee_simulation(
        self,
        opp: DGCPOpportunity,
        pkg: DGCPBidPackage,
        enriched: list[dict],
        final_val: dict,
        quality: dict,
        adjudication: dict,
    ) -> dict:
        observaciones: list[str] = []
        rechazos: list[str] = []
        debiles: list[str] = []
        incumplimientos: list[str] = []
        mejoras: list[str] = []

        for item in enriched:
            name = str(item.get("nombre") or item.get("requirement"))
            cumple = self.enterprise._cumple_label(item)
            if item.get("mandatory", True) and cumple == "Pendiente":
                incumplimientos.append(f"Falta documento/evidencia para: {name}")
                rechazos.append(f"Posible rechazo por incumplimiento de {name}")
            if cumple == "No cumple":
                rechazos.append(f"Documento rechazado / no conforme: {name}")
            if cumple == "Parcial":
                debiles.append(f"Evidencia débil o incompleta: {name}")
                observaciones.append(f"Revisar calidad de {name} antes de presentar")
            if item.get("status") in ("requiere_completado", "requiere_revision"):
                debiles.append(f"Requiere completado/revisión: {name}")
                mejoras.append(f"Completar y validar {name}")

        for gap in final_val.get("faltantes") or []:
            incumplimientos.append(f"Pendiente obligatorio: {gap}")
        for gap in final_val.get("rechazados") or []:
            rechazos.append(f"Rechazado en validación final: {gap}")

        if opp.deadline and (opp.deadline - date.today()).days <= 5:
            observaciones.append(
                f"Plazo cercano ({opp.deadline.isoformat()}): el comité podría cuestionar preparación apresurada."
            )
            mejoras.append("Priorizar requisitos críticos antes del cierre")

        if adjudication.get("score_general", 0) < 50:
            observaciones.append(
                f"Score de adjudicación bajo ({adjudication.get('score_general')}%): competitividad insuficiente según datos actuales."
            )

        veredicto = "apto_con_observaciones"
        if final_val.get("listo_para_presentar") and not rechazos and adjudication.get("score_general", 0) >= 70:
            veredicto = "apto"
        elif rechazos or len(incumplimientos) >= 3 or (quality.get("score_total") or 0) < 40:
            veredicto = "no_apto"

        return {
            "veredicto": veredicto,
            "veredicto_label": {
                "apto": "Apto para presentar",
                "apto_con_observaciones": "Apto con observaciones",
                "no_apto": "No apto / alto riesgo de rechazo",
            }[veredicto],
            "observaciones": observaciones[:20],
            "posibles_rechazos": list(dict.fromkeys(rechazos))[:15],
            "documentos_debiles": list(dict.fromkeys(debiles))[:15],
            "incumplimientos": list(dict.fromkeys(incumplimientos))[:20],
            "mejoras_recomendadas": list(dict.fromkeys(mejoras))[:15],
            "fundamento": (
                "Simulación basada en checklist, validación final del expediente y score de adjudicación. "
                "No sustituye evaluación oficial DGCP."
            ),
        }

    def _action_plan(self, opp: DGCPOpportunity, enriched: list[dict]) -> dict:
        tasks = []
        for item in enriched:
            if self.enterprise._cumple_label(item) == "Cumple":
                continue
            mandatory = bool(item.get("mandatory", True))
            status = str(item.get("status") or "")
            if status in ("vencido", "encontrado_vencido", "no_cumple") or mandatory:
                priority = "alta"
            elif status in ("requiere_completado", "requiere_revision", "requiere_actualizacion"):
                priority = "media"
            else:
                priority = "baja"
            due = item.get("due_date") or item.get("valid_until") or (
                opp.deadline.isoformat() if opp.deadline else None
            )
            tasks.append(
                {
                    "tarea": f"Resolver: {item.get('nombre') or item.get('requirement')}",
                    "responsable": item.get("assignee") or "Sin asignar",
                    "fecha_limite": due,
                    "dependencia": item.get("documento_asociado") or item.get("recommended_action") or "—",
                    "estado": item.get("estado") or item.get("status"),
                    "prioridad": priority,
                    "requirement_key": item.get("requirement_key"),
                    "checklist_item_id": str(item.get("id")) if item.get("id") else None,
                }
            )
        return {
            "alta": [t for t in tasks if t["prioridad"] == "alta"],
            "media": [t for t in tasks if t["prioridad"] == "media"],
            "baja": [t for t in tasks if t["prioridad"] == "baja"],
            "total": len(tasks),
        }

    def _risk_matrix(
        self,
        opp: DGCPOpportunity,
        pkg: DGCPBidPackage,
        enriched: list[dict],
        final_val: dict,
    ) -> list[dict]:
        risks: list[dict] = []

        def add(
            desc: str,
            *,
            impacto: str,
            probabilidad: str,
            recomendacion: str,
            accion: str,
        ) -> None:
            criticidad = "alta" if impacto == "alto" and probabilidad in ("alta", "media") else (
                "media" if impacto == "alto" or probabilidad == "alta" else "baja"
            )
            risks.append(
                {
                    "descripcion": desc,
                    "impacto": impacto,
                    "probabilidad": probabilidad,
                    "criticidad": criticidad,
                    "recomendacion_ia": recomendacion,
                    "accion_correctiva": accion,
                }
            )

        for item in enriched:
            name = item.get("nombre") or item.get("requirement")
            if item.get("status") in ("vencido", "encontrado_vencido"):
                add(
                    f"Documento vencido: {name}",
                    impacto="alto",
                    probabilidad="alta",
                    recomendacion="Renovar antes de la presentación; el pliego suele exigir vigencia.",
                    accion=f"Solicitar renovación de {name}",
                )
            if item.get("mandatory", True) and self.enterprise._cumple_label(item) == "Pendiente":
                add(
                    f"Requisito obligatorio pendiente: {name}",
                    impacto="alto",
                    probabilidad="alta",
                    recomendacion="Sin este requisito el expediente no está listo.",
                    accion=f"Asignar responsable y adjuntar evidencia de {name}",
                )
            if item.get("status") == "no_cumple":
                add(
                    f"Validación IA no conforme: {name}",
                    impacto="alto",
                    probabilidad="media",
                    recomendacion=str(item.get("observaciones_ia") or "Reemplazar documento"),
                    accion="Reemplazar documento y revalidar",
                )

        if opp.deadline:
            days = (opp.deadline - date.today()).days
            if days <= 7:
                add(
                    f"Cierre del proceso en {days} día(s)",
                    impacto="alto",
                    probabilidad="alta",
                    recomendacion="Concentrar esfuerzo en requisitos críticos.",
                    accion="Priorizar plan de acción alta",
                )

        for alert in pkg.alerts or []:
            if isinstance(alert, dict):
                desc = alert.get("message") or alert.get("descripcion") or alert.get("title")
                if desc:
                    nivel = str(alert.get("severity") or alert.get("nivel") or "medio").lower()
                    add(
                        str(desc),
                        impacto="alto" if nivel in ("alto", "critica", "crítica") else "medio",
                        probabilidad="media",
                        recomendacion="Atender alerta del motor de expediente.",
                        accion="Revisar alerta en pestaña Alertas",
                    )

        if final_val.get("listo_para_presentar") is False and final_val.get("explicacion"):
            add(
                "Validación final: no listo para presentar",
                impacto="alto",
                probabilidad="alta",
                recomendacion=str(final_val.get("explicacion"))[:300],
                accion="Ejecutar «Validar Expediente» y cerrar gaps",
            )

        # dedupe by description
        seen = set()
        out = []
        for r in risks:
            if r["descripcion"] in seen:
                continue
            seen.add(r["descripcion"])
            out.append(r)
        return out[:30]

    def _executive_summary(
        self,
        opp: DGCPOpportunity,
        pkg: DGCPBidPackage,
        quality: dict,
        final_val: dict,
        adjudication: dict,
        competitiveness: dict,
        risks: list[dict],
    ) -> dict:
        prep = float((pkg.bid_package or {}).get("preparation_pct") or 0)
        crit = [r for r in risks if r.get("criticidad") == "alta"]
        pending = final_val.get("faltantes") or []
        fortalezas = [f.get("item") for f in competitiveness.get("fortalezas") or []][:5]

        if final_val.get("listo_para_presentar") and adjudication.get("score_general", 0) >= 70 and len(crit) == 0:
            recomendacion = "listo_para_presentar"
            label = "✔ Listo para presentar"
        elif len(crit) >= 3 or adjudication.get("score_general", 0) < 40 or len(pending) >= 5:
            recomendacion = "no_presentar"
            label = "✘ No presentar"
        else:
            recomendacion = "presentar_con_observaciones"
            label = "⚠ Presentar con observaciones"

        return {
            "estado_expediente": pkg.expediente_status or "sin_preparar",
            "porcentaje_completado": prep,
            "score_calidad": quality.get("score_total"),
            "score_adjudicacion": adjudication.get("score_general"),
            "riesgos": [r["descripcion"] for r in crit[:8]],
            "fortalezas": fortalezas,
            "documentos_pendientes": pending[:15],
            "recomendacion": recomendacion,
            "recomendacion_label": label,
            "explicacion_ia": (
                f"{label}. Calidad expediente {quality.get('score_total')}%, "
                f"adjudicación {adjudication.get('score_general')}%, "
                f"preparación {prep:.0f}%. "
                f"{adjudication.get('explicacion_ia') or ''}"
            ).strip(),
            "proceso": {
                "code": opp.code,
                "title": opp.title,
                "institution": opp.institution,
                "amount": str(opp.amount),
                "deadline": opp.deadline.isoformat() if opp.deadline else None,
            },
        }
