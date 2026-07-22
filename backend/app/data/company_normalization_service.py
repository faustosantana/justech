"""Normalización y deduplicación de empresas del hub documental."""

from __future__ import annotations

import re
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.licitador_company_profile import LicitadorCompanyProfile

CANONICAL_ADDRESS = "Calle Francisco Segura Sandoval #157, Reparto Alma Rosa, SDE"

REQUIRED_PROFILE_FIELDS = (
    "razon_social",
    "rnc",
    "direccion",
    "telefono",
    "correo",
    "representante_legal",
    "cedula_representante",
    "registro_mercantil",
    "datos_bancarios",
)

CANONICAL_COMPANIES: list[dict[str, Any]] = [
    {
        "key": "justech",
        "label": "Justech SRL",
        "folder": "JUSTECH",
        "aliases": frozenset({"justech", "justech_srl", "justechsrl", "justech_s_r_l"}),
    },
    {
        "key": "just_office",
        "label": "Just Office SRL",
        "folder": "JUST_OFFICE",
        "aliases": frozenset({"just_office", "justoffice", "just_office_srl", "just_office_s_r_l"}),
    },
    {
        "key": "mf_plug_safe",
        "label": "MF Plug & Safe Services SRL",
        "folder": "PLUG_SAFE",
        "aliases": frozenset({
            "plug_safe",
            "plugsafe",
            "mf_plug_safe",
            "mf_plug_&_safe_services_srl",
            "mf_plug_safe_services_srl",
        }),
    },
    {
        "key": "omni_solutions",
        "label": "Omni Solutions SRL",
        "folder": "OMNI",
        "aliases": frozenset({"omni", "omni_solutions", "omni_srl", "omni_solutions_srl"}),
    },
]

KEY_ALIASES: dict[str, str] = {}
for _c in CANONICAL_COMPANIES:
    for alias in _c["aliases"]:
        KEY_ALIASES[alias] = _c["key"]
    KEY_ALIASES[_c["key"]] = _c["key"]

COMPANY_KEYS: list[tuple[str, str]] = [(c["key"], c["label"]) for c in CANONICAL_COMPANIES]


def normalize_company_key(raw: str | None) -> str | None:
    if not raw:
        return None
    key = re.sub(r"[^a-z0-9]+", "_", raw.strip().lower()).strip("_")
    return KEY_ALIASES.get(key, key if key in {c["key"] for c in CANONICAL_COMPANIES} else key)


def normalize_razon_social(name: str | None) -> str:
    if not name:
        return ""
    return re.sub(r"\s+", " ", name.strip().upper())


def canonical_label(company_key: str) -> str:
    for c in CANONICAL_COMPANIES:
        if c["key"] == company_key:
            return c["label"]
    return company_key.replace("_", " ").title()


def company_folder(company_key: str) -> str:
    key = normalize_company_key(company_key) or company_key
    for c in CANONICAL_COMPANIES:
        if c["key"] == key:
            return c["folder"]
    return key.upper().replace(" ", "_")


def identity_onedrive_paths(company_key: str) -> tuple[str, str]:
    """Ruta primaria y fallback para identidad corporativa."""
    folder = company_folder(company_key)
    primary = f"Justech-AI/IDENTIDAD_CORPORATIVA/{folder}"
    fallback = f"Justech-AI/01_DOCUMENTOS_LEGALES/{folder}/IDENTIDAD_CORPORATIVA"
    return primary, fallback


class CompanyNormalizationService:
    def __init__(self, db: AsyncSession, tenant_id: uuid.UUID):
        self.db = db
        self.tenant_id = tenant_id

    async def list_canonical_profiles(self) -> list[LicitadorCompanyProfile]:
        """Siempre devuelve exactamente 4 empresas canónicas, deduplicadas."""
        await self._deduplicate_and_migrate()
        rows = list(
            (
                await self.db.execute(
                    select(LicitadorCompanyProfile)
                    .where(LicitadorCompanyProfile.tenant_id == self.tenant_id)
                    .order_by(LicitadorCompanyProfile.company_key)
                )
            ).scalars().all()
        )
        by_key: dict[str, LicitadorCompanyProfile] = {}
        for row in rows:
            canon = normalize_company_key(row.company_key)
            if not canon or canon not in {c["key"] for c in CANONICAL_COMPANIES}:
                continue
            existing = by_key.get(canon)
            if not existing:
                if row.company_key != canon:
                    row.company_key = canon
                by_key[canon] = row
            else:
                self._merge_profile(existing, row)

        result: list[LicitadorCompanyProfile] = []
        for canon in CANONICAL_COMPANIES:
            key = canon["key"]
            row = by_key.get(key)
            if not row:
                row = LicitadorCompanyProfile(
                    tenant_id=self.tenant_id,
                    company_key=key,
                    razon_social=canon["label"],
                    direccion=CANONICAL_ADDRESS,
                    missing_fields=list(REQUIRED_PROFILE_FIELDS),
                    completeness_score=0,
                    raw_json={},
                )
                self.db.add(row)
            elif not row.razon_social:
                row.razon_social = canon["label"]
            result.append(row)

        await self.db.commit()
        for row in result:
            await self.db.refresh(row)
        return result

    async def _deduplicate_and_migrate(self) -> None:
        rows = list(
            (
                await self.db.execute(
                    select(LicitadorCompanyProfile).where(
                        LicitadorCompanyProfile.tenant_id == self.tenant_id
                    )
                )
            ).scalars().all()
        )
        if not rows:
            return

        by_rnc: dict[str, LicitadorCompanyProfile] = {}
        by_canon: dict[str, LicitadorCompanyProfile] = {}
        to_delete: list[LicitadorCompanyProfile] = []

        for row in rows:
            canon = normalize_company_key(row.company_key)
            if canon and canon in {c["key"] for c in CANONICAL_COMPANIES}:
                row.company_key = canon
                if not row.razon_social:
                    row.razon_social = canonical_label(canon)

            rnc = (row.rnc or "").strip().replace("-", "").replace(" ", "")
            if rnc:
                if rnc in by_rnc:
                    self._merge_profile(by_rnc[rnc], row)
                    to_delete.append(row)
                    continue
                by_rnc[rnc] = row

            if canon and canon in {c["key"] for c in CANONICAL_COMPANIES}:
                if canon in by_canon:
                    self._merge_profile(by_canon[canon], row)
                    to_delete.append(row)
                else:
                    by_canon[canon] = row
            elif canon and canon not in {c["key"] for c in CANONICAL_COMPANIES}:
                mapped = normalize_company_key(row.company_key)
                if mapped in by_canon:
                    self._merge_profile(by_canon[mapped], row)
                    to_delete.append(row)

        for dup in to_delete:
            await self.db.delete(dup)

        await self.db.commit()

    @staticmethod
    def _merge_profile(target: LicitadorCompanyProfile, source: LicitadorCompanyProfile) -> None:
        """Fusiona datos del duplicado en el perfil canónico sin perder información."""
        for field in (
            "razon_social",
            "nombre_comercial",
            "rnc",
            "direccion",
            "telefono",
            "correo",
            "representante_legal",
            "cedula_representante",
            "cargo_representante",
        ):
            if not getattr(target, field, None) and getattr(source, field, None):
                setattr(target, field, getattr(source, field))

        target_raw = dict(target.raw_json or {})
        source_raw = dict(source.raw_json or {})
        for k, v in source_raw.items():
            if k not in target_raw or not target_raw[k]:
                target_raw[k] = v
        target.raw_json = target_raw

        if source.completeness_score > target.completeness_score:
            target.completeness_score = source.completeness_score
            target.missing_fields = source.missing_fields or target.missing_fields

        if not target.graph_file_id and source.graph_file_id:
            target.graph_file_id = source.graph_file_id
        if not target.source_filename and source.source_filename:
            target.source_filename = source.source_filename
        if not target.synced_at and source.synced_at:
            target.synced_at = source.synced_at
