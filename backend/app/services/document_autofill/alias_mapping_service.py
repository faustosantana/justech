"""Resolución de aliases Word → valores canónicos con auditoría y clasificación."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field

from app.services.document_autofill.alias_mapping_store import AliasMappingStore
from app.services.document_autofill.field_alias_registry import (
    CANONICAL_FIELDS,
    AliasMappingSuggestion,
    canonical_value_key,
    classify_pending,
    normalize_alias,
    suggest_canonical,
)
from app.services.document_autofill.template_process_context import (
    TemplateProcessContext,
    match_post_adjudication_field,
    resolve_template_context,
)


@dataclass
class ResolvedAliasField:
    alias: str
    alias_normalized: str
    canonical: str | None
    canonical_label: str | None
    value: str | None
    value_source: str | None
    confidence: float
    status: str
    mapping_source: str
    automatic: bool
    pending_class: str = "no_critico"


@dataclass
class AliasFieldSummary:
    total: int = 0
    completed: int = 0
    critical_pending: int = 0
    non_critical_pending: int = 0
    ignored: int = 0
    not_applicable_stage: int = 0


@dataclass
class AliasResolutionResult:
    fields: list[ResolvedAliasField] = field(default_factory=list)
    alias_values: dict[str, str] = field(default_factory=dict)
    audit_aliases: list[dict] = field(default_factory=list)
    critical_pending: list[str] = field(default_factory=list)
    non_critical_pending: list[str] = field(default_factory=list)
    unresolved: list[str] = field(default_factory=list)
    summary: AliasFieldSummary = field(default_factory=AliasFieldSummary)
    ready_for_signature: bool = False
    generate_allowed: bool = False
    draft_allowed: bool = True
    can_pass: bool = False


class AliasMappingService:
    def __init__(self, tenant_id: uuid.UUID):
        self.tenant_id = tenant_id
        self.store = AliasMappingStore(tenant_id)

    def resolve_aliases(
        self,
        detected_aliases: list[str],
        canonical_values: dict[str, str],
        *,
        template_key: str | None = None,
        template_name: str = "",
        value_sources: dict[str, str] | None = None,
        opportunity_id: uuid.UUID | None = None,
        alias_overrides: dict[str, str] | None = None,
        template_context: TemplateProcessContext | None = None,
    ) -> AliasResolutionResult:
        global_map = self.store.load_global()
        template_map = self.store.load_template(template_key) if template_key else {}
        document_map = (
            self.store.load_document(opportunity_id, template_key)
            if opportunity_id and template_key
            else {}
        )
        value_sources = value_sources or {}
        alias_overrides = alias_overrides or {}
        ctx = template_context or resolve_template_context(template_name or template_key or "")

        result = AliasResolutionResult()
        seen: set[str] = set()

        for alias in detected_aliases:
            norm = normalize_alias(alias)
            if norm in seen:
                continue
            seen.add(norm)

            # Códigos SNCC numéricos (F.042 M365) — short-circuit antes de stores manuales
            sncc_numeric = {"3212": "rnc", "3213": "razon_social"}
            if norm in sncc_numeric:
                ckey = sncc_numeric[norm]
                vkey = canonical_value_key(ckey)
                val = (canonical_values.get(vkey) or canonical_values.get(ckey) or "").strip()
                if val:
                    resolved = ResolvedAliasField(
                        alias=alias,
                        alias_normalized=norm,
                        canonical=ckey,
                        canonical_label=CANONICAL_FIELDS.get(ckey, ckey),
                        value=val,
                        value_source=value_sources.get(vkey) or value_sources.get(ckey) or "Repositorio corporativo",
                        confidence=0.98,
                        status="mapeado",
                        mapping_source="sncc_numeric",
                        automatic=True,
                        pending_class="completado",
                    )
                    result.fields.append(resolved)
                    result.alias_values[norm] = val
                    result.alias_values[alias] = val
                    result.audit_aliases.append(self._audit_row(resolved))
                    continue
                # Sin valor corporativo: marcar pendiente explícito (no unresolved 0.0)
                resolved = ResolvedAliasField(
                    alias=alias,
                    alias_normalized=norm,
                    canonical=ckey,
                    canonical_label=CANONICAL_FIELDS.get(ckey, ckey),
                    value=None,
                    value_source=None,
                    confidence=0.98,
                    status="pendiente",
                    mapping_source="sncc_numeric",
                    automatic=True,
                    pending_class="critico" if ckey in ("rnc", "razon_social") else "no_critico",
                )
                result.fields.append(resolved)
                result.audit_aliases.append(self._audit_row(resolved))
                result.unresolved.append(alias)
                continue

            suggestion = suggest_canonical(
                alias,
                stored_global=global_map,
                stored_template=template_map,
                template_name=template_name,
            )

            doc_entry = document_map.get(norm, {})
            if doc_entry.get("status") == "ignorado":
                suggestion = AliasMappingSuggestion(
                    alias, norm, None, 1.0, "manual_document", "ignorado"
                )
            elif doc_entry.get("canonical"):
                suggestion = AliasMappingSuggestion(
                    alias,
                    norm,
                    doc_entry.get("canonical"),
                    float(doc_entry.get("confidence", 0.95)),
                    "manual_document",
                    "mapeado" if doc_entry.get("canonical") else "pendiente",
                )

            if suggestion.status == "ignorado" and norm not in sncc_numeric:
                resolved = ResolvedAliasField(
                    alias=alias,
                    alias_normalized=norm,
                    canonical=None,
                    canonical_label=None,
                    value=None,
                    value_source=None,
                    confidence=suggestion.confidence,
                    status="ignorado",
                    mapping_source=suggestion.source,
                    automatic=suggestion.source
                    not in ("manual_global", "manual_template", "manual_document"),
                    pending_class="ignorado",
                )
                result.fields.append(resolved)
                result.audit_aliases.append(self._audit_row(resolved))
                continue

            canonical = suggestion.canonical
            if not canonical and norm in sncc_numeric:
                canonical = sncc_numeric[norm]
                suggestion = AliasMappingSuggestion(
                    alias, norm, canonical, 0.98, "sncc_numeric", "mapeado"
                )

            value: str | None = None
            src: str | None = None

            if canonical:
                vkey = canonical_value_key(canonical)
                value = canonical_values.get(vkey) or canonical_values.get(canonical)
                src = value_sources.get(vkey) or value_sources.get(canonical)

            manual_val = None
            if opportunity_id:
                manual_val = self._lookup_manual(
                    norm,
                    alias,
                    canonical,
                    alias_overrides,
                    document_map,
                    global_map,
                    template_map,
                )
            if manual_val:
                value = manual_val
                src = "Manual / usuario"

            status = suggestion.status
            has_value = bool(value and str(value).strip())
            if has_value:
                status = "mapeado"
            elif canonical and suggestion.confidence >= 0.6:
                status = "pendiente"
            elif not canonical:
                status = "pendiente"
                result.unresolved.append(alias)

            pending_class = classify_pending(
                alias=alias,
                alias_normalized=norm,
                canonical=canonical,
                status=status if status != "ignorado" else "ignorado",
                has_value=has_value,
                process_stage=ctx.process_stage,
            )

            post_canonical = match_post_adjudication_field(alias, norm)
            if post_canonical:
                canonical = post_canonical
            if pending_class == "no_aplica_etapa":
                status = "no_aplica_etapa"
                value = None
                src = None
            elif pending_class == "critico" and not has_value:
                status = "pendiente"

            resolved = ResolvedAliasField(
                alias=alias,
                alias_normalized=norm,
                canonical=canonical,
                canonical_label=CANONICAL_FIELDS.get(canonical or "", canonical),
                value=str(value) if value else None,
                value_source=src,
                confidence=suggestion.confidence,
                status=status,
                mapping_source=suggestion.source,
                automatic=suggestion.source
                not in ("manual_global", "manual_template", "manual_document", "manual_override"),
                pending_class=pending_class,
            )
            result.fields.append(resolved)

            if status == "mapeado" and has_value:
                result.alias_values[norm] = str(value)
                result.alias_values[alias] = str(value)

            result.audit_aliases.append(self._audit_row(resolved))

        result.summary = self._build_summary(result.fields)
        result.critical_pending = [f.alias for f in result.fields if f.pending_class == "critico"]
        result.non_critical_pending = [f.alias for f in result.fields if f.pending_class == "no_critico"]
        result.ready_for_signature = result.summary.critical_pending == 0
        result.generate_allowed = result.ready_for_signature
        result.draft_allowed = True
        result.can_pass = result.ready_for_signature
        return result

    @staticmethod
    def _lookup_manual(
        norm: str,
        alias: str,
        canonical: str | None,
        alias_overrides: dict[str, str],
        document_map: dict,
        global_map: dict,
        template_map: dict,
    ) -> str | None:
        for key in (norm, alias, canonical, canonical_value_key(canonical) if canonical else None):
            if key and alias_overrides.get(key):
                return str(alias_overrides[key]).strip() or None

        doc = document_map.get(norm, {})
        if doc.get("value"):
            return str(doc["value"]).strip() or None

        for store in (template_map, global_map):
            entry = store.get(norm, {})
            if entry.get("value"):
                return str(entry["value"]).strip() or None
        return None

    @staticmethod
    def _audit_row(field: ResolvedAliasField) -> dict:
        return {
            "alias_original": field.alias,
            "alias_normalized": field.alias_normalized,
            "canonical": field.canonical,
            "value_applied": field.value,
            "source": field.value_source,
            "confidence": field.confidence,
            "automatic": field.automatic,
            "mapping_source": field.mapping_source,
            "status": field.status,
            "pending_class": field.pending_class,
        }

    @staticmethod
    def _build_summary(fields: list[ResolvedAliasField]) -> AliasFieldSummary:
        summary = AliasFieldSummary(total=len(fields))
        for f in fields:
            if f.pending_class == "completado":
                summary.completed += 1
            elif f.pending_class == "critico":
                summary.critical_pending += 1
            elif f.pending_class == "no_critico":
                summary.non_critical_pending += 1
            elif f.pending_class == "ignorado":
                summary.ignored += 1
            elif f.pending_class == "no_aplica_etapa":
                summary.not_applicable_stage += 1
        return summary
