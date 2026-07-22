"""Servicio de vault — cifrado, enmascarado y rotación de credenciales."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.integration_connector import IntegrationCredential
from app.services.credential_vault import decrypt_secret, encrypt_secret, mask_secret


class CredentialVaultService:
    def __init__(self, db: AsyncSession):
        self.db = db

    @staticmethod
    def mask(value: str) -> str:
        return mask_secret(value)

    @staticmethod
    def encrypt(value: str) -> str:
        return encrypt_secret(value)

    @staticmethod
    def decrypt(token: str) -> str:
        return decrypt_secret(token)

    def encrypt_secrets_map(self, secrets: dict[str, str]) -> dict[str, str]:
        return {k: encrypt_secret(v) for k, v in secrets.items() if v}

    def decrypt_secrets_map(self, encrypted: dict[str, str]) -> dict[str, str]:
        out: dict[str, str] = {}
        for k, v in (encrypted or {}).items():
            try:
                out[k] = decrypt_secret(v)
            except ValueError:
                continue
        return out

    def masked_secrets_map(self, encrypted: dict[str, str]) -> dict[str, str | None]:
        plain = self.decrypt_secrets_map(encrypted)
        return {k: mask_secret(v) if v else None for k, v in plain.items()} or {
            k: mask_secret(decrypt_secret(v)) if v else None for k, v in (encrypted or {}).items()
        }

    async def rotate_credential(
        self,
        *,
        provider_id: uuid.UUID,
        credential_key: str,
        new_value: str,
        actor_id: uuid.UUID | None,
    ) -> None:
        enc = encrypt_secret(new_value)
        result = await self.db.execute(
            select(IntegrationCredential).where(
                IntegrationCredential.provider_id == provider_id,
                IntegrationCredential.credential_key == credential_key,
            )
        )
        row = result.scalar_one_or_none()
        now = datetime.now(timezone.utc)
        if row:
            row.value_encrypted = enc
            row.rotated_at = now
            row.rotated_by = actor_id
        else:
            self.db.add(
                IntegrationCredential(
                    provider_id=provider_id,
                    credential_key=credential_key,
                    value_encrypted=enc,
                    rotated_at=now,
                    rotated_by=actor_id,
                )
            )

    async def touch_last_used(self, provider_id: uuid.UUID, credential_key: str) -> None:
        result = await self.db.execute(
            select(IntegrationCredential).where(
                IntegrationCredential.provider_id == provider_id,
                IntegrationCredential.credential_key == credential_key,
            )
        )
        row = result.scalar_one_or_none()
        if row:
            row.last_used_at = datetime.now(timezone.utc)
