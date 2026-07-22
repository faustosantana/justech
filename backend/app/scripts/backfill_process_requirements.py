#!/usr/bin/env python3
"""Backfill process_requirements desde dgcp_bid_packages.checklist (Fase 1)."""

from __future__ import annotations

import argparse
import asyncio
import uuid

from sqlalchemy import select

from app.db.session import AsyncSessionLocal
from app.models.dgcp_bid_package import DGCPBidPackage
from app.services.process_requirement_service import ProcessRequirementService


async def backfill_opportunity(
    opportunity_id: uuid.UUID,
    *,
    tenant_id: uuid.UUID | None = None,
    dry_run: bool = False,
) -> int:
    async with AsyncSessionLocal() as db:
        query = select(DGCPBidPackage).where(DGCPBidPackage.opportunity_id == opportunity_id)
        if tenant_id:
            query = query.where(DGCPBidPackage.tenant_id == tenant_id)
        result = await db.execute(query)
        pkg = result.scalar_one_or_none()
        if not pkg:
            raise SystemExit(f"No bid package for opportunity {opportunity_id}")

        checklist = list(pkg.checklist or [])
        if not checklist:
            raise SystemExit(f"Empty checklist for opportunity {opportunity_id}")

        svc = ProcessRequirementService(db, pkg.tenant_id)
        if dry_run:
            print(f"[dry-run] Would upsert {len(checklist)} items for {opportunity_id}")
            return len(checklist)

        count = await svc.upsert_from_checklist(opportunity_id, checklist, source="backfill")
        await db.commit()
        print(f"Upserted {count} process_requirements for {opportunity_id}")
        return count


def main() -> None:
    parser = argparse.ArgumentParser(description="Backfill process_requirements from JSONB checklist")
    parser.add_argument("opportunity_id", help="UUID de la oportunidad DGCP")
    parser.add_argument("--tenant-id", default=None, help="UUID tenant (opcional)")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    asyncio.run(
        backfill_opportunity(
            uuid.UUID(args.opportunity_id),
            tenant_id=uuid.UUID(args.tenant_id) if args.tenant_id else None,
            dry_run=args.dry_run,
        )
    )


if __name__ == "__main__":
    main()
