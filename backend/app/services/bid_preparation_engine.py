"""Expediente inteligente — preparación de licitación (Fase 7.2)."""

from __future__ import annotations

from datetime import datetime, timezone

from app.models.dgcp_opportunity import DGCPOpportunity
from app.schemas.dgcp_bid import DGCPBidPackageResponse


class BidPreparationEngine:
    FOUND_STATUSES = {"encontrado"}
    PENDING_STATUSES = {"pendiente", "faltante"}
    EXPIRED_STATUSES = {"vencido", "requiere_actualizacion"}
    COMPLETE_STATUSES = {"completar", "requiere_completado", "incompleto", "plantilla_disponible"}

    def build(
        self,
        opportunity: DGCPOpportunity,
        checklist: list[dict],
        matches: list[dict],
        *,
        analyzed_at: datetime | None = None,
    ) -> DGCPBidPackageResponse:
        now = analyzed_at or datetime.now(timezone.utc)
        mandatory = [c for c in checklist if c.get("mandatory")]
        total = len(mandatory) or len(checklist) or 1

        found = sum(1 for c in checklist if c.get("status") in self.FOUND_STATUSES)
        pending = sum(1 for c in checklist if c.get("status") in self.PENDING_STATUSES)
        expired = sum(1 for c in checklist if c.get("status") in self.EXPIRED_STATUSES)
        to_complete = sum(1 for c in checklist if c.get("status") in self.COMPLETE_STATUSES)

        ready = found
        pct = round((ready / total) * 100, 1) if total else 0.0

        available = [c["requirement"] for c in checklist if c.get("status") in self.FOUND_STATUSES]
        missing = [c["requirement"] for c in checklist if c.get("status") in self.PENDING_STATUSES]
        expired_list = [c["requirement"] for c in checklist if c.get("status") in self.EXPIRED_STATUSES]
        complete_list = [c["requirement"] for c in checklist if c.get("status") in self.COMPLETE_STATUSES]

        knowledge_found = sum(1 for m in matches if m.get("match_source") == "knowledge_repository")
        tasks: list[str] = []
        if pending:
            tasks.append(f"Solicitar {pending} documento(s) faltante(s)")
        if expired:
            tasks.append(f"Renovar {expired} documento(s) vencido(s)")
        if to_complete:
            tasks.append(f"Completar {to_complete} formulario(s) SNCC")
        if knowledge_found:
            tasks.append(f"{knowledge_found} documento(s) encontrado(s) en repositorio corporativo JustechAI")

        return DGCPBidPackageResponse(
            opportunity_id=opportunity.id,
            opportunity_code=opportunity.code,
            preparation_pct=pct,
            found_documents=found,
            pending_documents=pending,
            expired_documents=expired,
            forms_to_complete=to_complete,
            recommended_tasks=tasks,
            available=available,
            missing=missing,
            expired=expired_list,
            to_complete=complete_list,
            analyzed_at=now,
        )

    @staticmethod
    def enrich_checklist(checklist: list[dict], matches: list[dict]) -> list[dict]:
        match_by_key = {m["requirement_key"]: m for m in matches}
        enriched: list[dict] = []
        for item in checklist:
            m = match_by_key.get(item.get("requirement_key"), {})
            item = dict(item)
            item["match_source"] = m.get("match_source")
            item["knowledge_asset_id"] = m.get("knowledge_asset_id")
            item["relative_path"] = m.get("relative_path")
            item["vigency_status"] = m.get("vigency_status")
            status = m.get("status") or item.get("status")
            item["status"] = status
            if status == "requiere_completado":
                item["completable"] = True
            if status == "vencido" and not item.get("risk"):
                item["risk"] = "Documento vencido — riesgo de descalificación"
            elif status == "requiere_actualizacion" and not item.get("risk"):
                item["risk"] = "Documento próximo a vencer"
            elif status == "plantilla_disponible" and not item.get("recommended_action"):
                item["recommended_action"] = "Usar plantilla corporativa y completar vista previa"
            enriched.append(item)
        return enriched
