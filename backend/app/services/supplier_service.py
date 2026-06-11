"""Servicio — Directorio inteligente de proveedores."""

from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.business_company import BusinessCompany
from app.models.price_list import PriceListFile, PriceListProduct
from app.models.supplier import (
    SupplierCategory,
    SupplierCategoryLink,
    SupplierInteraction,
    SupplierPriceListLink,
)
from app.schemas.supplier import (
    SupplierCategoryCreate,
    SupplierCategoryListResponse,
    SupplierCategoryResponse,
    SupplierCategoryUpdate,
    SupplierCreate,
    SupplierDashboardStats,
    SupplierImportRequest,
    SupplierImportResponse,
    SupplierInteractionResponse,
    SupplierListResponse,
    SupplierPriceListSummary,
    SupplierQuoteRequest,
    SupplierQuoteResponse,
    SupplierResponse,
    SupplierSearchMatch,
    SupplierSearchRequest,
    SupplierSearchResponse,
    SupplierTenderSuggestion,
    SupplierTenderSuggestionRequest,
    SupplierTenderSuggestionResponse,
    SupplierUpdate,
)
from app.services.supplier_category_seed import (
    BASE_SUPPLIER_CATEGORIES,
    TENDER_REQUIREMENT_KEYWORDS,
    slugify,
)


class SupplierService:
    def __init__(self, db: AsyncSession, tenant_id: uuid.UUID, user_id: uuid.UUID | None = None):
        self.db = db
        self.tenant_id = tenant_id
        self.user_id = user_id

    # --- Categories ---

    async def ensure_base_categories(self) -> int:
        existing = await self.db.execute(
            select(func.count(SupplierCategory.id)).where(SupplierCategory.tenant_id == self.tenant_id)
        )
        if int(existing.scalar() or 0) > 0:
            return 0
        created = 0
        for item in BASE_SUPPLIER_CATEGORIES:
            slug = slugify(item["name"])
            self.db.add(
                SupplierCategory(
                    tenant_id=self.tenant_id,
                    name=item["name"],
                    slug=slug,
                    synonyms=item.get("synonyms", []),
                )
            )
            created += 1
        await self.db.commit()
        return created

    async def list_categories(self, *, active_only: bool = True) -> SupplierCategoryListResponse:
        stmt = select(SupplierCategory).where(SupplierCategory.tenant_id == self.tenant_id)
        if active_only:
            stmt = stmt.where(SupplierCategory.is_active.is_(True))
        result = await self.db.execute(stmt.order_by(SupplierCategory.name.asc()))
        items = [SupplierCategoryResponse.model_validate(r) for r in result.scalars().all()]
        return SupplierCategoryListResponse(items=items, total=len(items))

    async def create_category(self, payload: SupplierCategoryCreate) -> SupplierCategoryResponse:
        slug = payload.slug or slugify(payload.name)
        row = SupplierCategory(
            tenant_id=self.tenant_id,
            name=payload.name,
            slug=slug,
            description=payload.description,
            synonyms=payload.synonyms,
            parent_id=payload.parent_id,
            is_active=payload.is_active,
        )
        self.db.add(row)
        await self.db.commit()
        await self.db.refresh(row)
        return SupplierCategoryResponse.model_validate(row)

    async def update_category(
        self, category_id: uuid.UUID, payload: SupplierCategoryUpdate
    ) -> SupplierCategoryResponse | None:
        row = await self._get_category(category_id)
        if not row:
            return None
        for key, value in payload.model_dump(exclude_unset=True).items():
            if key == "slug" and value is None:
                continue
            setattr(row, key, value)
        if payload.name and not payload.slug:
            row.slug = slugify(payload.name)
        await self.db.commit()
        await self.db.refresh(row)
        return SupplierCategoryResponse.model_validate(row)

    async def _get_category(self, category_id: uuid.UUID) -> SupplierCategory | None:
        result = await self.db.execute(
            select(SupplierCategory).where(
                SupplierCategory.tenant_id == self.tenant_id,
                SupplierCategory.id == category_id,
            )
        )
        return result.scalar_one_or_none()

    # --- Suppliers CRUD ---

    async def list_suppliers(
        self,
        *,
        company_type: str | None = None,
        status: str | None = None,
        category_id: uuid.UUID | None = None,
        brand: str | None = None,
        search: str = "",
        limit: int = 100,
        offset: int = 0,
    ) -> SupplierListResponse:
        stmt = select(BusinessCompany).where(BusinessCompany.tenant_id == self.tenant_id)
        count_stmt = select(func.count(BusinessCompany.id)).where(BusinessCompany.tenant_id == self.tenant_id)

        if company_type:
            stmt = stmt.where(BusinessCompany.company_type == company_type)
            count_stmt = count_stmt.where(BusinessCompany.company_type == company_type)
        if status:
            stmt = stmt.where(BusinessCompany.status == status)
            count_stmt = count_stmt.where(BusinessCompany.status == status)
        if category_id:
            stmt = stmt.join(
                SupplierCategoryLink,
                SupplierCategoryLink.supplier_id == BusinessCompany.id,
            ).where(SupplierCategoryLink.category_id == category_id)
            count_stmt = count_stmt.join(
                SupplierCategoryLink,
                SupplierCategoryLink.supplier_id == BusinessCompany.id,
            ).where(SupplierCategoryLink.category_id == category_id)
        if brand and brand.strip():
            brand_val = brand.strip()
            stmt = stmt.where(BusinessCompany.brands.contains([brand_val]))
            count_stmt = count_stmt.where(BusinessCompany.brands.contains([brand_val]))
        if search.strip():
            pattern = f"%{search.strip()}%"
            filt = or_(
                BusinessCompany.name.ilike(pattern),
                BusinessCompany.legal_name.ilike(pattern),
                BusinessCompany.tax_id.ilike(pattern),
                BusinessCompany.email.ilike(pattern),
                BusinessCompany.primary_contact.ilike(pattern),
                BusinessCompany.category.ilike(pattern),
                BusinessCompany.notes.ilike(pattern),
            )
            stmt = stmt.where(filt)
            count_stmt = count_stmt.where(filt)

        total = int((await self.db.execute(count_stmt)).scalar() or 0)
        result = await self.db.execute(
            stmt.order_by(
                BusinessCompany.status == "preferido",
                BusinessCompany.internal_rating.desc().nullslast(),
                BusinessCompany.name.asc(),
            ).limit(limit).offset(offset)
        )
        rows = result.scalars().all()
        items = [await self._to_supplier_response(row) for row in rows]
        return SupplierListResponse(items=items, total=total)

    async def get_supplier(self, supplier_id: uuid.UUID) -> SupplierResponse | None:
        row = await self._get_supplier_row(supplier_id)
        return await self._to_supplier_response(row) if row else None

    async def create_supplier(self, payload: SupplierCreate) -> SupplierResponse:
        data = payload.model_dump(exclude={"category_ids"})
        row = BusinessCompany(tenant_id=self.tenant_id, **data)
        self.db.add(row)
        await self.db.flush()
        await self._sync_categories(row.id, payload.category_ids, payload.primary_category_id)
        await self.db.commit()
        await self.db.refresh(row)
        return await self._to_supplier_response(row)

    async def update_supplier(
        self, supplier_id: uuid.UUID, payload: SupplierUpdate
    ) -> SupplierResponse | None:
        row = await self._get_supplier_row(supplier_id)
        if not row:
            return None
        dump = payload.model_dump(exclude_unset=True, exclude={"category_ids"})
        for key, value in dump.items():
            setattr(row, key, value)
        if payload.category_ids is not None or payload.primary_category_id is not None:
            await self._sync_categories(
                supplier_id,
                payload.category_ids or await self._category_ids_for_supplier(supplier_id),
                payload.primary_category_id or row.primary_category_id,
            )
        await self.db.commit()
        await self.db.refresh(row)
        return await self._to_supplier_response(row)

    async def delete_supplier(self, supplier_id: uuid.UUID) -> bool:
        row = await self._get_supplier_row(supplier_id)
        if not row:
            return False
        row.status = "inactivo"
        await self.db.commit()
        return True

    async def mark_preferred(self, supplier_id: uuid.UUID, preferred: bool = True) -> SupplierResponse | None:
        row = await self._get_supplier_row(supplier_id)
        if not row:
            return None
        row.status = "preferido" if preferred else "activo"
        await self.db.commit()
        await self.db.refresh(row)
        return await self._to_supplier_response(row)

    # --- Dashboard ---

    async def dashboard_stats(self) -> SupplierDashboardStats:
        total_q = select(func.count(BusinessCompany.id)).where(BusinessCompany.tenant_id == self.tenant_id)
        active_q = total_q.where(BusinessCompany.status.in_(["activo", "preferido"]))
        preferred_q = total_q.where(BusinessCompany.status == "preferido")

        total = int((await self.db.execute(total_q)).scalar() or 0)
        active = int((await self.db.execute(active_q)).scalar() or 0)
        preferred = int((await self.db.execute(preferred_q)).scalar() or 0)

        type_rows = await self.db.execute(
            select(BusinessCompany.company_type, func.count(BusinessCompany.id))
            .where(BusinessCompany.tenant_id == self.tenant_id)
            .group_by(BusinessCompany.company_type)
        )
        by_type = {row[0]: int(row[1]) for row in type_rows.all()}

        cat_rows = await self.db.execute(
            select(SupplierCategory.name, func.count(SupplierCategoryLink.id))
            .join(SupplierCategoryLink, SupplierCategoryLink.category_id == SupplierCategory.id)
            .where(SupplierCategory.tenant_id == self.tenant_id)
            .group_by(SupplierCategory.name)
            .order_by(func.count(SupplierCategoryLink.id).desc())
            .limit(12)
        )
        by_category = [{"name": row[0], "count": int(row[1])} for row in cat_rows.all()]

        return SupplierDashboardStats(
            total_suppliers=total,
            active_suppliers=active,
            preferred_suppliers=preferred,
            by_type=by_type,
            by_category=by_category,
        )

    # --- Intelligent search ---

    async def search(self, payload: SupplierSearchRequest) -> SupplierSearchResponse:
        await self.ensure_base_categories()
        categories = await self._load_categories()
        tokens = self._tokenize(payload.query)
        matched_cats = self._match_categories(tokens, categories, payload.query)
        matched_brands = self._extract_brands(tokens, payload.query)

        stmt = select(BusinessCompany).where(
            BusinessCompany.tenant_id == self.tenant_id,
            BusinessCompany.status.in_(["activo", "preferido"]),
        )
        if payload.company_type:
            stmt = stmt.where(BusinessCompany.company_type == payload.company_type)
        if payload.status:
            stmt = stmt.where(BusinessCompany.status == payload.status)
        if payload.category_id:
            stmt = stmt.join(
                SupplierCategoryLink,
                SupplierCategoryLink.supplier_id == BusinessCompany.id,
            ).where(SupplierCategoryLink.category_id == payload.category_id)

        result = await self.db.execute(stmt)
        suppliers = result.scalars().all()

        matches: list[SupplierSearchMatch] = []
        for supplier in suppliers:
            score, terms, cat_names, brand_names, reason = self._score_supplier(
                supplier, tokens, matched_cats, matched_brands, payload.brand
            )
            if score <= 0:
                continue
            resp = await self._to_supplier_response(supplier)
            confidence = "high" if score >= 8 else "medium" if score >= 4 else "low"
            matches.append(
                SupplierSearchMatch(
                    supplier=resp,
                    score=score,
                    matched_terms=terms,
                    matched_categories=cat_names,
                    matched_brands=brand_names,
                    confidence=confidence,
                    recommendation_reason=reason,
                )
            )

        matches.sort(key=lambda m: (-m.score, -(m.supplier.internal_rating or 0)))
        if payload.limit:
            matches = matches[: payload.limit]

        return SupplierSearchResponse(
            query=payload.query,
            interpreted_categories=[c.name for c in matched_cats],
            interpreted_brands=matched_brands,
            results=matches,
            total=len(matches),
        )

    # --- Import ---

    async def import_suppliers(self, payload: SupplierImportRequest) -> SupplierImportResponse:
        created = updated = skipped = 0
        errors: list[str] = []

        for idx, row in enumerate(payload.rows):
            name = (row.get("name") or row.get("nombre") or row.get("nombre_comercial") or "").strip()
            if not name:
                skipped += 1
                continue
            tax_id = (row.get("tax_id") or row.get("rnc") or row.get("cedula") or "").strip() or None
            existing = await self._find_by_name_or_tax(name, tax_id)
            if existing and not payload.dry_run:
                for field, keys in (
                    ("email", ("email", "correo")),
                    ("phone", ("phone", "telefono", "teléfono")),
                    ("whatsapp", ("whatsapp",)),
                    ("primary_contact", ("contacto", "contacto_principal")),
                    ("category", ("categoria", "categoría", "category")),
                ):
                    for key in keys:
                        if row.get(key):
                            setattr(existing, field, str(row[key]).strip())
                if row.get("marcas") or row.get("brands"):
                    raw = row.get("marcas") or row.get("brands")
                    existing.brands = [b.strip() for b in str(raw).split(",") if b.strip()]
                updated += 1
            elif not existing and not payload.dry_run:
                self.db.add(
                    BusinessCompany(
                        tenant_id=self.tenant_id,
                        name=name,
                        company_type=str(row.get("company_type") or row.get("tipo") or "proveedor"),
                        tax_id=tax_id,
                        email=(row.get("email") or row.get("correo") or None),
                        phone=(row.get("phone") or row.get("telefono") or None),
                        whatsapp=row.get("whatsapp"),
                        primary_contact=row.get("contacto") or row.get("contacto_principal"),
                        category=row.get("categoria") or row.get("category"),
                        brands=[b.strip() for b in str(row.get("marcas") or row.get("brands") or "").split(",") if b.strip()],
                        status="activo",
                    )
                )
                created += 1
            elif payload.dry_run:
                if existing:
                    updated += 1
                else:
                    created += 1
            else:
                skipped += 1

        if not payload.dry_run:
            await self.db.commit()

        return SupplierImportResponse(created=created, updated=updated, skipped=skipped, errors=errors)

    # --- Quote request ---

    async def request_quote(
        self, supplier_id: uuid.UUID, payload: SupplierQuoteRequest
    ) -> SupplierQuoteResponse | None:
        row = await self._get_supplier_row(supplier_id)
        if not row:
            return None

        products_text = ", ".join(payload.products) if payload.products else "los productos solicitados"
        subject = payload.subject or f"Solicitud de cotización — {row.name}"
        default_message = (
            f"Buenos días,\n\n"
            f"Por favor envíennos cotización para: {products_text}.\n\n"
            f"Quedamos atentos.\n\nSaludos."
        )
        message = payload.message or default_message
        whatsapp_msg = f"Hola, necesito cotización para: {products_text}. Gracias."

        interaction = SupplierInteraction(
            tenant_id=self.tenant_id,
            supplier_id=supplier_id,
            user_id=self.user_id,
            interaction_type="quote_request",
            channel=payload.channel,
            subject=subject,
            body=message,
            metadata_json={"products": payload.products},
            created_at=datetime.now(timezone.utc),
        )
        self.db.add(interaction)
        row.last_quote_at = datetime.now(timezone.utc)
        await self.db.commit()
        await self.db.refresh(interaction)

        return SupplierQuoteResponse(
            supplier_id=supplier_id,
            subject=subject,
            email_body=message if payload.channel in ("email", "both") else None,
            whatsapp_message=whatsapp_msg if payload.channel in ("whatsapp", "both") else None,
            interaction_id=interaction.id,
        )

    # --- Price lists ---

    async def list_price_lists(self, supplier_id: uuid.UUID) -> list[SupplierPriceListSummary]:
        result = await self.db.execute(
            select(SupplierPriceListLink, PriceListFile)
            .join(PriceListFile, PriceListFile.id == SupplierPriceListLink.price_list_file_id)
            .where(
                SupplierPriceListLink.tenant_id == self.tenant_id,
                SupplierPriceListLink.supplier_id == supplier_id,
            )
            .order_by(SupplierPriceListLink.linked_at.desc())
        )
        summaries: list[SupplierPriceListSummary] = []
        for link, file_row in result.all():
            summaries.append(
                SupplierPriceListSummary(
                    id=link.id,
                    price_list_file_id=link.price_list_file_id,
                    filename=file_row.filename,
                    detected_brands=link.detected_brands or [],
                    detected_categories=link.detected_categories or [],
                    product_count=link.product_count or 0,
                    linked_at=link.linked_at,
                    file_modified_at=file_row.file_modified_at,
                )
            )
        return summaries

    async def link_price_list_file(self, supplier_id: uuid.UUID, file_id: uuid.UUID) -> SupplierPriceListSummary | None:
        supplier = await self._get_supplier_row(supplier_id)
        file_row = await self.db.execute(
            select(PriceListFile).where(
                PriceListFile.tenant_id == self.tenant_id,
                PriceListFile.id == file_id,
            )
        )
        price_file = file_row.scalar_one_or_none()
        if not supplier or not price_file:
            return None

        stats = await self.db.execute(
            select(
                func.count(PriceListProduct.id),
                func.array_agg(func.distinct(PriceListProduct.brand)),
                func.array_agg(func.distinct(PriceListProduct.category)),
            ).where(
                PriceListProduct.tenant_id == self.tenant_id,
                PriceListProduct.file_id == file_id,
                PriceListProduct.is_current.is_(True),
            )
        )
        count, brands, categories = stats.one()
        brands_clean = sorted({b for b in (brands or []) if b})
        cats_clean = sorted({c for c in (categories or []) if c})

        existing = await self.db.execute(
            select(SupplierPriceListLink).where(
                SupplierPriceListLink.supplier_id == supplier_id,
                SupplierPriceListLink.price_list_file_id == file_id,
            )
        )
        link = existing.scalar_one_or_none()
        if not link:
            link = SupplierPriceListLink(
                tenant_id=self.tenant_id,
                supplier_id=supplier_id,
                price_list_file_id=file_id,
                linked_at=datetime.now(timezone.utc),
            )
            self.db.add(link)
        link.detected_brands = brands_clean
        link.detected_categories = cats_clean
        link.product_count = int(count or 0)

        if not supplier.price_supplier_name and price_file.supplier:
            supplier.price_supplier_name = price_file.supplier

        await self.db.commit()
        await self.db.refresh(link)
        return SupplierPriceListSummary(
            id=link.id,
            price_list_file_id=link.price_list_file_id,
            filename=price_file.filename,
            detected_brands=link.detected_brands,
            detected_categories=link.detected_categories,
            product_count=link.product_count,
            linked_at=link.linked_at,
            file_modified_at=price_file.file_modified_at,
        )

    async def auto_link_price_file(self, file_id: uuid.UUID) -> uuid.UUID | None:
        """Detecta proveedor desde nombre de archivo/lista y vincula."""
        file_result = await self.db.execute(
            select(PriceListFile).where(
                PriceListFile.tenant_id == self.tenant_id,
                PriceListFile.id == file_id,
            )
        )
        price_file = file_result.scalar_one_or_none()
        if not price_file:
            return None

        supplier_name = (price_file.supplier or "").strip()
        if not supplier_name:
            supplier_name = self._guess_supplier_from_filename(price_file.filename)

        if not supplier_name:
            return None

        supplier = await self._find_by_name_or_tax(supplier_name, None)
        if not supplier:
            supplier = BusinessCompany(
                tenant_id=self.tenant_id,
                name=supplier_name,
                company_type="distribuidor" if "ingram" in supplier_name.lower() else "proveedor",
                price_supplier_name=supplier_name,
                status="activo",
            )
            self.db.add(supplier)
            await self.db.flush()

        await self.link_price_list_file(supplier.id, file_id)
        return supplier.id

    # --- Interactions ---

    async def list_interactions(self, supplier_id: uuid.UUID, limit: int = 50) -> list[SupplierInteractionResponse]:
        result = await self.db.execute(
            select(SupplierInteraction)
            .where(
                SupplierInteraction.tenant_id == self.tenant_id,
                SupplierInteraction.supplier_id == supplier_id,
            )
            .order_by(SupplierInteraction.created_at.desc())
            .limit(limit)
        )
        return [SupplierInteractionResponse.model_validate(r) for r in result.scalars().all()]

    # --- Tender suggestions ---

    async def suggest_for_tender(
        self, payload: SupplierTenderSuggestionRequest
    ) -> SupplierTenderSuggestionResponse:
        await self.ensure_base_categories()
        requirements = payload.requirements or []
        if payload.description:
            requirements = requirements + self._extract_tender_requirements(payload.description)

        search_text = " ".join(requirements)
        search_result = await self.search(
            SupplierSearchRequest(query=search_text, limit=payload.limit)
        )

        suggestions: list[SupplierTenderSuggestion] = []
        for match in search_result.results:
            suggestions.append(
                SupplierTenderSuggestion(
                    supplier=match.supplier,
                    score=match.score,
                    matched_requirements=match.matched_categories or match.matched_terms,
                    has_price_list=match.supplier.price_lists_count > 0,
                    last_quote_at=match.supplier.last_quote_at,
                )
            )

        return SupplierTenderSuggestionResponse(requirements=requirements, suggestions=suggestions)

    # --- Helpers ---

    async def _get_supplier_row(self, supplier_id: uuid.UUID) -> BusinessCompany | None:
        result = await self.db.execute(
            select(BusinessCompany).where(
                BusinessCompany.tenant_id == self.tenant_id,
                BusinessCompany.id == supplier_id,
            )
        )
        return result.scalar_one_or_none()

    async def _find_by_name_or_tax(self, name: str, tax_id: str | None) -> BusinessCompany | None:
        stmt = select(BusinessCompany).where(BusinessCompany.tenant_id == self.tenant_id)
        if tax_id:
            result = await self.db.execute(stmt.where(BusinessCompany.tax_id == tax_id))
            row = result.scalar_one_or_none()
            if row:
                return row
        result = await self.db.execute(stmt.where(func.lower(BusinessCompany.name) == name.lower()))
        return result.scalar_one_or_none()

    async def _category_ids_for_supplier(self, supplier_id: uuid.UUID) -> list[uuid.UUID]:
        result = await self.db.execute(
            select(SupplierCategoryLink.category_id).where(
                SupplierCategoryLink.tenant_id == self.tenant_id,
                SupplierCategoryLink.supplier_id == supplier_id,
            )
        )
        return list(result.scalars().all())

    async def _sync_categories(
        self,
        supplier_id: uuid.UUID,
        category_ids: list[uuid.UUID],
        primary_category_id: uuid.UUID | None,
    ) -> None:
        existing = await self.db.execute(
            select(SupplierCategoryLink).where(
                SupplierCategoryLink.tenant_id == self.tenant_id,
                SupplierCategoryLink.supplier_id == supplier_id,
            )
        )
        for link in existing.scalars().all():
            await self.db.delete(link)
        now = datetime.now(timezone.utc)
        for cat_id in set(category_ids):
            self.db.add(
                SupplierCategoryLink(
                    tenant_id=self.tenant_id,
                    supplier_id=supplier_id,
                    category_id=cat_id,
                    created_at=now,
                )
            )
        supplier = await self._get_supplier_row(supplier_id)
        if supplier:
            supplier.primary_category_id = primary_category_id

    async def _to_supplier_response(self, row: BusinessCompany) -> SupplierResponse:
        cat_result = await self.db.execute(
            select(SupplierCategory)
            .join(SupplierCategoryLink, SupplierCategoryLink.category_id == SupplierCategory.id)
            .where(
                SupplierCategoryLink.tenant_id == self.tenant_id,
                SupplierCategoryLink.supplier_id == row.id,
            )
        )
        categories = [SupplierCategoryResponse.model_validate(c) for c in cat_result.scalars().all()]

        pl_count = await self.db.execute(
            select(func.count(SupplierPriceListLink.id)).where(
                SupplierPriceListLink.tenant_id == self.tenant_id,
                SupplierPriceListLink.supplier_id == row.id,
            )
        )
        prod_count = await self.db.execute(
            select(func.coalesce(func.sum(SupplierPriceListLink.product_count), 0)).where(
                SupplierPriceListLink.tenant_id == self.tenant_id,
                SupplierPriceListLink.supplier_id == row.id,
            )
        )

        data = {
            "id": row.id,
            "name": row.name,
            "legal_name": row.legal_name,
            "company_type": row.company_type,
            "tax_id": row.tax_id,
            "email": row.email,
            "phone": row.phone,
            "whatsapp": row.whatsapp,
            "primary_contact": row.primary_contact,
            "website": row.website,
            "address": row.address,
            "city": row.city,
            "province": row.province,
            "country": row.country,
            "category": row.category,
            "primary_category_id": row.primary_category_id,
            "subcategories": row.subcategories or [],
            "brands": row.brands or [],
            "products_services": row.products_services or [],
            "payment_terms": row.payment_terms,
            "delivery_time": row.delivery_time,
            "currency": row.currency,
            "commercial_terms": row.commercial_terms,
            "notes": row.notes,
            "tags": row.tags or [],
            "status": row.status,
            "internal_rating": row.internal_rating,
            "odoo_partner_id": row.odoo_partner_id,
            "price_supplier_name": row.price_supplier_name,
            "last_purchase_at": row.last_purchase_at,
            "last_quote_at": row.last_quote_at,
            "created_at": row.created_at,
            "updated_at": row.updated_at,
            "category_ids": [c.id for c in categories],
            "categories": categories,
            "price_lists_count": int(pl_count.scalar() or 0),
            "products_indexed_count": int(prod_count.scalar() or 0),
        }
        return SupplierResponse.model_validate(data)

    async def _load_categories(self) -> list[SupplierCategory]:
        result = await self.db.execute(
            select(SupplierCategory).where(
                SupplierCategory.tenant_id == self.tenant_id,
                SupplierCategory.is_active.is_(True),
            )
        )
        return list(result.scalars().all())

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        return [t for t in re.findall(r"[a-záéíóúñ0-9]+", text.lower()) if len(t) > 2]

    def _match_categories(
        self, tokens: list[str], categories: list[SupplierCategory], raw_query: str
    ) -> list[SupplierCategory]:
        matched: list[SupplierCategory] = []
        q_lower = raw_query.lower()
        for cat in categories:
            terms = [cat.name.lower(), cat.slug.replace("-", " ")] + [s.lower() for s in cat.synonyms]
            if any(term in q_lower for term in terms):
                matched.append(cat)
                continue
            if any(token in " ".join(terms) for token in tokens):
                matched.append(cat)
        return matched

    @staticmethod
    def _extract_brands(tokens: list[str], raw_query: str) -> list[str]:
        known = [
            "hp", "dell", "lenovo", "hikvision", "dahua", "ubiquiti", "microsoft",
            "cisco", "fortinet", "ingram", "samsung", "canon", "epson", "brother",
        ]
        found = [b for b in known if b in raw_query.lower()]
        for token in tokens:
            if token in known and token not in found:
                found.append(token)
        return found

    def _score_supplier(
        self,
        supplier: BusinessCompany,
        tokens: list[str],
        matched_cats: list[SupplierCategory],
        matched_brands: list[str],
        brand_filter: str | None,
    ) -> tuple[float, list[str], list[str], list[str], str | None]:
        score = 0.0
        terms: list[str] = []
        cat_names: list[str] = []
        brand_names: list[str] = []
        reasons: list[str] = []

        searchable = " ".join(
            filter(
                None,
                [
                    supplier.name,
                    supplier.legal_name,
                    supplier.category,
                    supplier.notes,
                    " ".join(supplier.brands or []),
                    " ".join(supplier.products_services or []),
                    " ".join(supplier.subcategories or []),
                    " ".join(supplier.tags or []),
                    supplier.price_supplier_name,
                ],
            )
        ).lower()

        for token in tokens:
            if token in searchable:
                score += 1.5
                terms.append(token)

        for cat in matched_cats:
            cat_terms = [cat.name.lower()] + [s.lower() for s in cat.synonyms]
            if supplier.category and any(t in supplier.category.lower() for t in cat_terms):
                score += 4
                cat_names.append(cat.name)
                reasons.append(f"Categoría: {cat.name}")
            if any(t in searchable for t in cat_terms):
                score += 3
                if cat.name not in cat_names:
                    cat_names.append(cat.name)

        for brand in matched_brands:
            if any(brand.lower() in (b or "").lower() for b in supplier.brands or []):
                score += 5
                brand_names.append(brand.upper())
                reasons.append(f"Marca: {brand.upper()}")
            elif brand.lower() in searchable:
                score += 2
                brand_names.append(brand.upper())

        if brand_filter and any(brand_filter.lower() in (b or "").lower() for b in supplier.brands or []):
            score += 6

        if supplier.status == "preferido":
            score += 3
            reasons.append("Proveedor preferido")
        if supplier.internal_rating:
            score += float(supplier.internal_rating) * 0.5
        if supplier.last_quote_at:
            score += 1
        if supplier.price_supplier_name:
            score += 1

        reason = "; ".join(reasons) if reasons else None
        return score, terms, cat_names, brand_names, reason

    @staticmethod
    def _guess_supplier_from_filename(filename: str) -> str:
        base = re.sub(r"\.(xlsx|xls|csv|pdf)$", "", filename, flags=re.I)
        base = re.sub(r"[_\-]+", " ", base)
        for token in ("lista", "precios", "price", "list", "catalogo", "catálogo"):
            base = re.sub(rf"\b{token}\b", "", base, flags=re.I)
        return base.strip().title() if base.strip() else ""

    def _extract_tender_requirements(self, description: str) -> list[str]:
        found: list[str] = []
        lower = description.lower()
        for req, keywords in TENDER_REQUIREMENT_KEYWORDS.items():
            if any(k in lower for k in keywords):
                found.append(req)
        return found
