"""Seed datos deterministas para QA E2E Playwright."""

from __future__ import annotations

import asyncio
import json
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select

from app.db.session import AsyncSessionLocal
from app.models.document import Document
from app.models.price_list import PriceListProduct, PriceQuoteDraft
from app.models.tenant import Tenant
from app.models.user import User
from app.scripts.seed import ADMIN_EMAIL, TENANT_SLUG
from app.services.document_service import DocumentService


E2E_PREFIX = "E2E-QA-"


async def seed_fixtures() -> dict:
    async with AsyncSessionLocal() as db:
        tenant = (
            await db.execute(select(Tenant).where(Tenant.slug == TENANT_SLUG))
        ).scalar_one()
        admin = (
            await db.execute(select(User).where(User.email == ADMIN_EMAIL))
        ).scalar_one()
        marieli = (
            await db.execute(select(User).where(User.email == "marieli@justech.do"))
        ).scalar_one_or_none()
        jennipher = (
            await db.execute(select(User).where(User.email == "jennipher@justech.do"))
        ).scalar_one_or_none()

        old_docs = (
            await db.execute(
                select(Document).where(
                    Document.tenant_id == tenant.id,
                    Document.title.like(f"{E2E_PREFIX}%"),
                    Document.is_active.is_(True),
                )
            )
        ).scalars().all()
        for doc in old_docs:
            doc.is_active = False

        old_drafts = (
            await db.execute(
                select(PriceQuoteDraft).where(
                    PriceQuoteDraft.tenant_id == tenant.id,
                    PriceQuoteDraft.description.like(f"{E2E_PREFIX}%"),
                    PriceQuoteDraft.status != "descartado",
                )
            )
        ).scalars().all()
        for draft in old_drafts:
            draft.status = "descartado"

        doc_svc = DocumentService(db, tenant.id, admin.id)
        document_ids: list[str] = []
        for i in range(3):
            title = f"{E2E_PREFIX}doc-{i + 1}"
            content = f"Contenido E2E QA {i + 1} — {datetime.now(timezone.utc).isoformat()}".encode()
            doc = await doc_svc.register_document(
                filename=f"{E2E_PREFIX}doc-{i + 1}.txt",
                content=content,
                title=title,
                category="general",
                company="justech",
                client_name=f"Cliente E2E {i + 1}",
                mime_type="text/plain",
            )
            document_ids.append(str(doc.id))

        product = (
            await db.execute(
                select(PriceListProduct)
                .where(
                    PriceListProduct.tenant_id == tenant.id,
                    PriceListProduct.is_cotizable.is_(True),
                )
                .limit(1)
            )
        ).scalar_one_or_none()

        draft_ids: list[str] = []
        product_id: str | None = None
        if product:
            product_id = str(product.id)
            for i in range(2):
                draft = PriceQuoteDraft(
                    id=uuid.uuid4(),
                    tenant_id=tenant.id,
                    product_id=product.id,
                    user_id=admin.id,
                    client_name=f"{E2E_PREFIX}cliente-{i + 1}",
                    quantity=1,
                    description=f"{E2E_PREFIX}producto-{i + 1}",
                    cost_price=product.preferred_price or product.price,
                    currency=product.currency or "USD",
                    supplier=product.supplier,
                    margin_percent=15,
                    sale_price_suggested=product.preferred_price or product.price,
                    source_filename="e2e-fixture",
                    source_sheet="sheet1",
                    source_row=i + 1,
                    status="draft",
                )
                db.add(draft)
                draft_ids.append(str(draft.id))

        await db.commit()

        return {
            "tenant_id": str(tenant.id),
            "admin_user_id": str(admin.id),
            "marieli_user_id": str(marieli.id) if marieli else None,
            "jennipher_user_id": str(jennipher.id) if jennipher else None,
            "document_ids": document_ids,
            "draft_ids": draft_ids,
            "product_id": product_id,
            "e2e_prefix": E2E_PREFIX,
        }


def main() -> None:
    payload = asyncio.run(seed_fixtures())
    dest = sys.argv[1] if len(sys.argv) > 1 else None
    text = json.dumps(payload, indent=2, ensure_ascii=False)
    if dest:
        Path(dest).parent.mkdir(parents=True, exist_ok=True)
        Path(dest).write_text(text, encoding="utf-8")
        print(f"fixtures written: {dest}")
    else:
        print(text)


if __name__ == "__main__":
    main()
