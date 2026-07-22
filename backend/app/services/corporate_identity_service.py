"""Servicio de identidad corporativa — firmas y sellos JustechAI."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.corporate_identity import CorporateIdentityAsset
from app.schemas.corporate_identity import (
    CorporateIdentityAssetResponse,
    CorporateIdentityOverviewResponse,
    CorporateIdentityUploadResponse,
)
from app.services.audit_service import AuditService
from app.services.company_scope_filter import CompanyScopeFilter
from app.services.corporate_identity_constants import (
    CANONICAL_COMPANY_KEYS,
    COMPANY_LABELS,
    COMPANY_STAMP_FILES,
    DEFAULT_SIGNATURE_FILE,
)
from app.services.global_company_context_service import GlobalCompanyContextService


class CorporateIdentityService:
    SUBFOLDER = "09_IDENTIDAD_CORPORATIVA"

    def __init__(self, db: AsyncSession, tenant_id: uuid.UUID, *, user_id: uuid.UUID | None = None):
        self.db = db
        self.tenant_id = tenant_id
        self.user_id = user_id
        self.audit = AuditService(db)
        self.root = Path(settings.knowledge_source_path) / self.SUBFOLDER

    def identity_root(self) -> Path:
        return self.root

    def metadata(self) -> dict:
        meta_path = self.root / "metadata.json"
        if not meta_path.is_file():
            return {}
        try:
            return json.loads(meta_path.read_text(encoding="utf-8"))
        except Exception:
            return {}

    def signature_dir(self) -> Path:
        return self.root / "FIRMAS"

    def stamp_dir(self) -> Path:
        return self.root / "SELLOS"

    @staticmethod
    def normalize_company_key(company_key: str | None) -> str | None:
        if not company_key:
            return None
        key = company_key.strip().lower().replace("-", "_").replace(" ", "_")
        aliases = {
            "justoffice": "just_office",
            "just_office_srl": "just_office",
            "plugsafe": "mf_plug_safe",
            "mf_plug_&_safe_services_srl": "mf_plug_safe",
            "omni": "omni_solutions",
        }
        return aliases.get(key, key)

    def stamp_filename_for_company(self, company_key: str) -> str:
        meta = self.metadata()
        companies = meta.get("companies") or {}
        normalized = self.normalize_company_key(company_key) or company_key
        if normalized in companies and companies[normalized].get("stamp"):
            return companies[normalized]["stamp"]
        return COMPANY_STAMP_FILES.get(normalized, COMPANY_STAMP_FILES.get(company_key, ""))

    def default_signature_filename(self) -> str:
        meta = self.metadata()
        return meta.get("default_signature") or DEFAULT_SIGNATURE_FILE

    def placement_for(self, document_key: str = "default") -> dict:
        meta = self.metadata()
        placement = (meta.get("placement") or {}).copy()
        cfg = placement.get(document_key) or placement.get("default") or {}
        if cfg.get("inherits"):
            cfg = {**(placement.get(cfg["inherits"]) or placement.get("default") or {})}
        return cfg

    def _asset_path(self, asset_type: str, filename: str) -> Path:
        if asset_type == "signature":
            return self.signature_dir() / filename
        return self.stamp_dir() / filename

    def _file_status(self, path: Path) -> str:
        if not path.is_file():
            return "faltante"
        if path.stat().st_size < 32:
            return "requiere_revision"
        return "disponible"

    async def list_signatures(self) -> list[CorporateIdentityAssetResponse]:
        items: list[CorporateIdentityAssetResponse] = []
        default_name = self.default_signature_filename()
        path = self._asset_path("signature", default_name)
        items.append(
            self._build_asset_response(
                asset_type="signature",
                filename=default_name,
                path=path,
                company_key=None,
            )
        )
        db_assets = await self._db_assets(asset_type="signature")
        for row in db_assets:
            items.append(self._row_to_response(row))
        return items

    async def list_stamps(self) -> list[CorporateIdentityAssetResponse]:
        items: list[CorporateIdentityAssetResponse] = []
        seen: set[str] = set()
        for key in sorted(CANONICAL_COMPANY_KEYS):
            filename = self.stamp_filename_for_company(key)
            if not filename or filename in seen:
                continue
            seen.add(filename)
            path = self._asset_path("stamp", filename)
            items.append(
                self._build_asset_response(
                    asset_type="stamp",
                    filename=filename,
                    path=path,
                    company_key=key,
                )
            )
        db_assets = await self._db_assets(asset_type="stamp")
        for row in db_assets:
            items.append(self._row_to_response(row))
        return items

    async def get_overview(self, *, company_key: str | None = None) -> CorporateIdentityOverviewResponse:
        active_key = self.normalize_company_key(company_key)
        if self.user_id and not active_key:
            ctx = await GlobalCompanyContextService(self.db, self.tenant_id, self.user_id).get_context()
            if ctx.active_company_name:
                from app.services.company_scope_filter import CompanyScopeFilter

                active_key = CompanyScopeFilter.odoo_name_to_dgcp_key(ctx.active_company_name)

        signatures = await self.list_signatures()
        stamps = await self.list_stamps()
        signature = next((s for s in signatures if s.filename == self.default_signature_filename()), signatures[0] if signatures else None)
        stamp = None
        if active_key:
            expected = self.stamp_filename_for_company(active_key)
            stamp = next((s for s in stamps if s.filename == expected), None)

        missing: list[str] = []
        alerts: list[str] = []
        if not signature or signature.status == "faltante":
            missing.append(f"Firma {self.default_signature_filename()}")
            alerts.append("Falta firma corporativa (firma_fausto.png)")
        if active_key:
            if not stamp or stamp.status == "faltante":
                missing.append(f"Sello {self.stamp_filename_for_company(active_key)}")
                alerts.append(f"Falta sello para {COMPANY_LABELS.get(active_key, active_key)}")

        return CorporateIdentityOverviewResponse(
            root_path=str(self.root),
            metadata_loaded=bool(self.metadata()),
            default_signature=self.default_signature_filename(),
            active_company_key=active_key,
            active_company_label=COMPANY_LABELS.get(active_key or "", active_key),
            signature=signature,
            stamp=stamp,
            signatures=signatures,
            stamps=stamps,
            missing=missing,
            alerts=alerts,
            placement=self.placement_for("default"),
        )

    async def get_company_assets(self, company_key: str) -> CorporateIdentityOverviewResponse:
        normalized = self.normalize_company_key(company_key)
        if not normalized:
            raise ValueError("Empresa no válida")
        if self.user_id:
            label = COMPANY_LABELS.get(normalized, normalized)
            await CompanyScopeFilter(self.db, self.tenant_id, self.user_id).assert_company_name_allowed(label)
        return await self.get_overview(company_key=normalized)

    async def resolve_signature_path(self, filename: str | None = None) -> tuple[Path | None, str, str]:
        name = filename or self.default_signature_filename()
        db_row = await self._db_asset("signature", None, name)
        if db_row:
            path = self._resolve_storage_path(db_row.storage_relative_path)
            status = db_row.status if path.is_file() else "faltante"
            return (path if path.is_file() else None, name, status)
        path = self._asset_path("signature", name)
        return (path if path.is_file() else None, name, self._file_status(path))

    async def resolve_stamp_path(
        self,
        company_key: str,
        *,
        filename: str | None = None,
    ) -> tuple[Path | None, str, str]:
        normalized = self.normalize_company_key(company_key) or company_key
        name = filename or self.stamp_filename_for_company(normalized)
        if not name:
            return None, "", "faltante"
        db_row = await self._db_asset("stamp", normalized, name)
        if db_row:
            path = self._resolve_storage_path(db_row.storage_relative_path)
            status = db_row.status if path.is_file() else "faltante"
            return (path if path.is_file() else None, name, status)
        path = self._asset_path("stamp", name)
        return (path if path.is_file() else None, name, self._file_status(path))

    async def assert_stamp_allowed(self, company_key: str, stamp_filename: str) -> None:
        normalized = self.normalize_company_key(company_key) or company_key
        expected = self.stamp_filename_for_company(normalized)
        if stamp_filename != expected:
            raise ValueError(
                f"Sello no permitido para {COMPANY_LABELS.get(normalized, normalized)} — use {expected}"
            )
        if self.user_id:
            label = COMPANY_LABELS.get(normalized, normalized)
            await CompanyScopeFilter(self.db, self.tenant_id, self.user_id).assert_company_name_allowed(label)

    def _tenant_storage_dir(self, asset_type: str) -> Path:
        sub = "FIRMAS" if asset_type == "signature" else "SELLOS"
        return Path(settings.expediente_storage_path) / str(self.tenant_id) / "corporate_identity" / sub

    def _resolve_storage_path(self, storage_relative_path: str) -> Path:
        if storage_relative_path.startswith("corporate_identity/"):
            return Path(settings.expediente_storage_path) / str(self.tenant_id) / storage_relative_path
        return Path(settings.knowledge_source_path) / storage_relative_path

    async def upload_asset(
        self,
        *,
        asset_type: str,
        filename: str,
        content: bytes,
        company_key: str | None = None,
    ) -> CorporateIdentityUploadResponse:
        if not self.user_id:
            raise ValueError("Usuario requerido")
        if asset_type not in ("signature", "stamp"):
            raise ValueError("Tipo de activo inválido")
        normalized = self.normalize_company_key(company_key)
        if asset_type == "stamp" and not normalized:
            raise ValueError("company_key requerido para sello")

        safe_name = Path(filename).name
        sub = "FIRMAS" if asset_type == "signature" else "SELLOS"
        target_dir = self._tenant_storage_dir(asset_type)
        target_dir.mkdir(parents=True, exist_ok=True)
        dest = target_dir / safe_name
        dest.write_bytes(content)
        rel = f"corporate_identity/{sub}/{safe_name}"

        now = datetime.now(timezone.utc)
        row = await self._upsert_db_asset(
            asset_type=asset_type,
            company_key=normalized,
            filename=safe_name,
            storage_relative_path=rel,
            status="disponible" if len(content) > 32 else "requiere_revision",
            uploaded_at=now,
        )
        await self.audit.log(
            action="corporate_identity.upload",
            tenant_id=self.tenant_id,
            user_id=self.user_id,
            resource_type="corporate_identity_asset",
            resource_id=row.id,
            details={"asset_type": asset_type, "filename": safe_name, "company_key": normalized},
        )
        await self.db.commit()
        return CorporateIdentityUploadResponse(
            asset=self._row_to_response(row),
            message="Activo cargado correctamente",
        )

    async def get_asset_file(self, asset_id: uuid.UUID) -> tuple[bytes, str, str]:
        row = await self.db.get(CorporateIdentityAsset, asset_id)
        if not row or row.tenant_id != self.tenant_id:
            raise ValueError("Activo no encontrado")
        path = self._resolve_storage_path(row.storage_relative_path)
        if not path.is_file():
            path = self._asset_path(row.asset_type, row.filename)
        if not path.is_file():
            raise ValueError("Archivo no disponible")
        mime = "image/png" if path.suffix.lower() == ".png" else "application/octet-stream"
        return path.read_bytes(), path.name, mime

    async def detect_missing_alerts(self, company_key: str | None = None) -> list[str]:
        overview = await self.get_overview(company_key=company_key)
        return overview.alerts

    def _build_asset_response(
        self,
        *,
        asset_type: str,
        filename: str,
        path: Path,
        company_key: str | None,
    ) -> CorporateIdentityAssetResponse:
        status = self._file_status(path)
        warnings: list[str] = []
        if status == "faltante":
            warnings.append("Archivo no encontrado en repositorio")
        elif status == "requiere_revision":
            warnings.append("Archivo presente pero requiere revisión visual")
        return CorporateIdentityAssetResponse(
            asset_type=asset_type,
            company_key=company_key,
            company_label=COMPANY_LABELS.get(company_key or "", company_key),
            filename=filename,
            status=status,
            storage_relative_path=str(path.relative_to(Path(settings.knowledge_source_path)))
            if path.is_file()
            else None,
            warnings=warnings,
            preview_url=f"/api/v1/corporate-identity/assets/file?filename={filename}&asset_type={asset_type}"
            + (f"&company_key={company_key}" if company_key else ""),
        )

    async def _db_assets(self, asset_type: str) -> list[CorporateIdentityAsset]:
        result = await self.db.execute(
            select(CorporateIdentityAsset).where(
                CorporateIdentityAsset.tenant_id == self.tenant_id,
                CorporateIdentityAsset.asset_type == asset_type,
            )
        )
        return list(result.scalars().all())

    async def _db_asset(
        self,
        asset_type: str,
        company_key: str | None,
        filename: str,
    ) -> CorporateIdentityAsset | None:
        q = select(CorporateIdentityAsset).where(
            CorporateIdentityAsset.tenant_id == self.tenant_id,
            CorporateIdentityAsset.asset_type == asset_type,
            CorporateIdentityAsset.filename == filename,
        )
        if company_key:
            q = q.where(CorporateIdentityAsset.company_key == company_key)
        result = await self.db.execute(q.limit(1))
        return result.scalar_one_or_none()

    async def _upsert_db_asset(self, **fields) -> CorporateIdentityAsset:
        existing = await self._db_asset(
            fields["asset_type"],
            fields.get("company_key"),
            fields["filename"],
        )
        if existing:
            for k, v in fields.items():
                if hasattr(existing, k):
                    setattr(existing, k, v)
            existing.uploaded_by = self.user_id
            row = existing
        else:
            row = CorporateIdentityAsset(
                tenant_id=self.tenant_id,
                uploaded_by=self.user_id,
                **fields,
            )
            self.db.add(row)
        await self.db.flush()
        return row

    def _row_to_response(self, row: CorporateIdentityAsset) -> CorporateIdentityAssetResponse:
        path = self._resolve_storage_path(row.storage_relative_path)
        status = row.status if path.is_file() else "faltante"
        return CorporateIdentityAssetResponse(
            id=row.id,
            asset_type=row.asset_type,
            company_key=row.company_key,
            company_label=COMPANY_LABELS.get(row.company_key or "", row.company_key),
            filename=row.filename,
            status=status,
            storage_relative_path=row.storage_relative_path,
            uploaded_at=row.uploaded_at,
            uploaded_by=row.uploaded_by,
            preview_url=f"/api/v1/corporate-identity/assets/{row.id}/file",
        )
