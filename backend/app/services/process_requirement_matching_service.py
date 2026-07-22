"""Matching de process_requirements contra repositorio corporativo (Fase 1)."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from app.services.process_requirement_service import ProcessRequirementService

if TYPE_CHECKING:
    from app.services.dgcp_bid_package_service import DGCPBidPackageService


class ProcessRequirementMatchingService:
    def __init__(
        self,
        db,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID | None = None,
    ) -> None:
        self.db = db
        self.tenant_id = tenant_id
        self.user_id = user_id
        self.pr_svc = ProcessRequirementService(db, tenant_id, user_id)

    async def reconcile_for_opportunity(
        self,
        bid_svc: "DGCPBidPackageService",
        opportunity_id: uuid.UUID,
        *,
        persist_table: bool | None = None,
    ) -> tuple[list[dict], list[dict]] | None:
        """Ejecuta el motor de matching existente sobre filas de process_requirements."""
        rows = await self.pr_svc.list_rows(opportunity_id)
        if not rows:
            return None

        pkg = await bid_svc._get_package(opportunity_id)
        if not pkg:
            return None

        checklist = [self.pr_svc.row_to_checklist_dict(row) for row in rows]
        original_checklist = pkg.checklist
        original_matches = pkg.document_matches
        pkg.checklist = checklist

        try:
            reconciled_checklist, raw_matches = await bid_svc._reconcile_corporate_documents(
                opportunity_id,
                pkg,
            )
            reconciled_checklist = bid_svc._sync_checklist_from_matches(reconciled_checklist, raw_matches)

            should_persist = (
                persist_table
                if persist_table is not None
                else ProcessRequirementService.write_enabled()
            )
            if should_persist:
                await self.pr_svc.upsert_from_checklist(
                    opportunity_id,
                    reconciled_checklist,
                    source="matching",
                )
                await self.db.flush()

            return reconciled_checklist, raw_matches
        finally:
            pkg.checklist = original_checklist
            pkg.document_matches = original_matches
