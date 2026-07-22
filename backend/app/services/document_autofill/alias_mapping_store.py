"""Persistencia de mapeos alias → canónico y overrides de valor."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

from app.config import settings


def _base_dir(tenant_id: uuid.UUID) -> Path:
    return Path(settings.expediente_storage_path) / str(tenant_id) / "autofill_mappings"


def _global_path(tenant_id: uuid.UUID) -> Path:
    return _base_dir(tenant_id) / "global.json"


def _template_path(tenant_id: uuid.UUID, template_key: str) -> Path:
    safe = template_key.replace("/", "_")[:120]
    return _base_dir(tenant_id) / "templates" / f"{safe}.json"


def _document_path(tenant_id: uuid.UUID, opportunity_id: uuid.UUID, template_key: str) -> Path:
    safe_tpl = template_key.replace("/", "_")[:120]
    return _base_dir(tenant_id) / "documents" / str(opportunity_id) / f"{safe_tpl}.json"


class AliasMappingStore:
    def __init__(self, tenant_id: uuid.UUID):
        self.tenant_id = tenant_id

    def load_global(self) -> dict[str, dict]:
        path = _global_path(self.tenant_id)
        if not path.is_file():
            return {}
        return json.loads(path.read_text(encoding="utf-8")).get("aliases", {})

    def load_template(self, template_key: str) -> dict[str, dict]:
        path = _template_path(self.tenant_id, template_key)
        if not path.is_file():
            return {}
        return json.loads(path.read_text(encoding="utf-8")).get("aliases", {})

    def load_document(self, opportunity_id: uuid.UUID, template_key: str) -> dict[str, dict]:
        path = _document_path(self.tenant_id, opportunity_id, template_key)
        if not path.is_file():
            return {}
        data = json.loads(path.read_text(encoding="utf-8"))
        return {**data.get("aliases", {}), **data.get("overrides", {})}

    def save_mapping(
        self,
        alias_normalized: str,
        *,
        canonical: str | None,
        scope: str,
        template_key: str | None = None,
        opportunity_id: uuid.UUID | None = None,
        status: str = "mapeado",
        confidence: float = 0.95,
        user_email: str | None = None,
        alias_original: str | None = None,
        value: str | None = None,
    ) -> None:
        entry: dict = {
            "canonical": canonical,
            "status": status,
            "confidence": confidence,
            "alias_original": alias_original or alias_normalized,
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "updated_by": user_email,
        }
        if value is not None:
            entry["value"] = value

        if scope == "document" and opportunity_id and template_key:
            path = _document_path(self.tenant_id, opportunity_id, template_key)
            existing = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}
            if value is not None:
                overrides = existing.get("overrides", {})
                overrides[alias_normalized] = {
                    **entry,
                    "scope": "document",
                    "template_key": template_key,
                    "opportunity_id": str(opportunity_id),
                }
                existing["overrides"] = overrides
            else:
                aliases = existing.get("aliases", {})
                aliases[alias_normalized] = entry
                existing["aliases"] = aliases
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(existing, ensure_ascii=False, indent=2), encoding="utf-8")
            return

        if scope == "template" and template_key:
            path = _template_path(self.tenant_id, template_key)
            data = {"aliases": self.load_template(template_key)}
            data["aliases"][alias_normalized] = entry
        else:
            path = _global_path(self.tenant_id)
            data = {"aliases": self.load_global()}
            data["aliases"][alias_normalized] = entry
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def save_value_override(
        self,
        alias_normalized: str,
        value: str,
        *,
        scope: str,
        template_key: str | None = None,
        opportunity_id: uuid.UUID | None = None,
        user_email: str | None = None,
        alias_original: str | None = None,
    ) -> None:
        self.save_mapping(
            alias_normalized,
            canonical=None,
            scope=scope,
            template_key=template_key,
            opportunity_id=opportunity_id,
            status="mapeado",
            confidence=1.0,
            user_email=user_email,
            alias_original=alias_original,
            value=value,
        )
