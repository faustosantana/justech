"""Servicio principal — process_requirements (Fase 1)."""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.process_requirement import ProcessRequirement
from app.schemas.process_requirement import (
    ProcessRequirementItem,
    ProcessRequirementListResponse,
    ProcessRequirementUpdateRequest,
    ProcessRequirementUpdateResponse,
)
from app.services.process_requirement_status_mapper import (
    APPROVED_STATUSES,
    approved_status_to_legacy,
    legacy_checklist_item_status,
    legacy_status_to_approved,
)


class ProcessRequirementService:
    def __init__(
        self,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID | None = None,
    ) -> None:
        self.db = db
        self.tenant_id = tenant_id
        self.user_id = user_id

    @staticmethod
    def read_enabled() -> bool:
        return bool(settings.dgcp_requirements_table_read)

    @staticmethod
    def write_enabled() -> bool:
        return bool(settings.dgcp_requirements_table_write)

    async def count_for_opportunity(self, opportunity_id: uuid.UUID) -> int:
        result = await self.db.scalar(
            select(func.count())
            .select_from(ProcessRequirement)
            .where(
                ProcessRequirement.tenant_id == self.tenant_id,
                ProcessRequirement.opportunity_id == opportunity_id,
            )
        )
        return int(result or 0)

    async def list_rows(self, opportunity_id: uuid.UUID) -> list[ProcessRequirement]:
        result = await self.db.execute(
            select(ProcessRequirement)
            .where(
                ProcessRequirement.tenant_id == self.tenant_id,
                ProcessRequirement.opportunity_id == opportunity_id,
            )
            .order_by(ProcessRequirement.sort_order, ProcessRequirement.label)
        )
        return list(result.scalars().all())

    async def get_row(
        self,
        opportunity_id: uuid.UUID,
        requirement_id: uuid.UUID,
    ) -> ProcessRequirement | None:
        result = await self.db.execute(
            select(ProcessRequirement).where(
                ProcessRequirement.tenant_id == self.tenant_id,
                ProcessRequirement.opportunity_id == opportunity_id,
                ProcessRequirement.id == requirement_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_requirements(self, opportunity_id: uuid.UUID) -> ProcessRequirementListResponse:
        rows = await self.list_rows(opportunity_id)
        items = [self._row_to_item(row) for row in rows]
        status_counts: dict[str, int] = {}
        for item in items:
            status_counts[item.status] = status_counts.get(item.status, 0) + 1
        return ProcessRequirementListResponse(
            opportunity_id=opportunity_id,
            items=items,
            total=len(items),
            data_source="process_requirements",
            status_counts=status_counts,
        )

    async def checklist_from_table(self, opportunity_id: uuid.UUID) -> list[dict] | None:
        rows = await self.list_rows(opportunity_id)
        if not rows:
            return None
        return [self.row_to_checklist_dict(row) for row in rows]

    async def upsert_from_checklist(
        self,
        opportunity_id: uuid.UUID,
        checklist: list[dict],
        *,
        source: str = "checklist_sync",
    ) -> int:
        if not checklist:
            return 0

        existing = await self.list_rows(opportunity_id)
        by_key = {row.requirement_key: row for row in existing}
        touched = 0

        for index, item in enumerate(checklist):
            key = str(item.get("requirement_key") or "").strip()
            if not key:
                continue
            row = by_key.get(key)
            payload = self._checklist_item_to_row_fields(item, source=source, sort_order=index)
            if row:
                for field, value in payload.items():
                    setattr(row, field, value)
                row.updated_at = datetime.now(timezone.utc)
            else:
                row = ProcessRequirement(
                    tenant_id=self.tenant_id,
                    opportunity_id=opportunity_id,
                    requirement_key=key,
                    **payload,
                )
                self.db.add(row)
                by_key[key] = row
            touched += 1

        await self.db.flush()
        return touched

    async def update_requirement(
        self,
        opportunity_id: uuid.UUID,
        requirement_id: uuid.UUID,
        data: ProcessRequirementUpdateRequest,
        *,
        sync_legacy_checklist: bool = True,
    ) -> ProcessRequirementUpdateResponse:
        row = await self.get_row(opportunity_id, requirement_id)
        if not row:
            raise ValueError("Requisito no encontrado")

        if data.status is not None:
            normalized = data.status.strip().lower()
            if normalized not in APPROVED_STATUSES:
                raise ValueError(f"Estado inválido: {data.status}")
            row.status = normalized

        if data.document_ref_type is not None:
            row.document_ref_type = data.document_ref_type or None
        if data.document_ref_id is not None:
            row.document_ref_id = data.document_ref_id
        if data.assignee_user_id is not None:
            row.assignee_user_id = data.assignee_user_id
        if data.due_date is not None:
            row.due_date = data.due_date
        if data.notes is not None:
            row.notes = data.notes

        if data.history_note:
            history = list(row.history or [])
            history.append(self._history_event("note", data.history_note))
            row.history = history

        row.updated_at = datetime.now(timezone.utc)
        await self.db.flush()

        synced = False
        if sync_legacy_checklist and self.write_enabled():
            synced = await self._sync_row_to_legacy_checklist(opportunity_id, row)

        return ProcessRequirementUpdateResponse(
            opportunity_id=opportunity_id,
            requirement=self._row_to_item(row),
            synced_legacy_checklist=synced,
        )

    def row_to_checklist_dict(self, row: ProcessRequirement) -> dict[str, Any]:
        legacy_status = approved_status_to_legacy(row.status)
        item_id = row.legacy_checklist_item_id or row.id
        evidence = dict(row.source_evidence or {})
        checklist: dict[str, Any] = {
            "id": str(item_id),
            "requirement_key": row.requirement_key,
            "requirement": row.label,
            "tipo": row.category,
            "mandatory": row.mandatory,
            "status": legacy_status,
            "unified_status": row.status,
            "category": row.category,
            "priority": row.priority,
            "notes": row.notes,
            "note_history": evidence.get("note_history") or list(row.history or []),
            "assignee": evidence.get("assignee_name"),
            "task_id": str(row.task_id) if row.task_id else None,
            "form_type": (row.template_ref or {}).get("form_type"),
            "template_web_url": (row.template_ref or {}).get("web_url"),
            "match_source": evidence.get("match_source"),
            "document_title": evidence.get("document_title"),
            "relative_path": evidence.get("relative_path"),
            "recommended_action": evidence.get("recommended_action"),
            "risk": evidence.get("risk"),
            "completable": evidence.get("completable", False),
            "display_status": evidence.get("display_status"),
            "validity_analysis": evidence.get("validity_analysis"),
            "manual_validation": evidence.get("manual_validation"),
            "source_document": evidence.get("source_document"),
            "source_page": evidence.get("source_page"),
            "source_section": evidence.get("source_section"),
            "evidence_fragment": evidence.get("evidence_fragment"),
            "evidence_confidence": evidence.get("evidence_confidence"),
            "suggested_document": evidence.get("suggested_document"),
            "ia_observations": evidence.get("ia_observations"),
        }
        if row.due_date:
            checklist["valid_until"] = row.due_date.isoformat()
        if row.document_ref_type == "document" and row.document_ref_id:
            checklist["document_id"] = str(row.document_ref_id)
        elif row.document_ref_type == "knowledge" and row.document_ref_id:
            checklist["knowledge_asset_id"] = str(row.document_ref_id)
        elif row.document_ref_type == "process_document" and row.document_ref_id:
            checklist["process_document_id"] = str(row.document_ref_id)
        elif row.document_ref_type == "m365" and row.document_ref_id:
            checklist["m365_file_id"] = str(row.document_ref_id)
        if row.template_ref:
            if row.template_ref.get("m365_file_id"):
                checklist["m365_file_id"] = str(row.template_ref["m365_file_id"])
            if row.template_ref.get("web_url"):
                checklist["template_web_url"] = row.template_ref["web_url"]
        if row.status == "not_applicable":
            checklist["no_aplica"] = True
        return checklist

    def _checklist_item_to_row_fields(
        self,
        item: dict,
        *,
        source: str,
        sort_order: int,
    ) -> dict[str, Any]:
        raw_status = legacy_checklist_item_status(item)
        approved = legacy_status_to_approved(raw_status)
        item_id = item.get("id")
        legacy_id = uuid.UUID(str(item_id)) if item_id else None

        document_ref_type: str | None = None
        document_ref_id: uuid.UUID | None = None
        if item.get("document_id"):
            document_ref_type = "document"
            document_ref_id = uuid.UUID(str(item["document_id"]))
        elif item.get("knowledge_asset_id"):
            document_ref_type = "knowledge"
            document_ref_id = uuid.UUID(str(item["knowledge_asset_id"]))
        elif item.get("process_document_id"):
            document_ref_type = "process_document"
            document_ref_id = uuid.UUID(str(item["process_document_id"]))
        elif item.get("m365_file_id"):
            document_ref_type = "m365"
            document_ref_id = uuid.UUID(str(item["m365_file_id"]))

        template_ref: dict | None = None
        if item.get("form_type") or item.get("m365_file_id") or item.get("template_web_url"):
            template_ref = {
                "form_type": item.get("form_type"),
                "web_url": item.get("template_web_url"),
            }
            if item.get("m365_file_id"):
                template_ref["m365_file_id"] = str(item["m365_file_id"])
            if item.get("document_title"):
                template_ref["name"] = item.get("document_title")

        task_id = item.get("task_id")
        source_evidence = {
            "assignee_name": item.get("assignee"),
            "document_title": item.get("document_title"),
            "match_source": item.get("match_source"),
            "relative_path": item.get("relative_path"),
            "recommended_action": item.get("recommended_action"),
            "risk": item.get("risk"),
            "completable": item.get("completable", False),
            "display_status": item.get("display_status"),
            "validity_analysis": item.get("validity_analysis"),
            "manual_validation": item.get("manual_validation"),
            "note_history": item.get("note_history") or [],
            "source_document": item.get("source_document"),
            "source_page": item.get("source_page"),
            "source_section": item.get("source_section"),
            "evidence_fragment": item.get("evidence_fragment"),
            "evidence_confidence": item.get("evidence_confidence"),
            "suggested_document": item.get("suggested_document"),
            "ia_observations": item.get("ia_observations"),
        }

        due_date: date | None = None
        valid_until = item.get("valid_until")
        if valid_until:
            due_date = date.fromisoformat(str(valid_until)[:10])

        return {
            "label": str(item.get("requirement") or item.get("label") or item.get("requirement_key")),
            "category": str(item.get("category") or item.get("tipo") or "general"),
            "mandatory": bool(item.get("mandatory", True)),
            "priority": str(item.get("priority") or "normal"),
            "status": approved,
            "source": str(item.get("evidence_source") or item.get("source") or source),
            "source_evidence": source_evidence,
            "due_date": due_date,
            "document_ref_type": document_ref_type,
            "document_ref_id": document_ref_id,
            "template_ref": template_ref,
            "task_id": uuid.UUID(str(task_id)) if task_id else None,
            "notes": item.get("notes"),
            "history": list(item.get("note_history") or []),
            "sort_order": sort_order,
            "legacy_checklist_item_id": legacy_id,
        }

    def _row_to_item(self, row: ProcessRequirement) -> ProcessRequirementItem:
        evidence = dict(row.source_evidence or {})
        return ProcessRequirementItem(
            id=row.id,
            opportunity_id=row.opportunity_id,
            requirement_key=row.requirement_key,
            label=row.label,
            category=row.category,
            mandatory=row.mandatory,
            priority=row.priority,
            status=row.status,
            source=row.source,
            source_evidence=evidence,
            assignee_user_id=row.assignee_user_id,
            assignee_name=evidence.get("assignee_name"),
            due_date=row.due_date,
            document_ref_type=row.document_ref_type,
            document_ref_id=row.document_ref_id,
            document_title=evidence.get("document_title"),
            template_ref=row.template_ref,
            task_id=row.task_id,
            notes=row.notes,
            history=list(row.history or []),
            sort_order=row.sort_order,
            legacy_checklist_item_id=row.legacy_checklist_item_id,
            legacy_status=approved_status_to_legacy(row.status),
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    def _history_event(self, action: str, note: str) -> dict[str, Any]:
        return {
            "at": datetime.now(timezone.utc).isoformat(),
            "action": action,
            "note": note,
            "user_id": str(self.user_id) if self.user_id else None,
        }

    async def _sync_row_to_legacy_checklist(
        self,
        opportunity_id: uuid.UUID,
        row: ProcessRequirement,
    ) -> bool:
        from app.models.dgcp_bid_package import DGCPBidPackage

        result = await self.db.execute(
            select(DGCPBidPackage).where(
                DGCPBidPackage.tenant_id == self.tenant_id,
                DGCPBidPackage.opportunity_id == opportunity_id,
            )
        )
        pkg = result.scalar_one_or_none()
        if not pkg:
            return False

        checklist = [dict(i) for i in (pkg.checklist or [])]
        updated_item = self.row_to_checklist_dict(row)
        found = False
        for index, item in enumerate(checklist):
            if item.get("requirement_key") == row.requirement_key:
                merged = {**item, **updated_item}
                merged["id"] = item.get("id") or updated_item["id"]
                checklist[index] = merged
                found = True
                break
        if not found:
            checklist.append(updated_item)
        pkg.checklist = checklist
        await self.db.flush()
        return True
