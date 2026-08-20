"""Puente DGCP → Odoo CRM + cotización borrador (idempotente, soft-fail)."""

from __future__ import annotations

import logging
import re
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from app.models.dgcp_opportunity import DGCPOpportunity
from app.services.company_scope_filter import CompanyScopeFilter

logger = logging.getLogger(__name__)


def _as_int_id(value: Any) -> int:
    """Normaliza IDs que Odoo/SafeClient a veces devuelven como lista."""
    if isinstance(value, list):
        if not value:
            raise ValueError("empty_id_list")
        value = value[0]
    if isinstance(value, dict) and "id" in value:
        value = value["id"]
    return int(value)

# Persistencia en full_info["odoo_sync"]
SYNC_KEY = "odoo_sync"

# Campos custom Odoo (x_ porque se crean vía API sin módulo; el addon usa justech_*)
CRM_FIELDS = {
    "x_justech_dgcp_code": ("char", "Código DGCP"),
    "x_justech_jaios_id": ("char", "ID JAIOS/DGCP"),
    "x_justech_institution": ("char", "Entidad contratante"),
    "x_justech_company_key": ("char", "Empresa participante"),
    "x_justech_rpe": ("char", "RPE"),
    "x_justech_amount": ("float", "Monto estimado"),
    "x_justech_currency": ("char", "Moneda"),
    "x_justech_publish_date": ("date", "Fecha publicación"),
    "x_justech_deadline": ("date", "Fecha límite"),
    "x_justech_url": ("char", "URL DGCP"),
    "x_justech_dgcp_status": ("char", "Estado DGCP"),
    "x_justech_jaios_stage": ("char", "Etapa JAIOS"),
    "x_justech_awarded_amount": ("float", "Monto adjudicado"),
    "x_justech_awarded_date": ("date", "Fecha adjudicación"),
    "x_justech_result": ("char", "Resultado"),
}

SO_FIELDS = {
    "x_justech_dgcp_code": ("char", "Licitación DGCP"),
    "x_justech_jaios_id": ("char", "ID JAIOS/DGCP"),
}


class DGCPOdooCrmBridge:
    def __init__(self, db: AsyncSession, tenant_id: uuid.UUID, user_id: uuid.UUID):
        self.db = db
        self.tenant_id = tenant_id
        self.user_id = user_id
        self._crm_field_cache: set[str] | None = None
        self._so_field_cache: set[str] | None = None

    def _client(self):
        from app.services.odoo_service import OdooService
        import inspect

        bare = OdooService(self.db, self.tenant_id, user_id=self.user_id)._bare_client
        if inspect.iscoroutinefunction(bare):
            raise RuntimeError("Use _client_async")
        return bare()

    async def _client_async(self):
        from app.services.odoo_service import OdooService
        import inspect

        bare = OdooService(self.db, self.tenant_id, user_id=self.user_id)._bare_client
        if inspect.iscoroutinefunction(bare):
            return await bare()
        return bare()

    async def _company_id(self, opportunity: DGCPOpportunity) -> int | None:
        key = (opportunity.company or "").strip() or "justech"
        return await CompanyScopeFilter(
            self.db, self.tenant_id, self.user_id
        ).resolve_odoo_company_id_for_dgcp_key(key)

    async def _rpe_for_company(self, company_key: str) -> str | None:
        """Best-effort RPE from company profiles. Never abort the outer transaction."""
        queries = [
            """
            select coalesce(
              nullif(trim(metadata->>'rpe'), ''),
              nullif(trim(metadata->>'proveedor_estado'), '')
            ) as rpe
            from jaios.licitador_company_profiles
            where tenant_id = :t and company_key = :k
            limit 1
            """,
            """
            select coalesce(
              nullif(trim(rpe), ''),
              nullif(trim(proveedor_estado), '')
            ) as rpe
            from jaios.licitador_company_profiles
            where tenant_id = :t and company_key = :k
            limit 1
            """,
        ]
        from sqlalchemy import text

        for sql in queries:
            try:
                async with self.db.begin_nested():
                    row = (
                        await self.db.execute(
                            text(sql),
                            {"t": self.tenant_id, "k": company_key},
                        )
                    ).first()
                    if row and row[0]:
                        return str(row[0]).strip()
            except Exception:
                continue
        return None

    def _sync_blob(self, opportunity: DGCPOpportunity) -> dict[str, Any]:
        info = dict(opportunity.full_info or {})
        blob = dict(info.get(SYNC_KEY) or {})
        # migrate legacy keys
        if info.get("odoo_crm_opportunity_id") and not blob.get("crm_opportunity_id"):
            blob["crm_opportunity_id"] = info["odoo_crm_opportunity_id"]
            blob["crm_opportunity_url"] = info.get("odoo_crm_opportunity_url")
            blob["crm_opportunity_name"] = info.get("odoo_crm_opportunity_name")
        return blob

    def _save_sync(self, opportunity: DGCPOpportunity, blob: dict[str, Any]) -> None:
        info = dict(opportunity.full_info or {})
        info[SYNC_KEY] = blob
        # keep legacy mirrors for UI that still reads them
        if blob.get("crm_opportunity_id"):
            info["odoo_crm_opportunity_id"] = blob["crm_opportunity_id"]
            info["odoo_crm_opportunity_url"] = blob.get("crm_opportunity_url")
            info["odoo_crm_opportunity_name"] = blob.get("crm_opportunity_name")
        if blob.get("sale_order_id"):
            info["odoo_sale_order_id"] = blob["sale_order_id"]
            info["odoo_sale_order_url"] = blob.get("sale_order_url")
            info["odoo_sale_order_name"] = blob.get("sale_order_name")
        opportunity.full_info = info
        flag_modified(opportunity, "full_info")

    def _mark_pending(self, opportunity: DGCPOpportunity, action: str, error: str) -> dict[str, Any]:
        blob = self._sync_blob(opportunity)
        blob.update(
            {
                "status": "sync_pending",
                "last_action": action,
                "last_error": error[:1000],
                "last_error_at": datetime.now(timezone.utc).isoformat(),
                "retry_count": int(blob.get("retry_count") or 0) + 1,
            }
        )
        self._save_sync(opportunity, blob)
        return {"ok": False, "status": "sync_pending", "error": error, "retry_count": blob["retry_count"]}

    def _mark_ok(self, opportunity: DGCPOpportunity, action: str, **extra: Any) -> dict[str, Any]:
        blob = self._sync_blob(opportunity)
        blob.update(
            {
                "status": "synced",
                "last_action": action,
                "last_error": None,
                "last_synced_at": datetime.now(timezone.utc).isoformat(),
                **extra,
            }
        )
        self._save_sync(opportunity, blob)
        return {"ok": True, "status": "synced", **extra}

    async def _ensure_custom_fields(self, client, model: str, specs: dict[str, tuple[str, str]]) -> set[str]:
        existing = await client.execute_kw(model, "fields_get", [], {"attributes": ["string", "type"]})
        present = set(existing.keys())
        missing = [name for name in specs if name not in present]
        if not missing:
            return present
        models = await client.search_read("ir.model", [("model", "=", model)], ["id"], limit=1)
        if not models:
            return present
        model_id = models[0]["id"]
        for name in missing:
            ttype, label = specs[name]
            try:
                await client.execute_kw(
                    "ir.model.fields",
                    "create",
                    [
                        {
                            "name": name,
                            "field_description": label,
                            "model_id": model_id,
                            "ttype": ttype,
                            "state": "manual",
                        }
                    ],
                )
                present.add(name)
                logger.info("Created Odoo field %s.%s", model, name)
            except Exception as exc:
                logger.warning("Could not create field %s.%s: %s", model, name, exc)
        return present

    async def _crm_fields(self, client) -> set[str]:
        if self._crm_field_cache is None:
            self._crm_field_cache = await self._ensure_custom_fields(client, "crm.lead", CRM_FIELDS)
        return self._crm_field_cache

    async def _so_fields(self, client) -> set[str]:
        if self._so_field_cache is None:
            self._so_field_cache = await self._ensure_custom_fields(client, "sale.order", SO_FIELDS)
        return self._so_field_cache

    def _stage_label(self, status: str | None) -> str:
        mapping = {
            "detected": "nuevas",
            "interested": "interesadas",
            "preparing": "en_preparacion",
            "ready_to_submit": "listas_para_presentar",
            "submitted": "presentadas",
            "suspended": "suspendidas",
            "awarded": "adjudicadas",
            "won": "adjudicadas",
            "lost": "no_adjudicadas",
            "discarded": "descartadas",
        }
        return mapping.get((status or "").lower(), status or "")

    async def _crm_vals(self, client, opportunity: DGCPOpportunity, *, result: str | None = None) -> dict[str, Any]:
        fields = await self._crm_fields(client)
        company_key = (opportunity.company or "").strip() or "justech"
        rpe = await self._rpe_for_company(company_key)
        publish = None
        if opportunity.created_at:
            publish = opportunity.created_at.date().isoformat()
        payload = {
            "dgcp_code": opportunity.code,
            "jaios_id": str(opportunity.id),
            "institution": (opportunity.institution or "")[:200],
            "company_key": company_key,
            "rpe": rpe or "",
            "amount": float(opportunity.amount or 0),
            "currency": opportunity.currency or "DOP",
            "publish_date": publish,
            "deadline": opportunity.deadline.isoformat() if opportunity.deadline else False,
            "url": opportunity.source_url or "",
            "dgcp_status": opportunity.status,
            "jaios_stage": self._stage_label(opportunity.status),
            "result": result or "",
            "awarded_amount": float(opportunity.amount or 0) if result == "adjudicada" else None,
            "awarded_date": datetime.now(timezone.utc).date().isoformat() if result == "adjudicada" else None,
        }
        out: dict[str, Any] = {}
        # Prefer module fields (justech_*) then API-created (x_justech_*)
        mapping = {
            "dgcp_code": ("justech_dgcp_code", "x_justech_dgcp_code"),
            "jaios_id": ("justech_jaios_id", "x_justech_jaios_id"),
            "institution": ("justech_institution", "x_justech_institution"),
            "company_key": ("justech_company_key", "x_justech_company_key"),
            "rpe": ("justech_rpe", "x_justech_rpe"),
            "amount": ("justech_amount", "x_justech_amount"),
            "currency": ("justech_currency", "x_justech_currency"),
            "publish_date": ("justech_publish_date", "x_justech_publish_date"),
            "deadline": ("justech_deadline", "x_justech_deadline"),
            "url": ("justech_url", "x_justech_url"),
            "dgcp_status": ("justech_dgcp_status", "x_justech_dgcp_status"),
            "jaios_stage": ("justech_jaios_stage", "x_justech_jaios_stage"),
            "result": ("justech_result", "x_justech_result"),
            "awarded_amount": ("justech_awarded_amount", "x_justech_awarded_amount"),
            "awarded_date": ("justech_awarded_date", "x_justech_awarded_date"),
        }
        for key, names in mapping.items():
            val = payload.get(key)
            if val in (None, ""):
                continue
            for name in names:
                if name in fields:
                    out[name] = val
                    break
        return out

    async def _find_existing_lead(self, client, opportunity: DGCPOpportunity, company_id: int | None) -> int | None:
        fields = await self._crm_fields(client)
        domain_base: list[Any] = [("type", "=", "opportunity")]
        if company_id:
            domain_base.append(("company_id", "=", company_id))
        for fname in ("justech_dgcp_code", "x_justech_dgcp_code"):
            if fname in fields:
                rows = await client.search_read(
                    "crm.lead",
                    domain_base + [(fname, "=", opportunity.code)],
                    ["id"],
                    limit=1,
                )
                if rows:
                    return _as_int_id(rows[0]["id"])
        for fname in ("justech_jaios_id", "x_justech_jaios_id"):
            if fname in fields:
                rows = await client.search_read(
                    "crm.lead",
                    [(fname, "=", str(opportunity.id))],
                    ["id"],
                    limit=1,
                )
                if rows:
                    return _as_int_id(rows[0]["id"])
        rows = await client.search_read(
            "crm.lead",
            domain_base + [("name", "ilike", f"{opportunity.code} —%")],
            ["id"],
            limit=1,
        )
        if rows:
            return _as_int_id(rows[0]["id"])
        return None

    async def _resolve_partner(
        self, client, opportunity: DGCPOpportunity, *, company_id: int | None
    ) -> dict[str, Any]:
        """Return partner_id or review flags. Never invent ambiguous partners."""
        institution = (opportunity.institution or "").strip()
        if not institution or len(institution) < 4:
            return {"partner_id": None, "customer_required": True, "review_required": True, "reason": "no_institution"}

        domain: list[Any] = [("is_company", "=", True), ("name", "=ilike", institution)]
        exact = await client.search_read("res.partner", domain, ["id", "name"], limit=3)
        if len(exact) == 1:
            return {"partner_id": _as_int_id(exact[0]["id"]), "customer_required": False, "review_required": False}

        fuzzy = await client.search_read(
            "res.partner",
            [("is_company", "=", True), ("name", "ilike", institution[:60])],
            ["id", "name"],
            limit=5,
        )
        if len(fuzzy) == 1:
            return {"partner_id": _as_int_id(fuzzy[0]["id"]), "customer_required": False, "review_required": False}
        if len(fuzzy) > 1:
            return {
                "partner_id": None,
                "customer_required": True,
                "review_required": True,
                "reason": "ambiguous_partner",
                "candidates": [{"id": r["id"], "name": r["name"]} for r in fuzzy],
            }

        # Create only when unique name and sufficiently long/reliable
        if re.search(r"[A-Za-zÁÉÍÓÚáéíóúñÑ]{4,}", institution) and len(institution) >= 8:
            vals: dict[str, Any] = {
                "name": institution[:200],
                "is_company": True,
                "company_type": "company",
                "comment": f"Creado desde JAIOS DGCP {opportunity.code}",
            }
            if company_id:
                vals["company_id"] = company_id
            try:
                pid = await client.execute_kw("res.partner", "create", [vals])
                return {
                    "partner_id": _as_int_id(pid),
                    "customer_required": False,
                    "review_required": False,
                    "created": True,
                }
            except Exception as exc:
                return {
                    "partner_id": None,
                    "customer_required": True,
                    "review_required": True,
                    "reason": f"create_failed:{exc}",
                }

        return {
            "partner_id": None,
            "customer_required": True,
            "review_required": True,
            "reason": "unreliable_institution",
        }

    async def ensure_opportunity_on_prepare(self, opportunity: DGCPOpportunity) -> dict[str, Any]:
        """Upsert crm.lead by (company + DGCP code). Idempotent."""
        action = "ensure_opportunity"
        try:
            client = await self._client_async()
            if not client.is_configured:
                return self._mark_pending(opportunity, action, "odoo_not_configured")

            company_id = await self._company_id(opportunity)
            from app.services.odoo_url_helper import build_odoo_url

            existing_id = self._sync_blob(opportunity).get("crm_opportunity_id")
            if not existing_id:
                existing_id = await self._find_existing_lead(client, opportunity, company_id)

            custom = await self._crm_vals(client, opportunity, result=None)
            name = f"{opportunity.code} — {(opportunity.title or 'Licitación DGCP')[:120]}"
            description_parts = [
                f"Proceso DGCP: {opportunity.code}",
                f"JAIOS ID: {opportunity.id}",
                f"Institución: {opportunity.institution or '—'}",
                f"Empresa grupo: {opportunity.company or '—'}",
                f"Monto: {opportunity.amount or 0} {opportunity.currency or 'DOP'}",
                f"Estado: {opportunity.status}",
            ]
            if opportunity.source_url:
                description_parts.append(f"Portal: {opportunity.source_url}")

            vals: dict[str, Any] = {
                "name": name,
                "type": "opportunity",
                "description": "\n".join(description_parts),
                "expected_revenue": float(opportunity.amount or 0),
                **custom,
            }
            if opportunity.deadline:
                vals["date_deadline"] = opportunity.deadline.isoformat()
            if company_id:
                vals["company_id"] = company_id

            partner = await self._resolve_partner(client, opportunity, company_id=company_id)
            if partner.get("partner_id"):
                vals["partner_id"] = partner["partner_id"]

            ctx = {"allowed_company_ids": [company_id]} if company_id else None
            created = False
            if existing_id:
                await client.execute_kw("crm.lead", "write", [[_as_int_id(existing_id)], vals])
                lead_id = _as_int_id(existing_id)
            else:
                lead_id = _as_int_id(await client.execute_kw("crm.lead", "create", [vals]))
                created = True

            rows = await client.search_read(
                "crm.lead", [("id", "=", lead_id)], ["name"], limit=1
            )
            lead_name = (rows[0].get("name") if rows else None) or name
            return self._mark_ok(
                opportunity,
                action,
                crm_opportunity_id=lead_id,
                crm_opportunity_url=build_odoo_url("crm.lead", lead_id),
                crm_opportunity_name=lead_name,
                created=created,
                partner=partner,
            )
        except Exception as exc:
            logger.exception("DGCP→Odoo ensure_opportunity failed %s", opportunity.id)
            await self.db.flush()
            return self._mark_pending(opportunity, action, str(exc))

    async def _map_product_lines(
        self, client, opportunity: DGCPOpportunity
    ) -> list[dict[str, Any]]:
        """Map technical-sheet / suggested lines to Odoo products. Never invent."""
        lines_out: list[dict[str, Any]] = []
        candidates: list[dict[str, Any]] = []

        # From bid package technical sheets if present
        try:
            from sqlalchemy import select
            from app.models.dgcp_bid_package import DGCPBidPackage

            pkg = (
                await self.db.execute(
                    select(DGCPBidPackage).where(
                        DGCPBidPackage.opportunity_id == opportunity.id,
                        DGCPBidPackage.tenant_id == self.tenant_id,
                    )
                )
            ).scalar_one_or_none()
            block = (pkg.payload or {}).get("technical_sheets") if pkg and pkg.payload else None
            if isinstance(block, dict):
                for item in block.get("items") or []:
                    offered = item.get("offered_product") or {}
                    name = (
                        offered.get("name")
                        or offered.get("product_name")
                        or item.get("title")
                        or item.get("requirement")
                        or ""
                    )
                    sku = offered.get("sku") or offered.get("default_code")
                    qty = float(offered.get("quantity") or item.get("quantity") or 1)
                    price = float(offered.get("unit_price") or offered.get("price") or 0)
                    if name or sku:
                        candidates.append(
                            {"name": str(name)[:200], "sku": sku, "qty": qty, "price": price}
                        )
        except Exception:
            logger.debug("No technical sheet lines for %s", opportunity.id, exc_info=True)

        # From economic offer suggestions in full_info
        info = opportunity.full_info or {}
        for p in info.get("suggested_products") or []:
            if isinstance(p, dict):
                candidates.append(
                    {
                        "name": str(p.get("product_name") or "")[:200],
                        "sku": p.get("sku"),
                        "qty": float(p.get("quantity") or 1),
                        "price": float(p.get("unit_price") or p.get("price") or 0),
                    }
                )

        for cand in candidates[:40]:
            product_id = None
            status = "UNMATCHED"
            if cand.get("sku"):
                rows = await client.search_read(
                    "product.product",
                    [("default_code", "=", str(cand["sku"]))],
                    ["id", "name", "list_price", "default_code"],
                    limit=2,
                )
                if len(rows) == 1:
                    product_id = _as_int_id(rows[0]["id"])
                    status = "MATCHED"
                    if not cand["price"]:
                        cand["price"] = float(rows[0].get("list_price") or 0)
                elif len(rows) > 1:
                    status = "REVIEW_REQUIRED"
            if not product_id and cand.get("name") and len(cand["name"]) >= 5:
                rows = await client.search_read(
                    "product.product",
                    [("name", "=ilike", cand["name"])],
                    ["id", "name", "list_price"],
                    limit=3,
                )
                if len(rows) == 1:
                    product_id = _as_int_id(rows[0]["id"])
                    status = "MATCHED"
                    if not cand["price"]:
                        cand["price"] = float(rows[0].get("list_price") or 0)
                elif len(rows) > 1:
                    status = "REVIEW_REQUIRED"

            lines_out.append(
                {
                    "status": status,
                    "product_id": product_id,
                    "name": cand.get("name"),
                    "sku": cand.get("sku"),
                    "qty": cand.get("qty") or 1,
                    "price": cand.get("price") or 0,
                }
            )
        return lines_out

    async def _ensure_draft_quotation(
        self, client, opportunity: DGCPOpportunity, lead_id: int, company_id: int | None
    ) -> dict[str, Any]:
        from app.services.odoo_url_helper import build_odoo_url

        blob = self._sync_blob(opportunity)
        if blob.get("sale_order_id"):
            return {
                "sale_order_id": blob["sale_order_id"],
                "sale_order_name": blob.get("sale_order_name"),
                "sale_order_url": blob.get("sale_order_url"),
                "created": False,
            }

        # Idempotency: search by origin / x_justech_dgcp_code
        so_fields = await self._so_fields(client)
        domain: list[Any] = [("state", "in", ["draft", "sent"])]
        if company_id:
            domain.append(("company_id", "=", company_id))
        code_domains = []
        if "justech_dgcp_code" in so_fields:
            code_domains.append(("justech_dgcp_code", "=", opportunity.code))
        if "x_justech_dgcp_code" in so_fields:
            code_domains.append(("x_justech_dgcp_code", "=", opportunity.code))
        code_domains.append(("origin", "=", opportunity.code))
        existing = []
        for cd in code_domains:
            existing = await client.search_read(
                "sale.order", domain + [cd], ["id", "name", "state"], limit=1
            )
            if existing:
                break
        if existing:
            oid = _as_int_id(existing[0]["id"])
            return {
                "sale_order_id": oid,
                "sale_order_name": existing[0].get("name"),
                "sale_order_url": build_odoo_url("sale.order", oid),
                "created": False,
            }

        partner = await self._resolve_partner(client, opportunity, company_id=company_id)
        mapped = await self._map_product_lines(client, opportunity)
        matched = [m for m in mapped if m["status"] == "MATCHED" and m.get("product_id")]

        vals: dict[str, Any] = {
            "origin": opportunity.code,
            "opportunity_id": lead_id,
            "note": (
                f"Cotización borrador generada desde JAIOS al adjudicar {opportunity.code}.\n"
                f"Requiere revisión comercial antes de confirmar."
            ),
        }
        if "justech_dgcp_code" in so_fields:
            vals["justech_dgcp_code"] = opportunity.code
        elif "x_justech_dgcp_code" in so_fields:
            vals["x_justech_dgcp_code"] = opportunity.code
        if "justech_jaios_id" in so_fields:
            vals["justech_jaios_id"] = str(opportunity.id)
        elif "x_justech_jaios_id" in so_fields:
            vals["x_justech_jaios_id"] = str(opportunity.id)
        if company_id:
            vals["company_id"] = company_id
        if partner.get("partner_id"):
            vals["partner_id"] = partner["partner_id"]
        else:
            # Odoo requires partner_id — use a placeholder review partner only if exact company internal?
            # Do NOT invent. Mark pending for quotation if no partner.
            return {
                "sale_order_id": None,
                "customer_required": True,
                "review_required": True,
                "partner": partner,
                "line_mapping": mapped,
                "error": "customer_required_for_quotation",
            }

        order_lines = []
        for m in matched:
            order_lines.append(
                (
                    0,
                    0,
                    {
                        "product_id": m["product_id"],
                        "name": m["name"] or "Línea DGCP",
                        "product_uom_qty": m["qty"] or 1,
                        "price_unit": float(m["price"] or 0),
                    },
                )
            )
        # If no matched lines, create a note line via display_type if supported, else skip lines
        if order_lines:
            vals["order_line"] = order_lines

        ctx = {"allowed_company_ids": [company_id]} if company_id else None
        so_id = _as_int_id(await client.execute_kw("sale.order", "create", [vals]))
        rows = await client.search_read(
            "sale.order", [("id", "=", so_id)], ["name", "state"], limit=1
        )
        name = (rows[0].get("name") if rows else None) or f"SO{so_id}"
        return {
            "sale_order_id": so_id,
            "sale_order_name": name,
            "sale_order_url": build_odoo_url("sale.order", so_id),
            "created": True,
            "partner": partner,
            "line_mapping": mapped,
            "matched_lines": len(matched),
            "state": (rows[0].get("state") if rows else "draft"),
        }

    async def sync_outcome(self, opportunity: DGCPOpportunity, *, won: bool) -> dict[str, Any]:
        action = "mark_won" if won else "mark_lost"
        try:
            ensured = await self.ensure_opportunity_on_prepare(opportunity)
            if not ensured.get("ok") and not self._sync_blob(opportunity).get("crm_opportunity_id"):
                return ensured

            client = await self._client_async()
            company_id = await self._company_id(opportunity)
            lead_id = _as_int_id(self._sync_blob(opportunity)["crm_opportunity_id"])
            ctx = {"allowed_company_ids": [company_id]} if company_id else None

            custom = await self._crm_vals(
                client,
                opportunity,
                result="adjudicada" if won else "no_adjudicada",
            )

            vals: dict[str, Any] = {
                "probability": 100.0 if won else 0.0,
                **custom,
            }
            if won:
                vals["expected_revenue"] = float(opportunity.amount or 0)
            else:
                vals["active"] = False

            stages = await client.search_read(
                "crm.stage",
                [("name", "ilike", "Won" if won else "Lost")],
                ["id", "name"],
                limit=5,
            )
            if not stages:
                stages = await client.search_read(
                    "crm.stage",
                    [("name", "ilike", "Ganad" if won else "Perdid")],
                    ["id", "name"],
                    limit=5,
                )
            if stages:
                vals["stage_id"] = stages[0]["id"]

            await client.execute_kw("crm.lead", "write", [[lead_id], vals])

            quotation: dict[str, Any] | None = None
            if won:
                quotation = await self._ensure_draft_quotation(
                    client, opportunity, lead_id, company_id
                )
                if quotation.get("error") == "customer_required_for_quotation":
                    # Won synced, quotation pending human partner
                    return self._mark_ok(
                        opportunity,
                        action,
                        crm_opportunity_id=lead_id,
                        won=True,
                        quotation=quotation,
                        quotation_pending=True,
                    )
                extra = {
                    "crm_opportunity_id": lead_id,
                    "won": True,
                    "quotation": quotation,
                }
                if quotation.get("sale_order_id"):
                    extra.update(
                        {
                            "sale_order_id": quotation["sale_order_id"],
                            "sale_order_name": quotation.get("sale_order_name"),
                            "sale_order_url": quotation.get("sale_order_url"),
                        }
                    )
                return self._mark_ok(opportunity, action, **extra)

            return self._mark_ok(
                opportunity,
                action,
                crm_opportunity_id=lead_id,
                won=False,
                quotation=None,
            )
        except Exception as exc:
            logger.exception("DGCP→Odoo sync_outcome failed %s", opportunity.id)
            return self._mark_pending(opportunity, action, str(exc))

    async def retry_sync(self, opportunity: DGCPOpportunity) -> dict[str, Any]:
        blob = self._sync_blob(opportunity)
        action = blob.get("last_action") or "ensure_opportunity"
        status = (opportunity.status or "").lower()
        if action in ("mark_won",) or status in ("awarded", "won"):
            return await self.sync_outcome(opportunity, won=True)
        if action in ("mark_lost",) or status == "lost":
            return await self.sync_outcome(opportunity, won=False)
        return await self.ensure_opportunity_on_prepare(opportunity)
