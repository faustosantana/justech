"""Orquestador — análisis, relleno, copia controlada y auditoría."""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.dgcp_opportunity import DGCPOpportunity
from app.services.document_autofill.m365_template_catalog import _slugify, classify_template
from app.services.document_autofill.template_process_context import resolve_template_context
from app.services.document_autofill.alias_mapping_service import AliasMappingService
from app.services.document_autofill.docx_template_writer import extract_docx_aliases
from app.services.document_autofill.generic_docx_fill_engine import fill_docx_bytes_generic
from app.services.document_autofill.m365_template_cache import cache_status, is_likely_stub
from app.services.document_autofill.m365_template_resolver import (
    M365TemplateReference,
    M365TemplateResolver,
)
from app.services.document_autofill.pdf_field_writer import fill_pdf_acroform
from app.services.document_autofill.pdf_preview_service import template_to_preview_pdf, write_pdf
from app.services.document_autofill.template_analysis_service import TemplateAnalysisService
from app.services.document_autofill.field_alias_registry import CANONICAL_FIELDS, CRITICAL_CANONICAL_FIELDS
from app.services.document_autofill.field_alias_registry import (
    canonical_field_key,
    deduplicate_field_statuses,
)
from app.services.document_autofill.form_template_registry import numeric_alias_map
from app.services.document_completion_service import DocumentCompletionService


FIELD_LABELS: dict[str, str] = {
    "razon_social": "Razón social",
    "rnc": "RNC",
    "direccion": "Dirección",
    "representante_legal": "Representante legal",
    "telefono": "Teléfono",
    "correo": "Correo",
    "cuenta_bancaria": "Cuenta bancaria",
    "proceso_dgcp": "Código proceso DGCP",
    "entidad_contratante": "Entidad contratante",
    "objeto_proceso": "Objeto del proceso",
    "monto": "Monto oferta",
    "fecha": "Fecha",
    "numero_expediente": "Número expediente",
    "institucion": "Institución",
    "rpe": "RPE",
    "representante_autorizado": "Representante autorizado",
    "cargo": "Cargo",
    "productos": "Productos/servicios",
    "plazo_entrega": "Plazo",
    "condiciones": "Condiciones",
    "garantia": "Garantía",
    "fabricante": "Fabricante",
}

FIELD_SOURCES: dict[str, str] = {
    "razon_social": "Repositorio corporativo",
    "rnc": "Repositorio corporativo",
    "direccion": "Repositorio corporativo",
    "representante_legal": "Repositorio corporativo",
    "telefono": "Repositorio corporativo",
    "correo": "Repositorio corporativo",
    "cuenta_bancaria": "Repositorio corporativo",
    "proceso_dgcp": "DGCP",
    "entidad_contratante": "DGCP",
    "objeto_proceso": "DGCP",
    "monto": "DGCP",
    "fecha": "Sistema",
    "productos": "Usuario / expediente",
    "plazo_entrega": "Usuario / expediente",
    "condiciones": "Usuario / expediente",
    "garantia": "Usuario / expediente",
    "fabricante": "Usuario / expediente",
}


@dataclass
class FilledFieldStatus:
    key: str
    label: str
    value: str | None
    source: str | None
    status: str
    confidence: float


@dataclass
class AutofillDocumentResult:
    form_type: str
    template_slug: str
    template_path: str
    template_version: str
    template_hash: str
    docx_path: str | None
    pdf_path: str | None
    docx_filename: str | None
    pdf_filename: str | None
    fields: list[FilledFieldStatus] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)
    pdf_bytes: bytes = b""
    docx_bytes: bytes = b""
    audit_record: dict = field(default_factory=dict)
    pdf_engine: str = "libreoffice"
    template_source_type: str = "local"
    m365_template: dict | None = None
    alias_fields: list[dict] = field(default_factory=list)
    can_pass: bool = False
    ready_for_signature: bool = False
    generate_allowed: bool = False
    draft_allowed: bool = True
    completion_status: str = "PARTIAL"
    alias_summary: dict = field(default_factory=dict)
    unmapped_fields: list[str] = field(default_factory=list)
    fields_detected: int = 0
    template_cache_status: dict | None = None
    template_status: str = "unknown"  # official | unavailable | stub_blocked


# Campos mínimos para marcar listo para firma cuando la plantilla no expone aliases Word
FORM_SIGNATURE_REQUIRED: dict[str, tuple[str, ...]] = {
    "SNCC.F033": ("razon_social", "rnc", "representante_legal", "proceso_dgcp", "fecha"),
    "SNCC.F034": ("razon_social", "rnc", "representante_legal", "proceso_dgcp", "fecha"),
    "SNCC.F042": ("razon_social", "rnc", "representante_legal", "direccion", "telefono", "correo", "proceso_dgcp", "fecha"),
    "SNCC.F047": ("razon_social", "rnc", "direccion", "cuenta_bancaria", "proceso_dgcp", "fecha"),
}


def _form_signature_ready(
    form_type: str,
    values: dict,
    field_list: list,
    *,
    detected_aliases: bool,
    alias_result,
) -> bool:
    if detected_aliases:
        return bool(alias_result.ready_for_signature)
    required = FORM_SIGNATURE_REQUIRED.get(form_type.upper().replace(" ", "."))
    if required:
        return all(values.get(k) and str(values.get(k)).strip() for k in required)
    if field_list:
        pending = [
            f
            for f in field_list
            if f.status not in ("completo", "ignorado", "no_aplica_etapa", "no_critico")
        ]
        return len(pending) == 0
    return all(values.get(k) for k in ("razon_social", "rnc"))


class DocumentAutofillService:
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
        self.analysis_svc = TemplateAnalysisService()
        self.completion = DocumentCompletionService(db=db, tenant_id=tenant_id)
        self.m365_resolver = M365TemplateResolver(db, tenant_id, user_id)
        self.alias_mapping = AliasMappingService(tenant_id)

    async def resolve_values(
        self,
        opportunity: DGCPOpportunity,
        *,
        form_type: str,
        company: str = "justech",
        user_input: dict | None = None,
        overrides: dict | None = None,
    ) -> dict[str, str]:
        form_key = form_type.upper().replace(" ", ".")
        preview = await self.completion.preview(form_type=form_key, company_key=company)
        values = dict(preview.fields)
        # Fallback estático explícito (misma fuente que missing-fields)
        static_path = Path(__file__).resolve().parent.parent / "data" / "company_profiles.json"
        if static_path.exists():
            import json as _json

            static_profiles = _json.loads(static_path.read_text(encoding="utf-8"))
            static = static_profiles.get(company.lower()) or static_profiles.get("justech", {})
            for key, val in static.items():
                if val and not values.get(key):
                    values[key] = str(val)

        values.setdefault("proceso_dgcp", f"{opportunity.code}")
        values.setdefault("entidad_contratante", opportunity.institution or "")
        values.setdefault("objeto_proceso", opportunity.title or "")
        values.setdefault("numero_expediente", opportunity.code or "")
        values.setdefault("institucion", opportunity.institution or "")
        values.setdefault("entidad_contratante", opportunity.institution or "")
        values.setdefault("monto", f"{float(opportunity.amount):,.2f} {opportunity.currency}")
        values["fecha"] = datetime.now(timezone.utc).strftime("%d/%m/%Y")

        if self.db and self.tenant_id:
            await self._enrich_from_corporate_knowledge(company, values)
            await self._enrich_from_representatives(company, values)

        self._mirror_corporate_aliases(values)

        for key, val in (user_input or {}).items():
            if val and key not in self._CORPORATE_PRIORITY_KEYS:
                values[key] = str(val)

        for key, val in (overrides or {}).items():
            if val is not None:
                values[key] = str(val)

        # Perfil corporativo prevalece sobre user_input legacy/QA en campos de identidad
        if self.db and self.tenant_id:
            await self._enrich_from_corporate_knowledge(company, values, force=True)

        self._mirror_corporate_aliases(values)
        return values

    _CORPORATE_PRIORITY_KEYS = frozenset({
        "razon_social",
        "rnc",
        "rpe",
        "direccion",
        "telefono",
        "correo",
        "representante_legal",
        "representante_autorizado",
        "cargo",
        "cargo_representante",
        "cuenta_bancaria",
    })

    async def _enrich_from_corporate_knowledge(
        self,
        company_key: str,
        values: dict[str, str],
        *,
        force: bool = False,
    ) -> None:
        from app.services.corporate_knowledge_engine import CorporateKnowledgeEngine
        from app.services.company_normalization_service import canonical_label

        knowledge = CorporateKnowledgeEngine(self.db, self.tenant_id).get_company_profile(company_key)
        if not knowledge.get("razon_social"):
            knowledge["razon_social"] = canonical_label(company_key)
        for key, val in knowledge.items():
            if not val:
                continue
            if force or not values.get(key):
                values[key] = str(val)

    @staticmethod
    def _static_corporate_profile(company_key: str) -> dict[str, str]:
        """Perfil corporativo estático (company_profiles.json)."""
        import json as _json

        from app.services.company_normalization_service import canonical_label, normalize_company_key

        path = Path(__file__).resolve().parent.parent / "data" / "company_profiles.json"
        if not path.is_file():
            return {}
        data = _json.loads(path.read_text(encoding="utf-8"))
        key = normalize_company_key(company_key) or company_key.lower().replace(" ", "_")
        prof = dict(data.get(key) or data.get("justech") or {})
        if not prof.get("razon_social"):
            prof["razon_social"] = canonical_label(key)
        return {k: str(v) for k, v in prof.items() if v}

    async def _enrich_from_representatives(self, company_key: str, values: dict[str, str]) -> None:
        from sqlalchemy import select

        from app.models.licitador_company_profile import LicitadorCompanyProfile
        from app.services.company_representative_service import CompanyRepresentativeService

        row = (
            await self.db.execute(
                select(LicitadorCompanyProfile).where(
                    LicitadorCompanyProfile.tenant_id == self.tenant_id,
                    LicitadorCompanyProfile.company_key == company_key,
                )
            )
        ).scalar_one_or_none()
        if not row:
            return

        raw = row.raw_json or {}
        if not values.get("rpe"):
            rpe = raw.get("rpe") or raw.get("proveedor_estado")
            if rpe:
                values.setdefault("rpe", str(rpe))

        if not values.get("representante_autorizado") and row.representante_legal:
            values.setdefault("representante_autorizado", row.representante_legal)
        if not values.get("cargo") and row.cargo_representante:
            values.setdefault("cargo", row.cargo_representante)

        try:
            rep_svc = CompanyRepresentativeService(self.db, self.tenant_id, user_id=self.user_id)
            summary = await rep_svc.list_representatives(row.id)
            for rep in summary.representatives:
                if rep.can_sign and rep.full_name:
                    values.setdefault("representante_autorizado", rep.full_name)
                    if rep.position:
                        values.setdefault("cargo", rep.position)
                    break
                if rep.is_legal_representative and rep.full_name:
                    values.setdefault("representante_legal", rep.full_name)
                    if rep.position:
                        values.setdefault("cargo", rep.position)
        except Exception:
            pass

    @staticmethod
    def _mirror_corporate_aliases(values: dict[str, str]) -> None:
        """Duplica claves corporativas para aliases Word/SNCC (F.042)."""
        pairs = (
            ("representante_legal", "representante_autorizado"),
            ("representante_autorizado", "representante_legal"),
            ("cargo", "cargo_representante"),
            ("cargo_representante", "cargo"),
            ("institucion", "entidad_contratante"),
            ("entidad_contratante", "institucion"),
            ("razon_social", "nombre_oferente"),
            ("numero_expediente", "proceso_dgcp"),
            ("proceso_dgcp", "numero_expediente"),
        )
        for src, dst in pairs:
            if values.get(src) and not values.get(dst):
                values[dst] = values[src]
        if values.get("rpe") and not values.get("proveedor_estado"):
            values["proveedor_estado"] = values["rpe"]

    def field_statuses(self, values: dict[str, str], analysis_keys: list[str]) -> tuple[list[FilledFieldStatus], list[str]]:
        keys = analysis_keys or list(FIELD_LABELS.keys())
        fields: list[FilledFieldStatus] = []
        missing: list[str] = []
        for key in keys:
            label = FIELD_LABELS.get(key, key.replace("_", " ").title())
            raw = values.get(key)
            is_missing = not raw or str(raw).strip() == ""
            if is_missing:
                missing.append(label)
                fields.append(
                    FilledFieldStatus(
                        key=key,
                        label=label,
                        value=None,
                        source=None,
                        status="pendiente",
                        confidence=0.0,
                    )
                )
            else:
                conf = 0.92 if key in ("razon_social", "rnc", "direccion") else 0.85
                fields.append(
                    FilledFieldStatus(
                        key=key,
                        label=label,
                        value=str(raw),
                        source=FIELD_SOURCES.get(key, "Usuario"),
                        status="completo",
                        confidence=conf,
                    )
                )
        return fields, missing

    async def _load_template(
        self,
        form_type: str,
        *,
        m365_file_id: uuid.UUID | None = None,
    ) -> tuple[bytes, object, str, M365TemplateReference | None]:
        """Carga plantilla oficial desde caché/M365. Sin fallback a stubs locales."""
        from app.services.document_autofill.form_template_registry import normalize_form_type
        from app.services.document_autofill.template_source_error import (
            OfficialTemplateUnavailableError,
            StubTemplateBlockedError,
        )

        form_key = normalize_form_type(form_type)

        async def _load_ref(ref: M365TemplateReference) -> tuple[bytes, object, str, M365TemplateReference]:
            if (ref.name or "").lower().endswith(".pdf"):
                raise OfficialTemplateUnavailableError(
                    form_key,
                    ref.name,
                    detail="Requiere plantilla DOCX editable — el autollenado no procesa PDF como plantilla.",
                )
            template_bytes = await self.m365_resolver.download_bytes(ref)
            expected_size: int | None = None
            if ref.m365_file_id:
                from app.models.m365_repository import M365RepositoryFile

                row = await self.db.get(M365RepositoryFile, ref.m365_file_id)
                expected_size = row.size_bytes if row else None
            if is_likely_stub(template_bytes, expected_size=expected_size):
                raise StubTemplateBlockedError(
                    form_key,
                    ref.name,
                    detail=f"Plantilla rechazada por tamaño/contenido sospechoso ({len(template_bytes)} bytes).",
                )
            source_label = f"m365://{ref.name}"
            analysis = self.analysis_svc.analyze_bytes(
                form_key,
                template_bytes,
                source_label=source_label,
                template_version=ref.template_version,
                file_format="docx",
            )
            source_type = "m365"
            if ref.m365_file_id and cache_status(ref.m365_file_id, expected_size=expected_size).cached:
                source_type = "m365_cache"
            return template_bytes, analysis, source_type, ref

        if m365_file_id:
            ref = await self.m365_resolver.resolve_by_file_id(m365_file_id)
            if ref:
                try:
                    return await _load_ref(ref)
                except FileNotFoundError as exc:
                    raise OfficialTemplateUnavailableError(
                        form_key, ref.name, detail=str(exc)
                    ) from exc

        ref = await self.m365_resolver.resolve(form_key)
        if ref:
            try:
                return await _load_ref(ref)
            except FileNotFoundError as exc:
                raise OfficialTemplateUnavailableError(form_key, ref.name, detail=str(exc)) from exc

        raise OfficialTemplateUnavailableError(
            form_key,
            detail=(
                f"No hay plantilla oficial indexada para {form_key}. "
                "Verifique Documentos → Plantillas y ejecute bootstrap de caché M365."
            ),
        )

    async def build_document_from_m365(
        self,
        opportunity: DGCPOpportunity,
        *,
        m365_ref: M365TemplateReference,
        template_bytes: bytes,
        form_type: str,
        company: str = "justech",
        user_input: dict | None = None,
        overrides: dict | None = None,
        persist: bool = False,
        expediente_path: Path | None = None,
        user_email: str | None = None,
        template_format: str = "docx",
    ) -> AutofillDocumentResult:
        """Rellena plantilla M365 ya descargada (copia temporal)."""
        form_key = form_type.upper().replace(" ", ".")
        source_label = f"m365://{m365_ref.name}"
        analysis = self.analysis_svc.analyze_bytes(
            form_key,
            template_bytes,
            source_label=source_label,
            template_version=m365_ref.template_version,
            file_format=template_format,
        )
        return await self._build_from_analysis(
            opportunity,
            template_bytes=template_bytes,
            analysis=analysis,
            source_type="m365",
            m365_ref=m365_ref,
            form_type=form_type,
            company=company,
            user_input=user_input,
            overrides=overrides,
            persist=persist,
            expediente_path=expediente_path,
            user_email=user_email,
        )

    async def build_document(
        self,
        opportunity: DGCPOpportunity,
        *,
        form_type: str = "SNCC.F042",
        company: str = "justech",
        user_input: dict | None = None,
        overrides: dict | None = None,
        persist: bool = False,
        expediente_path: Path | None = None,
        user_email: str | None = None,
    ) -> AutofillDocumentResult:
        template_bytes, analysis, source_type, m365_ref = await self._load_template(form_type)
        return await self._build_from_analysis(
            opportunity,
            template_bytes=template_bytes,
            analysis=analysis,
            source_type=source_type,
            m365_ref=m365_ref,
            form_type=form_type,
            company=company,
            user_input=user_input,
            overrides=overrides,
            persist=persist,
            expediente_path=expediente_path,
            user_email=user_email,
        )

    async def _build_from_analysis(
        self,
        opportunity: DGCPOpportunity,
        *,
        template_bytes: bytes,
        analysis,
        source_type: str,
        m365_ref: M365TemplateReference | None,
        form_type: str,
        company: str = "justech",
        user_input: dict | None = None,
        overrides: dict | None = None,
        persist: bool = False,
        expediente_path: Path | None = None,
        user_email: str | None = None,
    ) -> AutofillDocumentResult:
        template_hash = hashlib.sha256(template_bytes).hexdigest()[:16]

        values = await self.resolve_values(
            opportunity,
            form_type=form_type,
            company=company,
            user_input=user_input,
            overrides=overrides,
        )

        template_key = (
            _slugify(m365_ref.name.rsplit(".", 1)[0])
            if m365_ref
            else (analysis.slug if hasattr(analysis, "slug") else _slugify(form_type))
        )
        detected_category, _, _ = (
            classify_template(
                m365_ref.name,
                m365_ref.parent_path or "",
                m365_ref.document_type or "",
            )
            if m365_ref
            else classify_template(form_type, "", "")
        )
        template_context = resolve_template_context(
            m365_ref.name if m365_ref else form_type,
            detected_category=detected_category,
            parent_path=m365_ref.parent_path if m365_ref else "",
            document_type=m365_ref.document_type if m365_ref else "",
        )
        detected_aliases = extract_docx_aliases(template_bytes) if analysis.format == "docx" else []
        alias_result = self.alias_mapping.resolve_aliases(
            detected_aliases,
            values,
            template_key=template_key,
            template_name=m365_ref.name if m365_ref else form_type,
            value_sources=FIELD_SOURCES,
            opportunity_id=opportunity.id if persist else None,
            alias_overrides=overrides,
            template_context=template_context,
        )

        # Aliases numéricos M365 (familia SNCC) — relleno desde valores canónicos
        num_map = numeric_alias_map(form_type)
        _corp_static = self._static_corporate_profile(company)
        for ckey in set(num_map.values()):
            if not values.get(ckey) and _corp_static.get(ckey):
                values[ckey] = _corp_static[ckey]
        for af in alias_result.fields:
            ckey = num_map.get(af.alias_normalized)
            if not ckey:
                continue
            raw = values.get(ckey) or values.get("nombre_oferente" if ckey == "razon_social" else ckey)
            if raw and str(raw).strip():
                af.value = str(raw).strip()
                af.status = "mapeado"
                af.confidence = 0.98
                af.value_source = FIELD_SOURCES.get(ckey, "Repositorio corporativo")
                af.pending_class = "completado"
                alias_result.alias_values[af.alias_normalized] = af.value
                alias_result.alias_values[af.alias] = af.value
        for norm, ckey in num_map.items():
            raw = values.get(ckey)
            if raw and str(raw).strip():
                alias_result.alias_values.setdefault(norm, str(raw).strip())

        field_list: list[FilledFieldStatus] = []
        missing: list[str] = []

        if detected_aliases:
            for af in alias_result.fields:
                if af.pending_class in ("ignorado", "no_aplica_etapa"):
                    if af.pending_class == "no_aplica_etapa":
                        field_list.append(
                            FilledFieldStatus(
                                key=af.alias_normalized,
                                label=af.alias,
                                value=None,
                                source=None,
                                status="no_aplica_etapa",
                                confidence=af.confidence,
                            )
                        )
                    continue
                if af.status == "mapeado" and af.value:
                    field_list.append(
                        FilledFieldStatus(
                            key=af.alias_normalized,
                            label=af.alias,
                            value=af.value,
                            source=af.value_source,
                            status="completo",
                            confidence=af.confidence,
                        )
                    )
                else:
                    if af.pending_class in ("critico", "no_critico"):
                        missing.append(af.alias)
                    field_list.append(
                        FilledFieldStatus(
                            key=af.alias_normalized,
                            label=af.alias,
                            value=af.value,
                            source=af.value_source,
                            status=af.pending_class,
                            confidence=af.confidence,
                        )
                    )
            # Placeholders {{}} adicionales — omitir si la clave canónica ya está resuelta
            canonical_complete = {
                canonical_field_key(x.key)
                for x in field_list
                if x.status in ("completo", "ignorado", "no_aplica_etapa")
            }
            present_keys = {x.key for x in field_list}
            placeholder_keys = [
                f.key
                for f in analysis.fields
                if f.key not in present_keys and canonical_field_key(f.key) not in canonical_complete
            ]
            pl_fields, pl_missing = self.field_statuses(values, placeholder_keys)
            field_list.extend(pl_fields)
            missing.extend(pl_missing)
            # Campos corporativos no presentes como alias en plantilla M365
            present_keys = {x.key for x in field_list}
            present_canonical = {canonical_field_key(x.key) for x in field_list}
            for ckey in (
                "rpe",
                "direccion",
                "representante_legal",
                "representante_autorizado",
                "cargo",
                "telefono",
                "correo",
            ):
                if ckey in present_keys or canonical_field_key(ckey) in present_canonical:
                    continue
                label = FIELD_LABELS.get(ckey, ckey.replace("_", " ").title())
                raw = values.get(ckey)
                if raw and str(raw).strip():
                    field_list.append(
                        FilledFieldStatus(
                            key=ckey,
                            label=label,
                            value=str(raw),
                            source=FIELD_SOURCES.get(ckey, "Repositorio corporativo"),
                            status="completo",
                            confidence=0.9,
                        )
                    )
                else:
                    missing.append(label)
                    field_list.append(
                        FilledFieldStatus(
                            key=ckey,
                            label=label,
                            value=None,
                            source=None,
                            status="no_critico",
                            confidence=0.0,
                        )
                    )
            # Asegurar aliases numéricos en respuesta preview
            for f in field_list:
                ckey = num_map.get(f.key or "")
                if not ckey:
                    continue
                raw = values.get(ckey) or _corp_static.get(ckey)
                if raw and str(raw).strip():
                    f.value = str(raw).strip()
                    f.status = "completo"
                    f.confidence = 0.98
                    f.source = FIELD_SOURCES.get(ckey, "Repositorio corporativo")
                    if f.label in missing:
                        missing.remove(f.label)
            field_list = deduplicate_field_statuses(field_list)
            missing = [
                f.label
                for f in field_list
                if f.status not in ("completo", "ignorado", "no_aplica_etapa") and f.label
            ]
        else:
            analysis_keys = [f.key for f in analysis.fields] or list(values.keys())
            field_list, missing = self.field_statuses(values, analysis_keys)

        ready_for_signature = _form_signature_ready(
            form_type,
            values,
            field_list,
            detected_aliases=bool(detected_aliases),
            alias_result=alias_result,
        )
        if detected_aliases:
            generate_allowed = alias_result.generate_allowed
        else:
            generate_allowed = ready_for_signature
        draft_allowed = True
        can_pass = ready_for_signature
        if detected_aliases and alias_result.summary.critical_pending:
            can_pass = False

        if detected_aliases and alias_result.summary.critical_pending:
            completion_status = "BLOCKED"
        elif ready_for_signature:
            completion_status = "READY_FOR_SIGNATURE"
        elif missing:
            completion_status = "DRAFT_OK"
        else:
            completion_status = "DRAFT_OK"

        if detected_aliases:
            summary_dict = {
                "total": alias_result.summary.total,
                "completed": alias_result.summary.completed,
                "critical_pending": alias_result.summary.critical_pending,
                "non_critical_pending": alias_result.summary.non_critical_pending,
                "ignored": alias_result.summary.ignored,
                "not_applicable_stage": alias_result.summary.not_applicable_stage,
            }
        else:
            summary_dict = {
                "total": 0,
                "completed": 0,
                "critical_pending": 0,
                "non_critical_pending": 0,
                "ignored": 0,
                "not_applicable_stage": 0,
            }

        filled_docx: bytes | None = None
        pdf_bytes: bytes
        pdf_engine = "libreoffice"
        fill_stats = None
        unmapped_fields: list[str] = []
        fields_detected = 0

        if analysis.format == "docx":
            filled_docx, fill_stats = fill_docx_bytes_generic(
                template_bytes,
                values,
                alias_values=alias_result.alias_values,
            )
            unmapped_fields = fill_stats.unmapped_brackets
            fields_detected = len(fill_stats.detected)
            pdf_bytes, pdf_engine = template_to_preview_pdf(
                template_bytes=template_bytes,
                template_format="docx",
                filled_docx_bytes=filled_docx,
                values=values,
                title=f"{form_type} — {opportunity.code}",
            )
        elif analysis.format == "pdf":
            try:
                from pypdf import PdfReader as _PdfReader

                if _PdfReader(BytesIO(template_bytes)).get_fields():
                    pdf_bytes = fill_pdf_acroform(template_bytes, values)
                    pdf_engine = "pypdf_acroform"
                else:
                    pdf_bytes = template_bytes
                    pdf_engine = "pdf_passthrough"
            except Exception:
                pdf_bytes = template_bytes
                pdf_engine = "pdf_passthrough"
        else:
            pdf_bytes, pdf_engine = template_to_preview_pdf(
                template_bytes=template_bytes,
                template_format=analysis.format,
                filled_docx_bytes=filled_docx,
                values=values,
                title=f"{form_type} — {opportunity.code}",
            )

        form_key = form_type.upper().replace(" ", ".")
        slug = analysis.slug if hasattr(analysis, "slug") else form_key.lower().replace(".", "-")
        safe_name = m365_ref.name.rsplit(".", 1)[0] if m365_ref else slug
        base_name = f"{safe_name}_{opportunity.code.replace('/', '_')}_COPIA".replace(" ", "_")[:120]
        docx_path: Path | None = None
        pdf_path: Path | None = None

        template_source = str(analysis.template_path)
        if m365_ref:
            template_source = m365_ref.web_url or f"m365:{m365_ref.name}"

        cache_meta = None
        template_status = "official"
        if m365_ref and m365_ref.m365_file_id:
            from app.models.m365_repository import M365RepositoryFile

            row = await self.db.get(M365RepositoryFile, m365_ref.m365_file_id)
            cache_meta = cache_status(
                m365_ref.m365_file_id,
                expected_size=row.size_bytes if row else None,
            ).to_dict()

        audit_record: dict
        if persist:
            out_dir = expediente_path or self._expediente_dir(opportunity) / "02_Formularios_SNCC"
            out_dir.mkdir(parents=True, exist_ok=True)
            if filled_docx:
                docx_path = out_dir / f"{base_name}.docx"
                docx_path.write_bytes(filled_docx)
            pdf_path = out_dir / f"{base_name}.pdf"
            write_pdf(pdf_path, pdf_bytes)

            audit_path = out_dir / f"{base_name}_audit.json"
            audit_record = {
                "form_type": form_key,
                "opportunity_id": str(opportunity.id),
                "opportunity_code": opportunity.code,
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "generated_by_user_id": str(self.user_id) if self.user_id else None,
                "generated_by_email": user_email,
                "template_source": template_source,
                "template_source_type": source_type,
                "template_hash": template_hash,
                "template_version": analysis.template_version,
                "pdf_engine": pdf_engine,
                "note": "Copia controlada — plantilla original M365/disco intacta",
                "docx_copy": str(docx_path) if docx_path else None,
                "pdf_copy": str(pdf_path),
                "m365_template": m365_ref.audit_dict() if m365_ref else None,
                "fields": [
                    {
                        "key": f.key,
                        "label": f.label,
                        "value": f.value,
                        "source": f.source,
                        "status": f.status,
                        "confidence": f.confidence,
                    }
                    for f in field_list
                ],
                "missing": missing,
                "alias_mappings": alias_result.audit_aliases,
                "aliases_detected": len(detected_aliases),
                "aliases_mapped": alias_result.summary.completed,
                "aliases_pending": alias_result.summary.critical_pending + alias_result.summary.non_critical_pending,
                "aliases_critical_pending": alias_result.summary.critical_pending,
                "aliases_non_critical_pending": alias_result.summary.non_critical_pending,
                "aliases_ignored": alias_result.summary.ignored,
                "aliases_not_applicable_stage": alias_result.summary.not_applicable_stage,
                "process_stage": template_context.process_stage,
                "document_usage": template_context.document_usage,
                "detected_category": template_context.detected_category,
                "alias_summary": summary_dict,
                "critical_pending": alias_result.critical_pending,
                "non_critical_pending": alias_result.non_critical_pending,
                "ready_for_signature": ready_for_signature,
                "generate_allowed": generate_allowed,
                "draft_allowed": draft_allowed,
                "can_pass": can_pass,
                "completion_status": completion_status,
                "fields_detected": fields_detected,
                "unmapped_fields": unmapped_fields,
                "template_cache_status": cache_meta,
                "template_status": template_status,
            }
            audit_path.write_text(json.dumps(audit_record, ensure_ascii=False, indent=2), encoding="utf-8")
        else:
            audit_record = {
                "preview": True,
                "template_hash": template_hash,
                "template_source_type": source_type,
                "pdf_engine": pdf_engine,
                "m365_template": m365_ref.audit_dict() if m365_ref else None,
                "alias_mappings": alias_result.audit_aliases,
                "alias_summary": summary_dict,
                "critical_pending": alias_result.critical_pending,
                "non_critical_pending": alias_result.non_critical_pending,
                "ready_for_signature": ready_for_signature,
                "generate_allowed": generate_allowed,
                "can_pass": can_pass,
                "completion_status": completion_status,
                "fields_detected": fields_detected,
                "unmapped_fields": unmapped_fields,
                "template_cache_status": cache_meta,
                "template_status": template_status,
            }

        alias_fields = [
            {
                "alias": f.alias,
                "alias_normalized": f.alias_normalized,
                "canonical": f.canonical,
                "canonical_label": f.canonical_label,
                "value": f.value,
                "source": f.value_source,
                "confidence": f.confidence,
                "status": f.status,
                "mapping_source": f.mapping_source,
                "automatic": f.automatic,
                "pending_class": f.pending_class,
            }
            for f in alias_result.fields
        ]

        return AutofillDocumentResult(
            form_type=form_key,
            template_slug=slug,
            template_path=template_source,
            template_version=analysis.template_version,
            template_hash=template_hash,
            docx_path=str(docx_path) if docx_path else None,
            pdf_path=str(pdf_path) if pdf_path else None,
            docx_filename=docx_path.name if docx_path else None,
            pdf_filename=pdf_path.name if pdf_path else None,
            fields=field_list,
            missing=missing,
            pdf_bytes=pdf_bytes,
            docx_bytes=filled_docx or b"",
            audit_record=audit_record,
            pdf_engine=pdf_engine,
            template_source_type=source_type,
            m365_template=m365_ref.audit_dict() if m365_ref else None,
            alias_fields=alias_fields,
            can_pass=can_pass,
            ready_for_signature=ready_for_signature,
            generate_allowed=generate_allowed,
            draft_allowed=draft_allowed,
            completion_status=completion_status,
            alias_summary=summary_dict,
            unmapped_fields=unmapped_fields,
            fields_detected=fields_detected,
            template_cache_status=cache_meta,
            template_status=template_status,
        )

    def _expediente_dir(self, opportunity: DGCPOpportunity) -> Path:
        safe_code = opportunity.code.replace("/", "_")
        return Path(settings.expediente_storage_path) / str(self.tenant_id) / safe_code
