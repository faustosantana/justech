"""Puente DGCP → Odoo CRM: oportunidad al iniciar preparación; won/lost al cerrar."""

from __future__ import annotations

import logging
import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from app.models.dgcp_opportunity import DGCPOpportunity
from app.services.company_scope_filter import CompanyScopeFilter

logger = logging.getLogger(__name__)

FULL_INFO_ODOO_ID = "odoo_crm_opportunity_id"
FULL_INFO_ODOO_URL = "odoo_crm_opportunity_url"
FULL_INFO_ODOO_NAME = "odoo_crm_opportunity_name"


class DGCPOdooCrmBridge:
    def __init__(self, db: AsyncSession, tenant_id: uuid.UUID, user_id: uuid.UUID):
        self.db = db
        self.tenant_id = tenant_id
        self.user_id = user_id

    def _client(self):
        from app.services.odoo_service import OdooService

        return OdooService(self.db, self.tenant_id, user_id=self.user_id)._bare_client()

    async def _company_id(self, opportunity: DGCPOpportunity) -> int | None:
        key = (opportunity.company or "").strip() or "justech"
        return await CompanyScopeFilter(
            self.db, self.tenant_id, self.user_id
        ).resolve_odoo_company_id_for_dgcp_key(key)

    async def ensure_opportunity_on_prepare(self, opportunity: DGCPOpportunity) -> dict[str, Any]:
        """Crea crm.lead (type=opportunity) si aún no existe. Soft-fail."""
        info = dict(opportunity.full_info or {})
        existing = info.get(FULL_INFO_ODOO_ID)
        if existing:
            return {"ok": True, "id": existing, "created": False}

        try:
            client = self._client()
            if not client.is_configured:
                return {"ok": False, "error": "odoo_not_configured"}

            company_id = await self._company_id(opportunity)
            name = f"{opportunity.code} — {(opportunity.title or 'Licitación DGCP')[:120]}"
            description_parts = [
                f"Proceso DGCP: {opportunity.code}",
                f"Institución: {opportunity.institution or '—'}",
                f"Empresa grupo: {opportunity.company or '—'}",
                f"Monto: {opportunity.amount or 0} {opportunity.currency or 'DOP'}",
            ]
            if opportunity.source_url:
                description_parts.append(f"Portal: {opportunity.source_url}")
            if opportunity.description:
                description_parts.append(str(opportunity.description)[:1500])

            vals: dict[str, Any] = {
                "name": name,
                "type": "opportunity",
                "description": "\n".join(description_parts),
                "expected_revenue": float(opportunity.amount or 0),
            }
            if opportunity.deadline:
                vals["date_deadline"] = opportunity.deadline.isoformat()
            if company_id:
                vals["company_id"] = company_id

            # Partner por institución (best-effort)
            institution = (opportunity.institution or "").strip()
            if institution:
                partners = await client.search_read(
                    "res.partner",
                    [("name", "ilike", institution[:80]), ("is_company", "=", True)],
                    ["id", "name"],
                    limit=1,
                )
                if partners:
                    vals["partner_id"] = partners[0]["id"]

            ctx = {"allowed_company_ids": [company_id]} if company_id else None
            lead_id = await client.execute_kw("crm.lead", "create", [vals], context=ctx)
            rows = await client.search_read(
                "crm.lead",
                [("id", "=", lead_id)],
                ["name"],
                limit=1,
                context=ctx,
            )
            lead_name = (rows[0].get("name") if rows else None) or name

            from app.services.odoo_url_helper import build_odoo_url

            info[FULL_INFO_ODOO_ID] = int(lead_id)
            info[FULL_INFO_ODOO_NAME] = lead_name
            info[FULL_INFO_ODOO_URL] = build_odoo_url("crm.lead", int(lead_id))
            opportunity.full_info = info
            flag_modified(opportunity, "full_info")
            await self.db.flush()
            return {"ok": True, "id": int(lead_id), "created": True, "name": lead_name}
        except Exception as exc:
            logger.exception(
                "DGCP→Odoo CRM create failed opportunity=%s: %s",
                opportunity.id,
                exc,
            )
            return {"ok": False, "error": str(exc)}

    async def sync_outcome(self, opportunity: DGCPOpportunity, *, won: bool) -> dict[str, Any]:
        """Actualiza probabilidad/etapa de la oportunidad Odoo. Soft-fail."""
        info = dict(opportunity.full_info or {})
        lead_id = info.get(FULL_INFO_ODOO_ID)
        if not lead_id:
            # Crear si no existía (p.ej. adjudicación directa)
            created = await self.ensure_opportunity_on_prepare(opportunity)
            if not created.get("ok"):
                return created
            info = dict(opportunity.full_info or {})
            lead_id = info.get(FULL_INFO_ODOO_ID)
        if not lead_id:
            return {"ok": False, "error": "no_odoo_id"}

        try:
            client = self._client()
            if not client.is_configured:
                return {"ok": False, "error": "odoo_not_configured"}

            company_id = await self._company_id(opportunity)
            ctx = {"allowed_company_ids": [company_id]} if company_id else None
            vals: dict[str, Any] = {
                "probability": 100.0 if won else 0.0,
            }
            if won:
                vals["expected_revenue"] = float(opportunity.amount or 0)
            else:
                vals["active"] = False

            # Intentar etapa Won/Lost por nombre (Odoo estándar)
            stage_domain = [
                ("name", "ilike", "Won" if won else "Lost"),
            ]
            stages = await client.search_read(
                "crm.stage",
                stage_domain,
                ["id", "name"],
                limit=5,
                context=ctx,
            )
            if not stages:
                stages = await client.search_read(
                    "crm.stage",
                    [("name", "ilike", "Ganad" if won else "Perdid")],
                    ["id", "name"],
                    limit=5,
                    context=ctx,
                )
            if stages:
                vals["stage_id"] = stages[0]["id"]

            await client.execute_kw(
                "crm.lead",
                "write",
                [[int(lead_id)], vals],
                context=ctx,
            )
            info["odoo_crm_last_outcome"] = "won" if won else "lost"
            opportunity.full_info = info
            flag_modified(opportunity, "full_info")
            await self.db.flush()
            return {"ok": True, "id": int(lead_id), "won": won}
        except Exception as exc:
            logger.exception(
                "DGCP→Odoo CRM outcome sync failed opportunity=%s: %s",
                opportunity.id,
                exc,
            )
            return {"ok": False, "error": str(exc)}
