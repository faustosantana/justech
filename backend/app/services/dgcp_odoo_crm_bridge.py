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

# Campos custom Odoo (x_ vía API sin módulo; el addon preferido usa justech_*)
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
    # Identidad JAIOS (UUID Char — no confundir con create_uid Odoo)
    "x_justech_jaios_user_id": ("char", "Iniciado por (ID JAIOS)"),
    "x_justech_jaios_user_name": ("char", "Iniciado por (nombre)"),
    "x_justech_jaios_user_email": ("char", "Iniciado por (email)"),
    "x_justech_jaios_owner_id": ("char", "Responsable JAIOS (ID)"),
    "x_justech_jaios_owner_name": ("char", "Responsable JAIOS (nombre)"),
    "x_justech_jaios_owner_email": ("char", "Responsable JAIOS (email)"),
    "x_justech_jaios_last_sync_at": ("datetime", "Última sync JAIOS"),
    "x_justech_jaios_url": ("char", "URL JAIOS"),
    "x_justech_jaios_last_action_user_id": ("char", "Última acción JAIOS (ID)"),
    "x_justech_jaios_last_action_user_name": ("char", "Última acción JAIOS (nombre)"),
    "x_justech_jaios_last_action_at": ("datetime", "Última acción JAIOS (fecha)"),
    "x_justech_jaios_odoo_user_id": ("integer", "Usuario Odoo mapeado (info)"),
}

SO_FIELDS = {
    "x_justech_dgcp_code": ("char", "Licitación DGCP"),
    "x_justech_jaios_id": ("char", "ID JAIOS/DGCP"),
}

SO_LINE_FIELDS = {
    "x_justech_dgcp_code": ("char", "Código DGCP"),
    "x_justech_dgcp_line_number": ("integer", "Línea DGCP"),
    "x_justech_dgcp_original": ("char", "Descripción original DGCP"),
    "x_justech_match_confidence": ("float", "Confianza match"),
    "x_justech_match_method": ("char", "Método match"),
    "x_justech_jaios_approver_id": ("char", "Aprobó match (ID JAIOS)"),
}

# Keys that must not be overwritten once set (initiator)
_INITIATOR_PAYLOAD_KEYS = ("jaios_user_id", "jaios_user_name", "jaios_user_email")


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
        """Best-effort numeric RPE from company profiles. Never invent / never abort txn."""
        from sqlalchemy import text

        queries = [
            """
            select coalesce(
              nullif(trim(raw_json->>'rpe'), ''),
              nullif(trim(raw_json->>'proveedor_estado'), '')
            ) as rpe
            from jaios.licitador_company_profiles
            where tenant_id = :t and company_key = :k
            limit 1
            """,
        ]
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
                        raw = str(row[0]).strip()
                        # Solo RPE numérico confiable (evitar nombres de PDF, etc.)
                        digits = re.sub(r"\D", "", raw)
                        if digits and digits == raw.replace(" ", "").replace("-", ""):
                            return digits
                        if re.fullmatch(r"\d{4,12}", digits):
                            return digits
            except Exception:
                continue
        return None

    async def _load_user(self, user_id: uuid.UUID | None):
        if not user_id:
            return None
        from sqlalchemy import select
        from app.models.user import User

        return (
            await self.db.execute(select(User).where(User.id == user_id))
        ).scalar_one_or_none()

    async def _actor_identity(self) -> dict[str, str]:
        """Authenticated JAIOS principal (JWT → User). Never trust FE payloads."""
        user = await self._load_user(self.user_id)
        if not user:
            return {
                "id": str(self.user_id),
                "name": "",
                "email": "",
            }
        return {
            "id": str(user.id),
            "name": (user.full_name or "").strip(),
            "email": (user.email or "").strip(),
        }

    async def _owner_identity(self, opportunity: DGCPOpportunity) -> dict[str, str]:
        """Current responsible in JAIOS if set; else actor."""
        info = opportunity.full_info or {}
        raw = info.get("responsible_user_id") or info.get("assignee_user_id")
        owner_uuid: uuid.UUID | None = None
        if raw:
            try:
                owner_uuid = uuid.UUID(str(raw))
            except (ValueError, TypeError):
                owner_uuid = None
        if owner_uuid:
            user = await self._load_user(owner_uuid)
            if user:
                return {
                    "id": str(user.id),
                    "name": (user.full_name or "").strip()
                    or str(info.get("responsible_name") or ""),
                    "email": (user.email or "").strip(),
                }
        # Fallback display name from JSON if UUID missing
        actor = await self._actor_identity()
        if info.get("responsible_name") and not owner_uuid:
            return {
                "id": actor["id"],
                "name": str(info.get("responsible_name")),
                "email": actor["email"],
            }
        return actor

    def _jaios_opportunity_url(self, opportunity: DGCPOpportunity) -> str:
        from app.config import settings

        base = (settings.public_app_url or settings.frontend_url or "").rstrip("/")
        if not base:
            return ""
        return f"{base}/dgcp/{opportunity.id}"

    async def _map_odoo_user_by_email(self, client, email: str) -> int | None:
        """Informational only — unique email match → res.users id. Never set crm.lead.user_id."""
        email = (email or "").strip().lower()
        if not email or "@" not in email:
            return None
        try:
            rows = await client.search_read(
                "res.users",
                [("login", "=ilike", email), ("active", "in", [True, False])],
                ["id", "login"],
                limit=3,
            )
            if len(rows) == 1:
                return _as_int_id(rows[0]["id"])
            partners = await client.search_read(
                "res.partner",
                [("email", "=ilike", email), ("user_ids", "!=", False)],
                ["id", "user_ids"],
                limit=3,
            )
            user_ids = []
            for p in partners:
                for uid in p.get("user_ids") or []:
                    user_ids.append(_as_int_id(uid))
            user_ids = list(dict.fromkeys(user_ids))
            if len(user_ids) == 1:
                return user_ids[0]
        except Exception:
            logger.debug("odoo user email map failed", exc_info=True)
        return None

    async def _post_chatter(
        self,
        client,
        lead_id: int,
        body: str,
        *,
        opportunity: DGCPOpportunity,
        event_key: str,
    ) -> None:
        """Post mail note; skip duplicates for the same event_key (no retry spam)."""
        blob = self._sync_blob(opportunity)
        posted = set(blob.get("chatter_events") or [])
        if event_key in posted:
            return
        try:
            await client.execute_kw(
                "crm.lead",
                "message_post",
                [[lead_id]],
                {
                    "body": body,
                    "message_type": "comment",
                    "subtype_xmlid": "mail.mt_note",
                },
            )
            posted.add(event_key)
            blob["chatter_events"] = sorted(posted)[-40:]
            self._save_sync(opportunity, blob)
        except Exception:
            logger.warning("chatter post failed lead=%s event=%s", lead_id, event_key, exc_info=True)

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

    async def _crm_vals(
        self,
        client,
        opportunity: DGCPOpportunity,
        *,
        result: str | None = None,
        existing_lead: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        fields = await self._crm_fields(client)
        company_key = (opportunity.company or "").strip() or "justech"
        rpe = await self._rpe_for_company(company_key)
        actor = await self._actor_identity()
        owner = await self._owner_identity(opportunity)
        now = datetime.now(timezone.utc)
        publish = None
        if opportunity.created_at:
            publish = opportunity.created_at.date().isoformat()

        # Initiator: immutable if already set on lead
        existing_initiator = None
        if existing_lead:
            for fname in ("justech_jaios_user_id", "x_justech_jaios_user_id"):
                val = existing_lead.get(fname)
                if val:
                    existing_initiator = str(val)
                    break

        initiator_id = existing_initiator or actor["id"]
        initiator_name = actor["name"]
        initiator_email = actor["email"]
        if existing_initiator and existing_lead:
            for pair in (
                ("justech_jaios_user_name", "x_justech_jaios_user_name"),
                ("justech_jaios_user_email", "x_justech_jaios_user_email"),
            ):
                pass
            for fname in ("justech_jaios_user_name", "x_justech_jaios_user_name"):
                if existing_lead.get(fname):
                    initiator_name = str(existing_lead[fname])
                    break
            for fname in ("justech_jaios_user_email", "x_justech_jaios_user_email"):
                if existing_lead.get(fname):
                    initiator_email = str(existing_lead[fname])
                    break

        mapped_odoo = await self._map_odoo_user_by_email(client, actor["email"])

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
            "awarded_date": now.date().isoformat() if result == "adjudicada" else None,
            "jaios_user_id": initiator_id,
            "jaios_user_name": initiator_name,
            "jaios_user_email": initiator_email,
            "jaios_owner_id": owner["id"],
            "jaios_owner_name": owner["name"],
            "jaios_owner_email": owner["email"],
            "jaios_last_sync_at": now.strftime("%Y-%m-%d %H:%M:%S"),
            "jaios_url": self._jaios_opportunity_url(opportunity),
            "jaios_last_action_user_id": actor["id"],
            "jaios_last_action_user_name": actor["name"],
            "jaios_last_action_at": now.strftime("%Y-%m-%d %H:%M:%S"),
            "jaios_odoo_user_id": mapped_odoo,
        }
        # Do not overwrite initiator on updates
        if existing_initiator:
            for k in _INITIATOR_PAYLOAD_KEYS:
                # keep payload values we resolved from existing; already set above
                pass

        out: dict[str, Any] = {}
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
            "jaios_user_id": ("justech_jaios_user_id", "x_justech_jaios_user_id"),
            "jaios_user_name": ("justech_jaios_user_name", "x_justech_jaios_user_name"),
            "jaios_user_email": ("justech_jaios_user_email", "x_justech_jaios_user_email"),
            "jaios_owner_id": ("justech_jaios_owner_id", "x_justech_jaios_owner_id"),
            "jaios_owner_name": ("justech_jaios_owner_name", "x_justech_jaios_owner_name"),
            "jaios_owner_email": ("justech_jaios_owner_email", "x_justech_jaios_owner_email"),
            "jaios_last_sync_at": ("justech_jaios_last_sync_at", "x_justech_jaios_last_sync_at"),
            "jaios_url": ("justech_jaios_url", "x_justech_jaios_url"),
            "jaios_last_action_user_id": (
                "justech_jaios_last_action_user_id",
                "x_justech_jaios_last_action_user_id",
            ),
            "jaios_last_action_user_name": (
                "justech_jaios_last_action_user_name",
                "x_justech_jaios_last_action_user_name",
            ),
            "jaios_last_action_at": (
                "justech_jaios_last_action_at",
                "x_justech_jaios_last_action_at",
            ),
            "jaios_odoo_user_id": ("justech_jaios_odoo_user_id", "x_justech_jaios_odoo_user_id"),
        }
        for key, names in mapping.items():
            val = payload.get(key)
            if val in (None, ""):
                continue
            # Skip writing initiator fields if already present and this is an update
            # (values already equal to existing — still write same; safe)
            for name in names:
                if name in fields:
                    out[name] = val
                    break
        return out

    async def _read_lead_identity(self, client, lead_id: int) -> dict[str, Any]:
        fields = await self._crm_fields(client)
        want = [
            n
            for n in (
                "justech_jaios_user_id",
                "x_justech_jaios_user_id",
                "justech_jaios_user_name",
                "x_justech_jaios_user_name",
                "justech_jaios_user_email",
                "x_justech_jaios_user_email",
            )
            if n in fields
        ]
        if not want:
            return {}
        rows = await client.search_read("crm.lead", [("id", "=", lead_id)], want, limit=1)
        return rows[0] if rows else {}

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
        """Upsert crm.lead by (company + DGCP code). Idempotent. Initiator immutable."""
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

            existing_lead = None
            if existing_id:
                existing_lead = await self._read_lead_identity(client, _as_int_id(existing_id))

            custom = await self._crm_vals(
                client, opportunity, result=None, existing_lead=existing_lead
            )
            actor = await self._actor_identity()
            name = f"{opportunity.code} — {(opportunity.title or 'Licitación DGCP')[:120]}"
            description_parts = [
                f"Proceso DGCP: {opportunity.code}",
                f"JAIOS ID: {opportunity.id}",
                f"Institución: {opportunity.institution or '—'}",
                f"Empresa grupo: {opportunity.company or '—'}",
                f"Monto: {opportunity.amount or 0} {opportunity.currency or 'DOP'}",
                f"Estado: {opportunity.status}",
                f"Iniciado/actualizado por JAIOS: {actor.get('name') or actor.get('id')} <{actor.get('email') or ''}>",
            ]
            if opportunity.source_url:
                description_parts.append(f"Portal: {opportunity.source_url}")
            jaios_url = self._jaios_opportunity_url(opportunity)
            if jaios_url:
                description_parts.append(f"JAIOS: {jaios_url}")

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

            created = False
            if existing_id:
                lead_id = _as_int_id(existing_id)
                prev_owner = None
                for fname in ("justech_jaios_owner_id", "x_justech_jaios_owner_id"):
                    # re-read owner from lead before write
                    pass
                # Read owner before write for change detection
                fields = await self._crm_fields(client)
                own_fields = [
                    n
                    for n in ("justech_jaios_owner_id", "x_justech_jaios_owner_id", "justech_jaios_owner_name", "x_justech_jaios_owner_name")
                    if n in fields
                ]
                before = {}
                if own_fields:
                    rows_b = await client.search_read(
                        "crm.lead", [("id", "=", lead_id)], own_fields, limit=1
                    )
                    before = rows_b[0] if rows_b else {}
                await client.execute_kw("crm.lead", "write", [[lead_id], vals])
                owner = await self._owner_identity(opportunity)
                prev = before.get("justech_jaios_owner_id") or before.get("x_justech_jaios_owner_id")
                if prev and str(prev) != owner["id"]:
                    await self._post_chatter(
                        client,
                        lead_id,
                        (
                            f"Responsable JAIOS actualizado: "
                            f"<b>{before.get('justech_jaios_owner_name') or before.get('x_justech_jaios_owner_name') or prev}</b>"
                            f" → <b>{owner.get('name') or owner.get('id')}</b>."
                        ),
                        opportunity=opportunity,
                        event_key=f"owner_change:{prev}->{owner['id']}",
                    )
            else:
                lead_id = _as_int_id(await client.execute_kw("crm.lead", "create", [vals]))
                created = True
                rpe = await self._rpe_for_company((opportunity.company or "").strip() or "justech")
                email_bit = f" &lt;{actor.get('email')}&gt;" if actor.get("email") else ""
                await self._post_chatter(
                    client,
                    lead_id,
                    (
                        "<p>Esta oportunidad fue creada automáticamente desde <b>JAIOS Licitaciones</b>.</p>"
                        f"<ul>"
                        f"<li>Código DGCP: <b>{opportunity.code}</b></li>"
                        f"<li>Empresa: <b>{opportunity.company or '—'}</b></li>"
                        f"<li>RPE: <b>{rpe or 'RPE_PENDING'}</b></li>"
                        f"<li>Usuario JAIOS: <b>{actor.get('name') or actor.get('id')}</b>{email_bit}</li>"
                        f"<li>Fecha: {datetime.now(timezone.utc).isoformat()}</li>"
                        f"</ul>"
                    ),
                    opportunity=opportunity,
                    event_key="created_from_jaios",
                )

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
                jaios_user=actor,
                jaios_owner=await self._owner_identity(opportunity),
            )
        except Exception as exc:
            logger.exception("DGCP→Odoo ensure_opportunity failed %s", opportunity.id)
            await self.db.flush()
            return self._mark_pending(opportunity, action, str(exc))

    async def _map_product_lines(
        self, client, opportunity: DGCPOpportunity
    ) -> list[dict[str, Any]]:
        """Delegate to product match service; only MATCHED+approved become SO lines."""
        from app.services.dgcp_odoo_product_match_service import DGCPOdooProductMatchService

        svc = DGCPOdooProductMatchService(self.db, self.tenant_id, self.user_id)
        blob = (opportunity.full_info or {}).get("odoo_product_matches")
        if not blob or not (blob.get("lines")):
            await svc.run_match(opportunity)
        approved = svc.approved_matched_lines(opportunity)
        # Also expose full mapping for sync metadata
        all_lines = ((opportunity.full_info or {}).get("odoo_product_matches") or {}).get("lines") or []
        lines_out: list[dict[str, Any]] = []
        for m in all_lines:
            lines_out.append(
                {
                    "status": m.get("status"),
                    "product_id": m.get("suggested_product_id") if m.get("approved") else None,
                    "name": m.get("description") or m.get("suggested_product_name"),
                    "sku": m.get("reference") or m.get("suggested_default_code"),
                    "qty": m.get("quantity") or 1,
                    "price": m.get("estimated_price") or 0,
                    "approved": bool(m.get("approved")),
                    "line_number": m.get("line_number"),
                    "confidence": m.get("confidence"),
                    "match_method": m.get("match_method"),
                    "original_text": m.get("original_text"),
                    "approved_by": m.get("approved_by"),
                }
            )
        # Prefer approved for order creation
        if approved:
            return [
                {
                    "status": "MATCHED",
                    "product_id": m["suggested_product_id"],
                    "name": m.get("suggested_product_name") or m.get("description"),
                    "sku": m.get("suggested_default_code") or m.get("reference"),
                    "qty": m.get("quantity") or 1,
                    "price": m.get("estimated_price") or 0,
                    "line_number": m.get("line_number"),
                    "confidence": m.get("confidence"),
                    "match_method": m.get("match_method"),
                    "original_text": m.get("original_text"),
                    "approved_by": m.get("approved_by"),
                    "approved": True,
                }
                for m in approved
            ]
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
        matched = [
            m
            for m in mapped
            if m.get("status") == "MATCHED" and m.get("product_id") and m.get("approved")
        ]

        vals: dict[str, Any] = {
            "origin": opportunity.code,
            "opportunity_id": lead_id,
            "note": (
                f"Cotización borrador generada desde JAIOS al adjudicar {opportunity.code}.\n"
                f"Requiere revisión comercial antes de confirmar.\n"
                f"Líneas MATCHED aprobadas: {len(matched)}."
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
            return {
                "sale_order_id": None,
                "customer_required": True,
                "review_required": True,
                "partner": partner,
                "line_mapping": mapped,
                "error": "customer_required_for_quotation",
            }

        line_fields = await self._ensure_custom_fields(client, "sale.order.line", SO_LINE_FIELDS)
        order_lines = []
        for m in matched:
            line_vals: dict[str, Any] = {
                "product_id": m["product_id"],
                "name": m["name"] or "Línea DGCP",
                "product_uom_qty": m["qty"] or 1,
                "price_unit": float(m["price"] or 0),
            }
            if "x_justech_dgcp_code" in line_fields:
                line_vals["x_justech_dgcp_code"] = opportunity.code
            if "x_justech_dgcp_line_number" in line_fields and m.get("line_number") is not None:
                line_vals["x_justech_dgcp_line_number"] = int(m["line_number"])
            if "x_justech_dgcp_original" in line_fields and m.get("original_text"):
                line_vals["x_justech_dgcp_original"] = str(m["original_text"])[:500]
            if "x_justech_match_confidence" in line_fields and m.get("confidence") is not None:
                line_vals["x_justech_match_confidence"] = float(m["confidence"])
            if "x_justech_match_method" in line_fields and m.get("match_method"):
                line_vals["x_justech_match_method"] = str(m["match_method"])[:64]
            if "x_justech_jaios_approver_id" in line_fields and m.get("approved_by"):
                line_vals["x_justech_jaios_approver_id"] = str(m["approved_by"])
            order_lines.append((0, 0, line_vals))
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
            existing_lead = await self._read_lead_identity(client, lead_id)
            actor = await self._actor_identity()

            custom = await self._crm_vals(
                client,
                opportunity,
                result="adjudicada" if won else "no_adjudicada",
                existing_lead=existing_lead,
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

            label = "Adjudicada" if won else "No adjudicada"
            email_bit = f" ({actor.get('email')})" if actor.get("email") else ""
            await self._post_chatter(
                client,
                lead_id,
                (
                    f"Licitación marcada <b>{label}</b> en JAIOS por "
                    f"<b>{actor.get('name') or actor.get('id')}</b>{email_bit}."
                ),
                opportunity=opportunity,
                event_key=f"outcome:{'won' if won else 'lost'}",
            )

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
