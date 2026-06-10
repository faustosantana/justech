from __future__ import annotations

import re
import uuid
from datetime import date
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.schemas.odoo import (
    OdooCustomerResponse,
    OdooHealthResponse,
    OdooInvoiceResponse,
    OdooLastPriceResponse,
    OdooListResponse,
    OdooOpportunityResponse,
    OdooProductResponse,
    OdooProjectResponse,
    OdooPurchaseHistoryItem,
    OdooQuotationResponse,
    OdooSaleHistoryItem,
    OdooSummaryResponse,
    OdooTicketResponse,
    OdooVendorResponse,
)
from app.services.audit_service import AuditService
from app.services.odoo_company_service import OdooCompanyContextService
from integrations.odoo.client import OdooClient
from integrations.odoo.company_context import OdooCompanyContext, apply_company_domain
from integrations.odoo.config import OdooConfig
from integrations.odoo.exceptions import OdooConnectionError, OdooNotConfiguredError
from integrations.odoo.normalize import (
    odoo_bool,
    odoo_date,
    odoo_dec,
    odoo_float,
    odoo_m2o_id,
    odoo_m2o_name,
    odoo_m2o_name_opt,
    odoo_str,
    odoo_str_opt,
)
from integrations.odoo.safe_client import SafeOdooClient


class OdooService:
    def __init__(
        self,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        *,
        user_id: uuid.UUID | None = None,
    ):
        self.db = db
        self.tenant_id = tenant_id
        self.user_id = user_id
        self._company_id: int | None = None
        self._company_name: str | None = None
        self._company_ids: list[int] = []

    async def _bare_client(self) -> SafeOdooClient:
        return self._build_client(None)

    def _build_client(self, company_context: OdooCompanyContext | None) -> SafeOdooClient:
        audit = AuditService(self.db)

        async def audit_cb(action: str, model: str, details: dict) -> None:
            await audit.log(
                action=action,
                tenant_id=self.tenant_id,
                user_id=self.user_id,
                resource_type="odoo",
                details=details,
            )

        raw = OdooClient(
            str(self.tenant_id),
            OdooConfig(
                url=settings.odoo_url,
                database=settings.odoo_db,
                username=settings.odoo_username,
                api_key=settings.odoo_api_key,
            ),
        )
        return SafeOdooClient(
            raw,
            read_only=settings.odoo_read_only,
            audit_callback=audit_cb,
            company_context=company_context,
            jaios_user_id=self.user_id,
        )

    async def _resolve_company(self) -> OdooCompanyContext | None:
        if not self.user_id:
            return None
        from app.services.global_company_context_service import GlobalCompanyContextService

        global_svc = GlobalCompanyContextService(self.db, self.tenant_id, self.user_id)
        ctx = await global_svc.resolve_odoo_context()
        if ctx:
            self._company_id = ctx.company_id
            self._company_ids = list(ctx.allowed_company_ids)
            response = await global_svc.get_context()
            self._company_name = response.active_company_name
            return ctx
        svc = OdooCompanyContextService(
            self.db,
            self.tenant_id,
            self.user_id,
            odoo_client_factory=self._bare_client,
        )
        ctx_row = await svc.get_context_response()
        if ctx_row.selected and ctx_row.odoo_company_id:
            self._company_id = ctx_row.odoo_company_id
            self._company_name = ctx_row.odoo_company_name
            self._company_ids = [ctx_row.odoo_company_id]
            return await svc.get_active_odoo_context()
        return None

    async def _get_client(self) -> SafeOdooClient:
        company_ctx = await self._resolve_company()
        return self._build_client(company_ctx)

    def _domain(self, model: str, domain: list, *, shared: bool = False) -> list:
        ids = self._company_ids or ([self._company_id] if self._company_id else None)
        return apply_company_domain(
            domain,
            model,
            self._company_id,
            include_shared=shared,
            company_ids=ids,
        )

    def _not_connected_list(self) -> OdooListResponse:
        return OdooListResponse(
            items=[],
            total=0,
            connected=False,
            message="Odoo no conectado",
        )

    def _list_response(self, items: list, total: int) -> OdooListResponse:
        return OdooListResponse(items=items, total=total, company_id=self._company_id)

    def company_context_service(self) -> OdooCompanyContextService:
        if not self.user_id:
            raise ValueError("user_id required for company context operations")
        return OdooCompanyContextService(
            self.db,
            self.tenant_id,
            self.user_id,
            odoo_client_factory=self._bare_client,
        )

    async def health(self) -> OdooHealthResponse:
        client = await self._get_client()
        if not client.is_configured:
            return OdooHealthResponse(
                connected=False,
                read_only=settings.odoo_read_only,
                message="Odoo no conectado",
            )
        result = await client.test_connection()
        return OdooHealthResponse(
            connected=bool(result.get("connected")),
            read_only=settings.odoo_read_only,
            version=result.get("version"),
            database=result.get("database"),
            message="Conectado" if result.get("connected") else result.get("error", "Odoo no conectado"),
            active_company_id=self._company_id,
            active_company_name=self._company_name,
        )

    async def summary(self) -> OdooSummaryResponse:
        client = await self._get_client()
        if not client.is_configured:
            return OdooSummaryResponse(connected=False)
        try:
            inv_base = [
                ("move_type", "=", "out_invoice"),
                ("state", "=", "posted"),
                ("payment_state", "in", ["not_paid", "partial"]),
            ]
            overdue_base = inv_base + [("invoice_date_due", "<", date.today().isoformat())]
            return OdooSummaryResponse(
                connected=True,
                customers=await client.search_count(
                    "res.partner",
                    [("customer_rank", ">", 0)],
                ),
                products=await client.search_count(
                    "product.product",
                    self._domain("product.product", [("sale_ok", "=", True)], shared=True),
                ),
                open_invoices=await client.search_count(
                    "account.move",
                    self._domain("account.move", inv_base),
                ),
                overdue_invoices=await client.search_count(
                    "account.move",
                    self._domain("account.move", overdue_base),
                ),
                quotations=await client.search_count(
                    "sale.order",
                    self._domain("sale.order", [("state", "in", ["draft", "sent"])]),
                ),
                opportunities=await client.search_count(
                    "crm.lead",
                    self._domain("crm.lead", [("type", "=", "opportunity")]),
                ),
                projects=await client.search_count(
                    "project.project",
                    self._domain("project.project", []),
                ),
                company_id=self._company_id,
                company_name=self._company_name,
            )
        except (OdooNotConfiguredError, OdooConnectionError):
            return OdooSummaryResponse(connected=False)
        except Exception:
            return OdooSummaryResponse(connected=False)

    async def list_customers(self, *, search: str = "", limit: int = 50) -> OdooListResponse:
        client = await self._get_client()
        if not client.is_configured:
            return self._not_connected_list()
        domain: list = [("customer_rank", ">", 0)]
        if search:
            domain.append("|")
            domain.extend([("name", "ilike", search), ("vat", "ilike", search)])
        rows = await client.search_read(
            "res.partner",
            domain,
            ["name", "email", "phone", "vat", "city", "is_company"],
            limit=limit,
            order="name asc",
        )
        items = [
            OdooCustomerResponse(
                id=r["id"],
                name=odoo_str(r.get("name")),
                email=odoo_str_opt(r.get("email")),
                phone=odoo_str_opt(r.get("phone")),
                vat=odoo_str_opt(r.get("vat")),
                city=odoo_str_opt(r.get("city")),
                is_company=odoo_bool(r.get("is_company")),
            )
            for r in rows
        ]
        total = await client.search_count("res.partner", domain)
        return self._list_response(items, total)

    async def list_products(self, *, search: str = "", limit: int = 50) -> OdooListResponse:
        client = await self._get_client()
        if not client.is_configured:
            return self._not_connected_list()
        domain: list = [("sale_ok", "=", True)]
        if search:
            domain.append("|")
            domain.extend([("name", "ilike", search), ("default_code", "ilike", search)])
        domain = self._domain("product.product", domain, shared=True)
        rows = await client.search_read(
            "product.product",
            domain,
            ["name", "default_code", "list_price", "standard_price", "qty_available", "uom_id"],
            limit=limit,
            order="name asc",
        )
        items = [
            OdooProductResponse(
                id=r["id"],
                name=odoo_str(r.get("name")),
                default_code=odoo_str_opt(r.get("default_code")),
                list_price=odoo_dec(r.get("list_price")),
                standard_price=odoo_dec(r.get("standard_price")),
                qty_available=odoo_float(r.get("qty_available")),
                uom=odoo_m2o_name_opt(r.get("uom_id")),
            )
            for r in rows
        ]
        total = await client.search_count("product.product", domain)
        return self._list_response(items, total)

    async def sales_history(
        self,
        *,
        partner_id: int | None = None,
        product_id: int | None = None,
        limit: int = 50,
    ) -> OdooListResponse:
        client = await self._get_client()
        if not client.is_configured:
            return self._not_connected_list()
        domain: list = [("order_id.state", "in", ["sale", "done"])]
        if partner_id:
            domain.append(("order_partner_id", "=", partner_id))
        if product_id:
            domain.append(("product_id", "=", product_id))
        domain = self._domain("sale.order.line", domain)
        line_fields = [
            "order_id",
            "order_partner_id",
            "product_id",
            "name",
            "product_uom_qty",
            "price_unit",
            "price_subtotal",
        ]
        try:
            rows = await client.search_read(
                "sale.order.line",
                domain,
                line_fields + ["purchase_price"],
                limit=limit,
                order="id desc",
            )
        except OdooConnectionError:
            rows = await client.search_read(
                "sale.order.line",
                domain,
                line_fields,
                limit=limit,
                order="id desc",
            )
        items = []
        for r in rows:
            cost = odoo_dec(r.get("purchase_price")) if "purchase_price" in r else None
            price = odoo_dec(r.get("price_unit"))
            margin = (price - cost) if cost and cost > 0 else None
            margin_pct = float((margin / price * 100) if margin and price else 0) if margin else None
            items.append(
                OdooSaleHistoryItem(
                    id=r["id"],
                    order_name=odoo_m2o_name(r.get("order_id")),
                    partner_id=odoo_m2o_id(r.get("order_partner_id")),
                    partner_name=odoo_m2o_name(r.get("order_partner_id")),
                    product_id=odoo_m2o_id(r.get("product_id")),
                    product_name=odoo_m2o_name(r.get("product_id")) or odoo_str(r.get("name")),
                    quantity=odoo_float(r.get("product_uom_qty")),
                    unit_price=price,
                    subtotal=odoo_dec(r.get("price_subtotal")),
                    margin=margin,
                    margin_pct=margin_pct,
                )
            )
        total = await client.search_count("sale.order.line", domain)
        return self._list_response(items, total)

    def _product_terms_domain(self, terms: list[str]) -> list:
        clauses: list[tuple] = []
        for term in terms:
            if not term.strip():
                continue
            clauses.append(("product_id.name", "ilike", term))
            clauses.append(("name", "ilike", term))
            clauses.append(("product_id.default_code", "ilike", term))
        if not clauses:
            return []
        domain: list = []
        for i, clause in enumerate(clauses):
            if i < len(clauses) - 1:
                domain.append("|")
            domain.append(clause)
        return domain

    async def search_sales_by_product_terms(
        self,
        terms: list[str],
        *,
        limit: int = 500,
    ) -> OdooListResponse:
        """Líneas de venta confirmadas cuyo producto coincide con términos (read-only)."""
        client = await self._get_client()
        if not client.is_configured:
            return self._not_connected_list()
        term_domain = self._product_terms_domain(terms)
        if not term_domain:
            return OdooListResponse(items=[], total=0, connected=True, company_id=self._company_id)

        domain: list = [("order_id.state", "in", ["sale", "done"])] + term_domain
        domain = self._domain("sale.order.line", domain)
        line_fields = [
            "order_id",
            "order_partner_id",
            "product_id",
            "name",
            "product_uom_qty",
            "price_unit",
            "price_subtotal",
        ]
        rows = await client.search_read(
            "sale.order.line",
            domain,
            line_fields,
            limit=limit,
            order="id desc",
        )

        order_ids = list({odoo_m2o_id(r.get("order_id")) for r in rows if odoo_m2o_id(r.get("order_id"))})
        order_dates: dict[int, str | None] = {}
        if order_ids:
            order_rows = await client.search_read(
                "sale.order",
                self._domain("sale.order", [("id", "in", order_ids)]),
                ["id", "name", "date_order"],
                limit=len(order_ids),
            )
            for o in order_rows:
                order_dates[int(o["id"])] = odoo_date(o.get("date_order"))

        items = []
        for r in rows:
            oid = odoo_m2o_id(r.get("order_id"))
            items.append(
                OdooSaleHistoryItem(
                    id=r["id"],
                    order_name=odoo_m2o_name(r.get("order_id")),
                    order_date=order_dates.get(oid) if oid else None,
                    partner_id=odoo_m2o_id(r.get("order_partner_id")),
                    partner_name=odoo_m2o_name(r.get("order_partner_id")),
                    product_id=odoo_m2o_id(r.get("product_id")),
                    product_name=odoo_m2o_name(r.get("product_id")) or odoo_str(r.get("name")),
                    quantity=odoo_float(r.get("product_uom_qty")),
                    unit_price=odoo_dec(r.get("price_unit")),
                    subtotal=odoo_dec(r.get("price_subtotal")),
                )
            )
        total = await client.search_count("sale.order.line", domain)
        return self._list_response(items, total)

    async def search_purchases_by_product_terms(
        self,
        terms: list[str],
        *,
        limit: int = 500,
    ) -> OdooListResponse:
        """Líneas de compra confirmadas cuyo producto coincide con términos (read-only)."""
        client = await self._get_client()
        if not client.is_configured:
            return self._not_connected_list()
        term_domain = self._product_terms_domain(terms)
        if not term_domain:
            return OdooListResponse(items=[], total=0, connected=True, company_id=self._company_id)

        domain: list = [("order_id.state", "in", ["purchase", "done"])] + term_domain
        domain = self._domain("purchase.order.line", domain)
        try:
            rows = await client.search_read(
                "purchase.order.line",
                domain,
                ["order_id", "product_id", "name", "product_qty", "price_unit", "price_subtotal"],
                limit=limit,
                order="id desc",
            )
        except Exception:
            return OdooListResponse(
                items=[],
                total=0,
                connected=True,
                message="Módulo de compras no disponible",
                company_id=self._company_id,
            )

        order_ids = list({odoo_m2o_id(r.get("order_id")) for r in rows if odoo_m2o_id(r.get("order_id"))})
        order_meta: dict[int, dict] = {}
        if order_ids:
            order_rows = await client.search_read(
                "purchase.order",
                self._domain("purchase.order", [("id", "in", order_ids)]),
                ["id", "name", "date_order", "partner_id"],
                limit=len(order_ids),
            )
            for o in order_rows:
                order_meta[int(o["id"])] = o

        items = []
        for r in rows:
            oid = odoo_m2o_id(r.get("order_id"))
            order = order_meta.get(oid, {}) if oid else {}
            items.append(
                OdooPurchaseHistoryItem(
                    id=r["id"],
                    order_name=odoo_str(order.get("name")) or odoo_m2o_name(r.get("order_id")),
                    order_date=odoo_date(order.get("date_order")),
                    partner_name=odoo_m2o_name(order.get("partner_id")),
                    product_name=odoo_m2o_name(r.get("product_id")) or odoo_str(r.get("name")),
                    quantity=odoo_float(r.get("product_qty")),
                    unit_price=odoo_dec(r.get("price_unit")),
                    subtotal=odoo_dec(r.get("price_subtotal")),
                )
            )
        total = await client.search_count("purchase.order.line", domain)
        return self._list_response(items, total)

    async def search_purchases_by_vendor_name(
        self,
        vendor_name: str,
        *,
        limit: int = 500,
    ) -> tuple[list[OdooPurchaseHistoryItem], str | None]:
        client = await self._get_client()
        if not client.is_configured:
            return [], None
        vendors = await self.list_vendors(search=vendor_name, limit=5)
        if not vendors.items:
            return [], None
        vendor_id = vendors.items[0].id
        resolved = vendors.items[0].name
        resp = await self.purchase_history(partner_id=vendor_id, limit=limit)
        items = [i for i in resp.items if isinstance(i, OdooPurchaseHistoryItem)]
        return items, resolved

    async def _resolve_partner_id(
        self,
        partner_name: str,
        *,
        search_terms: list[str] | None = None,
    ) -> tuple[int | None, str | None]:
        client = await self._get_client()
        if not client.is_configured:
            return None, None
        candidates = [partner_name.strip()] + list(search_terms or [])
        seen: set[str] = set()
        best_id: int | None = None
        best_name: str | None = None
        best_score = -1

        for candidate in candidates:
            name = candidate.strip()
            if not name or name.lower() in seen:
                continue
            seen.add(name.lower())
            rows = await client.search_read(
                "res.partner",
                [("customer_rank", ">", 0), ("name", "ilike", name)],
                ["id", "name"],
                limit=8,
                order="name asc",
            )
            if not rows:
                continue
            lowered = name.lower()
            tokens = [t for t in re.split(r"[\s,\-]+", lowered) if len(t) >= 3]
            for row in rows:
                partner = odoo_str(row.get("name"))
                if not partner:
                    continue
                pl = partner.lower()
                score = 0
                if lowered in pl or pl in lowered:
                    score += 10
                score += sum(1 for t in tokens if t in pl)
                if score > best_score:
                    best_score = score
                    best_id = int(row["id"])
                    best_name = partner

        if best_id:
            return best_id, best_name
        return None, None

    async def search_sales_by_partner_name(
        self,
        partner_name: str,
        *,
        limit: int = 500,
        search_terms: list[str] | None = None,
    ) -> tuple[list[OdooSaleHistoryItem], str | None]:
        """Líneas de venta confirmadas de un cliente (read-only)."""
        client = await self._get_client()
        if not client.is_configured:
            return [], None
        partner_id, resolved_name = await self._resolve_partner_id(
            partner_name,
            search_terms=search_terms,
        )
        if not partner_id:
            return [], None

        domain: list = [
            ("order_id.state", "in", ["sale", "done"]),
            ("order_partner_id", "=", partner_id),
        ]
        domain = self._domain("sale.order.line", domain)
        line_fields = [
            "order_id",
            "order_partner_id",
            "product_id",
            "name",
            "product_uom_qty",
            "price_unit",
            "price_subtotal",
        ]
        rows = await client.search_read(
            "sale.order.line",
            domain,
            line_fields,
            limit=limit,
            order="id desc",
        )

        order_ids = list({odoo_m2o_id(r.get("order_id")) for r in rows if odoo_m2o_id(r.get("order_id"))})
        order_dates: dict[int, str | None] = {}
        if order_ids:
            order_rows = await client.search_read(
                "sale.order",
                self._domain("sale.order", [("id", "in", order_ids)]),
                ["id", "name", "date_order"],
                limit=len(order_ids),
            )
            for o in order_rows:
                order_dates[int(o["id"])] = odoo_date(o.get("date_order"))

        items = []
        for r in rows:
            oid = odoo_m2o_id(r.get("order_id"))
            items.append(
                OdooSaleHistoryItem(
                    id=r["id"],
                    order_name=odoo_m2o_name(r.get("order_id")),
                    order_date=order_dates.get(oid) if oid else None,
                    partner_id=odoo_m2o_id(r.get("order_partner_id")),
                    partner_name=odoo_m2o_name(r.get("order_partner_id")),
                    product_id=odoo_m2o_id(r.get("product_id")),
                    product_name=odoo_m2o_name(r.get("product_id")) or odoo_str(r.get("name")),
                    quantity=odoo_float(r.get("product_uom_qty")),
                    unit_price=odoo_dec(r.get("price_unit")),
                    subtotal=odoo_dec(r.get("price_subtotal")),
                )
            )
        return items, resolved_name

    async def last_price(
        self,
        *,
        partner_id: int | None = None,
        product_id: int | None = None,
        product_name: str | None = None,
        partner_name: str | None = None,
    ) -> OdooLastPriceResponse:
        client = await self._get_client()
        if not client.is_configured:
            return OdooLastPriceResponse()
        if product_name and not product_id:
            products = await client.search_read(
                "product.product",
                self._domain("product.product", [("name", "ilike", product_name)], shared=True),
                ["id"],
                limit=1,
            )
            if products:
                product_id = products[0]["id"]
        if partner_name and not partner_id:
            partners = await client.search_read(
                "res.partner", [("name", "ilike", partner_name)], ["id"], limit=1
            )
            if partners:
                partner_id = partners[0]["id"]
        domain: list = [("order_id.state", "in", ["sale", "done"])]
        if partner_id:
            domain.append(("order_partner_id", "=", partner_id))
        if product_id:
            domain.append(("product_id", "=", product_id))
        domain = self._domain("sale.order.line", domain)
        rows = await client.search_read(
            "sale.order.line",
            domain,
            ["order_id", "order_partner_id", "product_id", "price_unit"],
            limit=100,
            order="id desc",
        )
        if not rows:
            return OdooLastPriceResponse(
                product_name=product_name,
                partner_name=partner_name,
                sales_count=0,
            )
        prices = [odoo_dec(r.get("price_unit")) for r in rows]
        avg = sum(prices) / len(prices) if prices else None
        last = rows[0]
        order_rows = await client.search_read(
            "sale.order",
            self._domain("sale.order", [("id", "=", odoo_m2o_id(last.get("order_id")))]),
            ["name", "date_order"],
            limit=1,
        )
        order_date = order_rows[0].get("date_order") if order_rows else None
        return OdooLastPriceResponse(
            product_name=odoo_m2o_name_opt(last.get("product_id")) or product_name,
            partner_name=odoo_m2o_name_opt(last.get("order_partner_id")) or partner_name,
            unit_price=odoo_dec(last.get("price_unit")),
            min_price=min(prices) if prices else None,
            max_price=max(prices) if prices else None,
            order_date=odoo_date(order_date),
            order_name=odoo_m2o_name_opt(last.get("order_id")),
            average_price=avg,
            sales_count=len(rows),
        )

    async def list_vendors(self, *, search: str = "", limit: int = 50) -> OdooListResponse:
        client = await self._get_client()
        if not client.is_configured:
            return self._not_connected_list()
        domain: list = [("supplier_rank", ">", 0)]
        if search:
            domain.append("|")
            domain.extend([("name", "ilike", search), ("vat", "ilike", search)])
        rows = await client.search_read(
            "res.partner",
            domain,
            ["name", "email", "phone", "vat", "city"],
            limit=limit,
            order="name asc",
        )
        items = [
            OdooVendorResponse(
                id=r["id"],
                name=odoo_str(r.get("name")),
                email=odoo_str_opt(r.get("email")),
                phone=odoo_str_opt(r.get("phone")),
                vat=odoo_str_opt(r.get("vat")),
                city=odoo_str_opt(r.get("city")),
            )
            for r in rows
        ]
        total = await client.search_count("res.partner", domain)
        return self._list_response(items, total)

    async def product_purchase_history(
        self,
        *,
        product_id: int,
        limit: int = 50,
    ) -> OdooListResponse:
        client = await self._get_client()
        if not client.is_configured:
            return self._not_connected_list()
        domain = self._domain(
            "purchase.order.line",
            [("product_id", "=", product_id), ("order_id.state", "in", ["purchase", "done"])],
        )
        try:
            rows = await client.search_read(
                "purchase.order.line",
                domain,
                ["order_id", "product_id", "name", "product_qty", "price_unit", "price_subtotal"],
                limit=limit,
                order="id desc",
            )
        except Exception:
            return OdooListResponse(
                items=[],
                total=0,
                connected=True,
                message="Módulo de compras no disponible",
                company_id=self._company_id,
            )
        items = []
        for r in rows:
            order_id = odoo_m2o_id(r.get("order_id"))
            order_rows = await client.search_read(
                "purchase.order",
                self._domain("purchase.order", [("id", "=", order_id)]),
                ["name", "date_order", "partner_id"],
                limit=1,
            ) if order_id else []
            order = order_rows[0] if order_rows else {}
            items.append(
                OdooPurchaseHistoryItem(
                    id=r["id"],
                    order_name=odoo_str(order.get("name")) or odoo_m2o_name(r.get("order_id")),
                    order_date=odoo_date(order.get("date_order")),
                    partner_name=odoo_m2o_name(order.get("partner_id")),
                    product_name=odoo_m2o_name(r.get("product_id")) or odoo_str(r.get("name")),
                    quantity=odoo_float(r.get("product_qty")),
                    unit_price=odoo_dec(r.get("price_unit")),
                    subtotal=odoo_dec(r.get("price_subtotal")),
                )
            )
        total = await client.search_count("purchase.order.line", domain)
        return self._list_response(items, total)

    async def open_invoices(self, *, partner_id: int | None = None, limit: int = 50) -> OdooListResponse:
        return await self._list_invoices(partner_id=partner_id, limit=limit, overdue_only=False)

    async def overdue_invoices(self, *, partner_id: int | None = None, limit: int = 50) -> OdooListResponse:
        return await self._list_invoices(partner_id=partner_id, limit=limit, overdue_only=True)

    async def _list_invoices(
        self,
        *,
        partner_id: int | None,
        limit: int,
        overdue_only: bool,
    ) -> OdooListResponse:
        client = await self._get_client()
        if not client.is_configured:
            return self._not_connected_list()
        domain: list = [
            ("move_type", "=", "out_invoice"),
            ("state", "=", "posted"),
            ("payment_state", "in", ["not_paid", "partial"]),
        ]
        if partner_id:
            domain.append(("partner_id", "=", partner_id))
        if overdue_only:
            domain.append(("invoice_date_due", "<", date.today().isoformat()))
        domain = self._domain("account.move", domain)
        rows = await client.search_read(
            "account.move",
            domain,
            ["name", "partner_id", "invoice_date", "invoice_date_due", "amount_total", "amount_residual", "currency_id", "state", "payment_state"],
            limit=limit,
            order="invoice_date_due asc",
        )
        items = [
            OdooInvoiceResponse(
                id=r["id"],
                name=odoo_str(r.get("name")),
                partner_name=odoo_m2o_name(r.get("partner_id")),
                invoice_date=odoo_date(r.get("invoice_date")),
                due_date=odoo_date(r.get("invoice_date_due")),
                amount_total=odoo_dec(r.get("amount_total")),
                amount_residual=odoo_dec(r.get("amount_residual")),
                currency=odoo_m2o_name(r.get("currency_id")) or "DOP",
                state=odoo_str(r.get("state")),
                payment_state=odoo_str_opt(r.get("payment_state")),
            )
            for r in rows
        ]
        total = await client.search_count("account.move", domain)
        return self._list_response(items, total)

    async def list_quotations(self, *, partner_id: int | None = None, limit: int = 50) -> OdooListResponse:
        client = await self._get_client()
        if not client.is_configured:
            return self._not_connected_list()
        domain: list = [("state", "in", ["draft", "sent"])]
        if partner_id:
            domain.append(("partner_id", "=", partner_id))
        domain = self._domain("sale.order", domain)
        rows = await client.search_read(
            "sale.order",
            domain,
            ["name", "partner_id", "date_order", "amount_total", "state", "currency_id", "user_id", "company_id", "validity_date"],
            limit=limit,
            order="date_order desc",
        )
        items = [
            OdooQuotationResponse(
                id=r["id"],
                name=odoo_str(r.get("name")),
                partner_id=odoo_m2o_id(r.get("partner_id")),
                partner_name=odoo_m2o_name(r.get("partner_id")),
                date_order=odoo_date(r.get("date_order")),
                amount_total=odoo_dec(r.get("amount_total")),
                currency=odoo_m2o_name(r.get("currency_id")) or "DOP",
                state=odoo_str(r.get("state")),
                user_id=odoo_m2o_id(r.get("user_id")),
                salesperson_name=odoo_m2o_name_opt(r.get("user_id")),
                company_id=odoo_m2o_id(r.get("company_id")),
                company_name=odoo_m2o_name_opt(r.get("company_id")),
                validity_date=odoo_date(r.get("validity_date")),
            )
            for r in rows
        ]
        total = await client.search_count("sale.order", domain)
        return self._list_response(items, total)

    async def list_opportunities(self, *, partner_id: int | None = None, limit: int = 50) -> OdooListResponse:
        client = await self._get_client()
        if not client.is_configured:
            return self._not_connected_list()
        domain: list = [("type", "=", "opportunity")]
        if partner_id:
            domain.append(("partner_id", "=", partner_id))
        domain = self._domain("crm.lead", domain)
        rows = await client.search_read(
            "crm.lead",
            domain,
            ["name", "partner_id", "expected_revenue", "probability", "stage_id", "date_deadline"],
            limit=limit,
            order="create_date desc",
        )
        items = [
            OdooOpportunityResponse(
                id=r["id"],
                name=odoo_str(r.get("name")),
                partner_name=odoo_m2o_name_opt(r.get("partner_id")),
                expected_revenue=odoo_dec(r.get("expected_revenue")),
                probability=odoo_float(r.get("probability")),
                stage=odoo_m2o_name_opt(r.get("stage_id")),
                date_deadline=odoo_date(r.get("date_deadline")),
            )
            for r in rows
        ]
        total = await client.search_count("crm.lead", domain)
        return self._list_response(items, total)

    async def list_projects(self, *, partner_id: int | None = None, limit: int = 50) -> OdooListResponse:
        client = await self._get_client()
        if not client.is_configured:
            return self._not_connected_list()
        domain: list = []
        if partner_id:
            domain.append(("partner_id", "=", partner_id))
        domain = self._domain("project.project", domain)
        rows = await client.search_read(
            "project.project",
            domain,
            ["name", "partner_id", "stage_id"],
            limit=limit,
            order="name asc",
        )
        items = [
            OdooProjectResponse(
                id=r["id"],
                name=odoo_str(r.get("name")),
                partner_name=odoo_m2o_name_opt(r.get("partner_id")),
                stage=odoo_m2o_name_opt(r.get("stage_id")),
            )
            for r in rows
        ]
        total = await client.search_count("project.project", domain)
        return self._list_response(items, total)

    async def purchase_history(self, *, partner_id: int | None = None, limit: int = 50) -> OdooListResponse:
        client = await self._get_client()
        if not client.is_configured:
            return self._not_connected_list()
        domain: list = [("order_id.state", "in", ["purchase", "done"])]
        if partner_id:
            domain.append(("order_id.partner_id", "=", partner_id))
        domain = self._domain("purchase.order.line", domain)
        try:
            rows = await client.search_read(
                "purchase.order.line",
                domain,
                ["order_id", "product_id", "name", "product_qty", "price_unit", "price_subtotal"],
                limit=limit,
                order="id desc",
            )
        except Exception:
            return OdooListResponse(
                items=[],
                total=0,
                connected=True,
                message="Módulo de compras no disponible",
                company_id=self._company_id,
            )
        items = []
        for r in rows:
            order_id = odoo_m2o_id(r.get("order_id"))
            order_rows = await client.search_read(
                "purchase.order",
                self._domain("purchase.order", [("id", "=", order_id)]),
                ["name", "date_order", "partner_id"],
                limit=1,
            ) if order_id else []
            order = order_rows[0] if order_rows else {}
            items.append(
                OdooPurchaseHistoryItem(
                    id=r["id"],
                    order_name=odoo_str(order.get("name")) or odoo_m2o_name(r.get("order_id")),
                    order_date=odoo_date(order.get("date_order")),
                    partner_name=odoo_m2o_name(order.get("partner_id")),
                    product_name=odoo_m2o_name(r.get("product_id")) or odoo_str(r.get("name")),
                    quantity=odoo_float(r.get("product_qty")),
                    unit_price=odoo_dec(r.get("price_unit")),
                    subtotal=odoo_dec(r.get("price_subtotal")),
                )
            )
        total = await client.search_count("purchase.order.line", domain)
        return self._list_response(items, total)

    async def list_tickets(self, *, partner_id: int | None = None, limit: int = 50) -> OdooListResponse:
        client = await self._get_client()
        if not client.is_configured:
            return self._not_connected_list()
        domain: list = []
        if partner_id:
            domain.append(("partner_id", "=", partner_id))
        domain = self._domain("helpdesk.ticket", domain)
        try:
            rows = await client.search_read(
                "helpdesk.ticket",
                domain,
                ["name", "partner_id", "stage_id", "priority"],
                limit=limit,
                order="create_date desc",
            )
        except Exception:
            return OdooListResponse(
                items=[],
                total=0,
                connected=True,
                message="Helpdesk no disponible en Odoo",
                company_id=self._company_id,
            )
        items = [
            OdooTicketResponse(
                id=r["id"],
                name=odoo_str(r.get("name")),
                partner_name=odoo_m2o_name_opt(r.get("partner_id")),
                stage=odoo_m2o_name_opt(r.get("stage_id")),
                priority=odoo_str_opt(r.get("priority")),
            )
            for r in rows
        ]
        total = await client.search_count("helpdesk.ticket", domain)
        return self._list_response(items, total)

    async def _partner_ids_for_search(self, search: str, *, limit: int = 20) -> list[int]:
        if not search.strip():
            return []
        client = await self._get_client()
        if not client.is_configured:
            return []
        domain = self._domain(
            "res.partner",
            ["|", ("name", "ilike", search), ("vat", "ilike", search)],
        )
        rows = await client.search_read("res.partner", domain, ["id"], limit=limit)
        return [int(r["id"]) for r in rows]

    def _text_search_domain(self, search: str, partner_ids: list[int]) -> list:
        if not search.strip():
            return []
        if partner_ids:
            return ["|", ("name", "ilike", search), ("partner_id", "in", partner_ids)]
        return [("name", "ilike", search)]

    async def search_invoices(self, *, search: str = "", limit: int = 10) -> OdooListResponse:
        client = await self._get_client()
        if not client.is_configured:
            return self._not_connected_list()
        partner_ids = await self._partner_ids_for_search(search)
        domain: list = [("move_type", "=", "out_invoice")]
        domain.extend(self._text_search_domain(search, partner_ids))
        domain = self._domain("account.move", domain)
        rows = await client.search_read(
            "account.move",
            domain,
            ["name", "partner_id", "invoice_date", "invoice_date_due", "amount_total", "amount_residual", "currency_id", "state", "payment_state"],
            limit=limit,
            order="invoice_date desc",
        )
        items = [
            OdooInvoiceResponse(
                id=r["id"],
                name=odoo_str(r.get("name")),
                partner_name=odoo_m2o_name(r.get("partner_id")),
                invoice_date=odoo_date(r.get("invoice_date")),
                due_date=odoo_date(r.get("invoice_date_due")),
                amount_total=odoo_dec(r.get("amount_total")),
                amount_residual=odoo_dec(r.get("amount_residual")),
                currency=odoo_m2o_name(r.get("currency_id")) or "DOP",
                state=odoo_str(r.get("state")),
                payment_state=odoo_str_opt(r.get("payment_state")),
            )
            for r in rows
        ]
        total = await client.search_count("account.move", domain)
        return self._list_response(items, total)

    async def search_quotations(self, *, search: str = "", limit: int = 10) -> OdooListResponse:
        client = await self._get_client()
        if not client.is_configured:
            return self._not_connected_list()
        partner_ids = await self._partner_ids_for_search(search)
        domain: list = []
        domain.extend(self._text_search_domain(search, partner_ids))
        domain = self._domain("sale.order", domain)
        rows = await client.search_read(
            "sale.order",
            domain,
            ["name", "partner_id", "date_order", "amount_total", "state", "currency_id", "user_id", "company_id", "validity_date"],
            limit=limit,
            order="date_order desc",
        )
        items = [
            OdooQuotationResponse(
                id=r["id"],
                name=odoo_str(r.get("name")),
                partner_id=odoo_m2o_id(r.get("partner_id")),
                partner_name=odoo_m2o_name(r.get("partner_id")),
                date_order=odoo_date(r.get("date_order")),
                amount_total=odoo_dec(r.get("amount_total")),
                currency=odoo_m2o_name(r.get("currency_id")) or "DOP",
                state=odoo_str(r.get("state")),
                user_id=odoo_m2o_id(r.get("user_id")),
                salesperson_name=odoo_m2o_name_opt(r.get("user_id")),
                company_id=odoo_m2o_id(r.get("company_id")),
                company_name=odoo_m2o_name_opt(r.get("company_id")),
                validity_date=odoo_date(r.get("validity_date")),
            )
            for r in rows
        ]
        total = await client.search_count("sale.order", domain)
        return self._list_response(items, total)

    async def search_opportunities(self, *, search: str = "", limit: int = 10) -> OdooListResponse:
        client = await self._get_client()
        if not client.is_configured:
            return self._not_connected_list()
        partner_ids = await self._partner_ids_for_search(search)
        domain: list = [("type", "=", "opportunity")]
        domain.extend(self._text_search_domain(search, partner_ids))
        domain = self._domain("crm.lead", domain)
        rows = await client.search_read(
            "crm.lead",
            domain,
            ["name", "partner_id", "expected_revenue", "probability", "stage_id", "date_deadline"],
            limit=limit,
            order="create_date desc",
        )
        items = [
            OdooOpportunityResponse(
                id=r["id"],
                name=odoo_str(r.get("name")),
                partner_name=odoo_m2o_name_opt(r.get("partner_id")),
                expected_revenue=odoo_dec(r.get("expected_revenue")),
                probability=odoo_float(r.get("probability")),
                stage=odoo_m2o_name_opt(r.get("stage_id")),
                date_deadline=odoo_date(r.get("date_deadline")),
            )
            for r in rows
        ]
        total = await client.search_count("crm.lead", domain)
        return self._list_response(items, total)

    async def search_projects(self, *, search: str = "", limit: int = 10) -> OdooListResponse:
        client = await self._get_client()
        if not client.is_configured:
            return self._not_connected_list()
        partner_ids = await self._partner_ids_for_search(search)
        domain: list = []
        domain.extend(self._text_search_domain(search, partner_ids))
        domain = self._domain("project.project", domain)
        rows = await client.search_read(
            "project.project",
            domain,
            ["name", "partner_id", "stage_id"],
            limit=limit,
            order="name asc",
        )
        items = [
            OdooProjectResponse(
                id=r["id"],
                name=odoo_str(r.get("name")),
                partner_name=odoo_m2o_name_opt(r.get("partner_id")),
                stage=odoo_m2o_name_opt(r.get("stage_id")),
            )
            for r in rows
        ]
        total = await client.search_count("project.project", domain)
        return self._list_response(items, total)
