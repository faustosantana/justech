"""Importar proveedores reales desde listas de precios indexadas y Odoo.

Run: python -m app.scripts.seed_suppliers
     python -m app.scripts.seed_suppliers --odoo --limit 300
"""

from __future__ import annotations

import argparse
import asyncio
import uuid

from sqlalchemy import func, select

from app.db.session import AsyncSessionLocal
from app.models.business_company import BusinessCompany
from app.models.price_list import PriceListFile, PriceListProduct
from app.models.tenant import Tenant
from app.schemas.supplier import SupplierCreate, SupplierUpdate
from app.services.odoo_service import OdooService
from app.services.supplier_service import SupplierService

TENANT_SLUG = "justech"

# Palabras clave para inferir categoría desde productos indexados
CATEGORY_HINTS: list[tuple[list[str], str]] = [
    (["toner", "cartucho", "consumible", "tinta"], "toners-y-consumibles"),
    (["laptop", "notebook", "portatil", "portátil"], "laptops"),
    (["desktop", "computadora", "pc "], "computadoras-nuevas"),
    (["servidor", "server"], "servidores"),
    (["switch", "router", "network", "ubiquiti"], "networking"),
    (["camara", "cámara", "cctv", "hikvision", "dahua"], "camaras-de-seguridad"),
    (["impresora", "printer", "multifuncional"], "impresoras"),
    (["microsoft", "office 365", "windows"], "licencias-microsoft"),
    (["ups", "bateria", "batería"], "ups-y-energia"),
]


async def seed(*, include_odoo: bool, odoo_limit: int) -> dict:
    async with AsyncSessionLocal() as db:
        tenant = (
            await db.execute(select(Tenant).where(Tenant.slug == TENANT_SLUG))
        ).scalar_one_or_none()
        if not tenant:
            raise SystemExit(f"Tenant '{TENANT_SLUG}' no encontrado")

        svc = SupplierService(db, tenant.id)
        await svc.ensure_base_categories()
        categories = (await svc.list_categories()).items
        slug_to_id = {c.slug: c.id for c in categories}

        stats = {"from_prices": 0, "from_odoo": 0, "linked_files": 0, "updated": 0}

        # --- Desde listas de precios indexadas ---
        file_rows = await db.execute(
            select(PriceListFile)
            .where(
                PriceListFile.tenant_id == tenant.id,
                PriceListFile.is_current.is_(True),
                PriceListFile.supplier.isnot(None),
            )
        )
        files = list(file_rows.scalars().all())
        supplier_names = sorted({f.supplier.strip() for f in files if f.supplier and f.supplier.strip()})

        for name in supplier_names:
            brands, cats, company_type = await _profile_from_products(db, tenant.id, name)
            category_ids = _match_category_ids(cats, slug_to_id)
            existing = await svc._find_by_name_or_tax(name, None)  # noqa: SLF001

            payload_data = {
                "name": name,
                "company_type": company_type,
                "price_supplier_name": name,
                "brands": brands,
                "products_services": cats[:20],
                "category_ids": category_ids,
                "primary_category_id": category_ids[0] if category_ids else None,
                "status": "activo",
            }

            if existing:
                await svc.update_supplier(existing.id, SupplierUpdate(**payload_data))
                stats["updated"] += 1
                supplier_id = existing.id
            else:
                created = await svc.create_supplier(SupplierCreate(**payload_data))
                stats["from_prices"] += 1
                supplier_id = created.id

            for f in files:
                if (f.supplier or "").strip() == name:
                    linked = await svc.auto_link_price_file(f.id)
                    if linked:
                        stats["linked_files"] += 1

        # --- Desde Odoo (proveedores con supplier_rank > 0) ---
        if include_odoo:
            odoo = OdooService(db, tenant.id)
            health = await odoo.health()
            if health.connected:
                vendors = await odoo.list_vendors(limit=odoo_limit)
                for v in vendors.items:
                    existing = await svc._find_by_name_or_tax(v.name, v.vat)  # noqa: SLF001
                    data = {
                        "name": v.name,
                        "company_type": "proveedor",
                        "tax_id": v.vat,
                        "email": v.email,
                        "phone": v.phone,
                        "city": v.city,
                        "odoo_partner_id": v.id,
                        "status": "activo",
                    }
                    if existing:
                        await svc.update_supplier(existing.id, SupplierUpdate(**data))
                        stats["updated"] += 1
                    else:
                        await svc.create_supplier(SupplierCreate(**data))
                        stats["from_odoo"] += 1
            else:
                print("Odoo no conectado — omitiendo importación Odoo")

        return stats


async def _profile_from_products(db, tenant_id: uuid.UUID, supplier_name: str) -> tuple[list[str], list[str], str]:
    result = await db.execute(
        select(PriceListProduct.brand, PriceListProduct.category, PriceListProduct.description)
        .where(
            PriceListProduct.tenant_id == tenant_id,
            PriceListProduct.is_current.is_(True),
            PriceListProduct.supplier == supplier_name,
        )
        .limit(500)
    )
    brands: set[str] = set()
    categories: set[str] = set()
    text_blob: list[str] = []
    for brand, category, desc in result.all():
        if brand:
            brands.add(brand.strip())
        if category:
            categories.add(category.strip())
        if desc:
            text_blob.append(desc.lower())

    combined = " ".join(text_blob)
    company_type = "fabricante" if supplier_name.lower() in {"dell", "lenovo", "hp", "hikvision", "cisco"} else "distribuidor"
    return sorted(brands)[:15], sorted(categories)[:20], company_type


def _match_category_ids(product_categories: list[str], slug_to_id: dict[str, uuid.UUID]) -> list[uuid.UUID]:
    matched: list[uuid.UUID] = []
    blob = " ".join(product_categories).lower()
    for keywords, slug in CATEGORY_HINTS:
        if any(k in blob for k in keywords):
            cid = slug_to_id.get(slug)
            if cid and cid not in matched:
                matched.append(cid)
    if not matched and ("laptop" in blob or "notebook" in blob):
        cid = slug_to_id.get("laptops")
        if cid:
            matched.append(cid)
    if not matched and product_categories:
        # fallback: laptops para fabricantes de hardware si hay productos
        cid = slug_to_id.get("laptops")
        if cid:
            matched.append(cid)
    return matched


def main() -> None:
    parser = argparse.ArgumentParser(description="Importar proveedores desde precios y Odoo")
    parser.add_argument("--odoo", action="store_true", help="Importar proveedores desde Odoo ERP")
    parser.add_argument("--limit", type=int, default=300, help="Límite de proveedores Odoo")
    args = parser.parse_args()

    stats = asyncio.run(seed(include_odoo=args.odoo, odoo_limit=args.limit))
    print("Importación completada:")
    for key, val in stats.items():
        print(f"  {key}: {val}")


if __name__ == "__main__":
    main()
