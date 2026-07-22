"""Procesador batch nocturno — autollenado de todas las plantillas M365 DGCP."""

from __future__ import annotations

import hashlib
import json
import logging
import traceback
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.dgcp_opportunity import DGCPOpportunity
from app.models.m365_repository import M365RepositoryFile
from app.models.user import User
from app.services.document_autofill.document_autofill_service import DocumentAutofillService
from app.services.document_autofill.m365_template_catalog import (
    TemplateCatalogEntry,
    is_dgcp_template_candidate,
    row_to_catalog_entry,
)
from app.services.document_autofill.m365_template_resolver import M365TemplateReference, M365TemplateResolver

logger = logging.getLogger(__name__)


@dataclass
class TemplateRunResult:
    template_name: str
    template_key: str
    form_type: str
    m365_location: str
    detected_type: str
    source: str
    pdf_engine: str
    fields_detected: list[str] = field(default_factory=list)
    fields_filled: list[str] = field(default_factory=list)
    fields_pending: list[str] = field(default_factory=list)
    pdf_generated: bool = False
    docx_generated: bool = False
    original_intact: bool = False
    errors: list[str] = field(default_factory=list)
    stacktrace: str | None = None
    status: str = "FAILED"
    m365_file_id: str | None = None
    web_url: str | None = None
    pdf_path: str | None = None
    docx_path: str | None = None
    audit_path: str | None = None
    duration_ms: int = 0
    aliases_detected: int = 0
    aliases_mapped: int = 0
    aliases_pending: int = 0
    aliases_critical_pending: int = 0
    aliases_non_critical_pending: int = 0
    aliases_ignored: int = 0
    aliases_not_applicable_stage: int = 0
    critical_pending_aliases: list[str] = field(default_factory=list)
    non_critical_pending_aliases: list[str] = field(default_factory=list)
    partial_reason: str | None = None
    can_pass: bool = False
    ready_for_signature: bool = False
    completion_status: str = "FAILED"


class DgcpAutofillBatchService:
    """Ejecuta autollenado QA sobre todas las plantillas del repositorio M365."""

    def __init__(
        self,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID | None,
        *,
        output_root: Path | None = None,
    ):
        self.db = db
        self.tenant_id = tenant_id
        self.user_id = user_id
        self.resolver = M365TemplateResolver(db, tenant_id, user_id)
        self.documents = DocumentAutofillService(db, tenant_id, user_id=user_id)
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        self.output_root = output_root or (
            Path(settings.expediente_storage_path) / str(tenant_id) / f"_autofill_qa_{ts}"
        )

    async def list_all_templates(self) -> list[TemplateCatalogEntry]:
        rows = (
            await self.db.execute(
                select(M365RepositoryFile).where(
                    M365RepositoryFile.tenant_id == self.tenant_id,
                    M365RepositoryFile.is_deleted.is_(False),
                    M365RepositoryFile.is_folder.is_(False),
                )
            )
        ).scalars().all()
        entries = [row_to_catalog_entry(r) for r in rows if is_dgcp_template_candidate(r)]
        entries.sort(key=lambda e: (-e.score, e.name.lower()))
        return entries

    async def run_all(
        self,
        opportunity: DGCPOpportunity,
        *,
        company: str = "justech",
        user_email: str | None = None,
    ) -> list[TemplateRunResult]:
        templates = await self.list_all_templates()
        results: list[TemplateRunResult] = []
        logger.info("dgcp_autofill_batch_start count=%d output=%s", len(templates), self.output_root)

        for idx, entry in enumerate(templates, 1):
            logger.info("processing %d/%d: %s", idx, len(templates), entry.name)
            result = await self._process_one(
                entry,
                opportunity,
                company=company,
                user_email=user_email,
            )
            results.append(result)
            self._append_jsonl(result)

        summary_path = self.output_root / "batch_summary.json"
        self.output_root.mkdir(parents=True, exist_ok=True)
        summary_path.write_text(
            json.dumps(
                {
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                    "total": len(results),
                    "pass": sum(1 for r in results if r.status == "READY_FOR_SIGNATURE"),
                    "draft": sum(1 for r in results if r.status == "DRAFT_OK"),
                    "blocked": sum(1 for r in results if r.status == "BLOCKED"),
                    "failed": sum(1 for r in results if r.status == "FAILED"),
                    "ready_for_signature": sum(1 for r in results if r.status == "READY_FOR_SIGNATURE"),
                    "draft_ok": sum(1 for r in results if r.status == "DRAFT_OK"),
                    "blocked": sum(1 for r in results if r.status == "BLOCKED"),
                    "aliases_detected_total": sum(r.aliases_detected for r in results),
                    "aliases_completed_total": sum(r.aliases_mapped for r in results),
                    "aliases_critical_pending_total": sum(r.aliases_critical_pending for r in results),
                    "aliases_non_critical_pending_total": sum(r.aliases_non_critical_pending for r in results),
                    "aliases_ignored_total": sum(r.aliases_ignored for r in results),
                    "aliases_not_applicable_stage_total": sum(
                        r.aliases_not_applicable_stage for r in results
                    ),
                    "results": [asdict(r) for r in results],
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        return results

    async def _process_one(
        self,
        entry: TemplateCatalogEntry,
        opportunity: DGCPOpportunity,
        *,
        company: str,
        user_email: str | None,
    ) -> TemplateRunResult:
        started = datetime.now(timezone.utc)
        m365_loc = f"{entry.parent_path}/{entry.name}".strip("/")
        result = TemplateRunResult(
            template_name=entry.name,
            template_key=entry.template_key,
            form_type=entry.form_type,
            m365_location=m365_loc,
            detected_type=entry.detected_category,
            source="pending",
            pdf_engine="pending",
            m365_file_id=str(entry.m365_file_id),
            web_url=entry.web_url,
        )

        try:
            ref = M365TemplateReference(
                form_type=entry.form_type,
                m365_file_id=entry.m365_file_id,
                graph_item_id=entry.graph_item_id,
                drive_id=entry.drive_id,
                source=entry.source,
                name=entry.name,
                web_url=entry.web_url,
                parent_path=entry.parent_path,
                content_hash=entry.content_hash,
                template_version=entry.content_hash or "index",
                document_type=entry.document_type,
                resolver="m365_index",
            )

            before_bytes = await self.resolver.download_bytes(ref)
            before_hash = hashlib.sha256(before_bytes).hexdigest()

            out_dir = self.output_root / entry.template_key
            doc_result = await self.documents.build_document_from_m365(
                opportunity,
                m365_ref=ref,
                template_bytes=before_bytes,
                form_type=entry.form_type,
                company=company,
                persist=True,
                expediente_path=out_dir,
                user_email=user_email,
                template_format=entry.format,
            )

            after_bytes = await self.resolver.download_bytes(ref)
            after_hash = hashlib.sha256(after_bytes).hexdigest()

            result.source = doc_result.template_source_type
            result.pdf_engine = doc_result.pdf_engine
            result.fields_detected = [f.key for f in doc_result.fields]
            result.fields_filled = [f.key for f in doc_result.fields if f.value]
            result.fields_pending = doc_result.missing
            result.pdf_generated = bool(doc_result.pdf_path and Path(doc_result.pdf_path).is_file())
            result.docx_generated = bool(doc_result.docx_path and Path(doc_result.docx_path).is_file())
            result.original_intact = before_hash == after_hash
            result.pdf_path = doc_result.pdf_path
            result.docx_path = doc_result.docx_path
            result.audit_path = (
                str(Path(doc_result.pdf_path).with_name(Path(doc_result.pdf_path).stem + "_audit.json"))
                if doc_result.pdf_path
                else None
            )
            summary = doc_result.alias_summary or {}
            result.aliases_detected = doc_result.audit_record.get("aliases_detected", summary.get("total", 0))
            result.aliases_mapped = summary.get("completed", 0)
            result.aliases_critical_pending = summary.get("critical_pending", 0)
            result.aliases_non_critical_pending = summary.get("non_critical_pending", 0)
            result.aliases_ignored = summary.get("ignored", 0)
            result.aliases_not_applicable_stage = summary.get("not_applicable_stage", 0)
            result.aliases_pending = result.aliases_critical_pending + result.aliases_non_critical_pending
            result.critical_pending_aliases = doc_result.audit_record.get("critical_pending", [])
            result.non_critical_pending_aliases = doc_result.audit_record.get("non_critical_pending", [])
            result.unresolved_aliases = result.critical_pending_aliases + result.non_critical_pending_aliases
            result.can_pass = doc_result.can_pass
            result.ready_for_signature = doc_result.ready_for_signature
            result.completion_status = doc_result.completion_status
            if not result.ready_for_signature:
                parts = []
                if result.critical_pending_aliases:
                    parts.append(f"críticos: {', '.join(result.critical_pending_aliases[:5])}")
                if result.non_critical_pending_aliases:
                    parts.append(f"no críticos: {', '.join(result.non_critical_pending_aliases[:5])}")
                result.partial_reason = "; ".join(parts) if parts else "pendientes sin clasificar"

            if not result.original_intact:
                result.errors.append("Plantilla original M365 modificada (hash distinto)")
            if not result.pdf_generated:
                result.errors.append("PDF no generado")

            if result.pdf_generated and result.original_intact:
                if result.completion_status == "READY_FOR_SIGNATURE":
                    result.status = "READY_FOR_SIGNATURE"
                elif result.completion_status == "BLOCKED":
                    result.status = "BLOCKED"
                else:
                    result.status = "DRAFT_OK"
            else:
                result.status = "FAILED"

        except Exception as exc:
            result.errors.append(str(exc))
            result.stacktrace = traceback.format_exc()
            result.status = "FAILED"
            logger.exception("template_failed name=%s", entry.name)

        elapsed = int((datetime.now(timezone.utc) - started).total_seconds() * 1000)
        result.duration_ms = elapsed
        return result

    def _append_jsonl(self, result: TemplateRunResult) -> None:
        self.output_root.mkdir(parents=True, exist_ok=True)
        line = json.dumps(asdict(result), ensure_ascii=False) + "\n"
        with (self.output_root / "batch_progress.jsonl").open("a", encoding="utf-8") as f:
            f.write(line)

    @staticmethod
    def render_markdown_report(
        results: list[TemplateRunResult],
        *,
        output_dir: str = "",
        previous_status: dict[str, str] | None = None,
    ) -> str:
        total = len(results)
        ready = sum(1 for r in results if r.status == "READY_FOR_SIGNATURE")
        draft = sum(1 for r in results if r.status == "DRAFT_OK")
        blocked = sum(1 for r in results if r.status == "BLOCKED")
        failed = sum(1 for r in results if r.status == "FAILED")
        aliases_detected = sum(r.aliases_detected for r in results)
        aliases_completed = sum(r.aliases_mapped for r in results)
        aliases_critical = sum(r.aliases_critical_pending for r in results)
        aliases_non_critical = sum(r.aliases_non_critical_pending for r in results)
        aliases_ignored = sum(r.aliases_ignored for r in results)
        aliases_not_applicable = sum(r.aliases_not_applicable_stage for r in results)
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

        critical_counts: dict[str, int] = {}
        non_critical_counts: dict[str, int] = {}
        for r in results:
            for alias in r.critical_pending_aliases:
                critical_counts[alias] = critical_counts.get(alias, 0) + 1
            for alias in r.non_critical_pending_aliases:
                non_critical_counts[alias] = non_critical_counts.get(alias, 0) + 1

        lines = [
            "# Reporte autollenado — Todas las plantillas M365 DGCP",
            "",
            f"**Generado:** {now}  ",
            f"**Directorio QA:** `{output_dir}`  ",
            "",
            "## Resumen ejecutivo",
            "",
            "| Métrica | Valor |",
            "|---------|-------|",
            f"| Plantillas encontradas | {total} |",
            f"| Listos para firma | {ready} |",
            f"| Solo borrador (no críticos pendientes) | {draft} |",
            f"| Bloqueados (críticos pendientes) | {blocked} |",
            f"| FAILED | {failed} |",
            f"| Aliases detectados | {aliases_detected} |",
            f"| Aliases completados | {aliases_completed} |",
            f"| Pendientes críticos | {aliases_critical} |",
            f"| Pendientes no críticos | {aliases_non_critical} |",
            f"| Ignorados | {aliases_ignored} |",
            f"| No aplica por etapa | {aliases_not_applicable} |",
            "",
        ]

        if previous_status:
            prev_ready = sum(1 for s in previous_status.values() if s in ("PASS", "READY_FOR_SIGNATURE"))
            prev_draft = sum(1 for s in previous_status.values() if s in ("PARTIAL", "DRAFT_OK"))
            prev_failed = sum(1 for s in previous_status.values() if s == "FAILED")
            lines.extend(
                [
                    "## Comparación vs batch anterior",
                    "",
                    "| Métrica | Antes | Después | Δ |",
                    "|---------|-------|---------|---|",
                    f"| Listos firma | {prev_ready} | {ready} | {ready - prev_ready:+d} |",
                    f"| Borrador | {prev_draft} | {draft + blocked} | {draft + blocked - prev_draft:+d} |",
                    f"| FAILED | {prev_failed} | {failed} | {failed - prev_failed:+d} |",
                    "",
                ]
            )

        lines.extend(["## Top 20 pendientes críticos", ""])
        if critical_counts:
            for alias, count in sorted(critical_counts.items(), key=lambda x: -x[1])[:20]:
                lines.append(f"- `{alias}` ({count} plantillas)")
        else:
            lines.append("- Ninguno.")

        lines.extend(["", "## Top 20 pendientes no críticos", ""])
        if non_critical_counts:
            for alias, count in sorted(non_critical_counts.items(), key=lambda x: -x[1])[:20]:
                lines.append(f"- `{alias}` ({count} plantillas)")
        else:
            lines.append("- Ninguno.")

        lines.extend(
            [
                "",
                "## Detalle por plantilla",
                "",
                "| Plantilla | Completados | Crít. | No crít. | Ign. | N/A etapa | Estado | Motivo |",
                "|-----------|-------------|-------|----------|------|-----------|--------|--------|",
            ]
        )

        for r in sorted(
            results,
            key=lambda x: (x.status != "READY_FOR_SIGNATURE", x.status != "DRAFT_OK", x.template_name),
        ):
            reason = (r.partial_reason or "—")[:55] if r.status != "READY_FOR_SIGNATURE" else "—"
            lines.append(
                f"| {r.template_name[:45]} | {r.aliases_mapped} | {r.aliases_critical_pending} "
                f"| {r.aliases_non_critical_pending} | {r.aliases_ignored} | {r.aliases_not_applicable_stage} "
                f"| **{r.status}** | {reason} |"
            )

        # Failure analysis
        fail_reasons: dict[str, int] = {}
        for r in results:
            if r.status == "FAILED":
                key = r.errors[0][:60] if r.errors else "unknown"
                fail_reasons[key] = fail_reasons.get(key, 0) + 1

        lines.extend(["", "## Principales causas de fallo", ""])
        if fail_reasons:
            for reason, count in sorted(fail_reasons.items(), key=lambda x: -x[1]):
                lines.append(f"- ({count}) {reason}")
        else:
            lines.append("- Ningún fallo total.")

        lines.extend(
            [
                "",
                "## Próximos pasos recomendados",
                "",
                "1. Revisar plantillas PARTIAL — mapear aliases Word a campos corporativos conocidos.",
                "2. Para FAILED por timeout LibreOffice — aumentar `libreoffice_convert_timeout` o procesar en cola.",
                "3. Conectar plantillas PARTIAL con checklist DGCP por `form_type` detectado.",
                "4. Excluir pliegos/contratos que no requieren autollenado de datos empresa en UI.",
                "5. Sincronizar repositorio M365 si faltan plantillas nuevas en SharePoint.",
                "",
            ]
        )
        return "\n".join(lines)
