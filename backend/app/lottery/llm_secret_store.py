"""Fundación segura de secretos LLM (Pre-J11A TD-010) — sin conectar proveedores.

Almacena API keys cifradas en reposo; nunca expone texto plano en respuestas
ni logs. Rotación y auditoría se registran como eventos estructurados.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Literal
from uuid import UUID, uuid4

from app.services.credential_vault import decrypt_secret, encrypt_secret, mask_secret, redact_for_logs

logger = logging.getLogger(__name__)

ProviderId = Literal["huawei_modelarts", "openai", "compatible"]


@dataclass
class LlmSecretRecord:
    id: UUID
    provider: ProviderId
    environment: str  # development | test | production
    label: str
    ciphertext: str
    created_at: datetime
    rotated_at: datetime | None
    created_by: UUID | None
    rotated_by: UUID | None
    active: bool = True


# Almacén en memoria para la fundación (persistencia DB en J-11A).
# No contiene secretos reales en fixtures de prueba.
_STORE: dict[UUID, LlmSecretRecord] = {}
_AUDIT: list[dict[str, Any]] = []


def _audit(event: str, **fields: Any) -> None:
    row = {
        "event": event,
        "at": datetime.now(timezone.utc).isoformat(),
        **{k: v for k, v in fields.items() if k not in ("plaintext", "api_key", "secret")},
    }
    _AUDIT.append(row)
    logger.info("llm_secret_audit %s", redact_for_logs(str(row)))


def clear_store_for_tests() -> None:
    _STORE.clear()
    _AUDIT.clear()


def store_secret(
    *,
    provider: ProviderId,
    environment: str,
    plaintext: str,
    label: str = "default",
    actor_id: UUID | None = None,
) -> dict[str, Any]:
    if not (plaintext or "").strip():
        raise ValueError("El secreto LLM no puede estar vacío")
    if environment not in ("development", "test", "production"):
        raise ValueError("environment debe ser development|test|production")

    rid = uuid4()
    now = datetime.now(timezone.utc)
    rec = LlmSecretRecord(
        id=rid,
        provider=provider,
        environment=environment,
        label=label,
        ciphertext=encrypt_secret(plaintext.strip()),
        created_at=now,
        rotated_at=None,
        created_by=actor_id,
        rotated_by=None,
        active=True,
    )
    _STORE[rid] = rec
    _audit("llm_secret.created", secret_id=str(rid), provider=provider, environment=environment, actor=str(actor_id))
    return public_view(rec)


def rotate_secret(
    secret_id: UUID,
    *,
    plaintext: str,
    actor_id: UUID | None = None,
) -> dict[str, Any]:
    rec = _STORE.get(secret_id)
    if not rec:
        raise KeyError("Secreto no encontrado")
    if not (plaintext or "").strip():
        raise ValueError("El secreto LLM no puede estar vacío")
    rec.ciphertext = encrypt_secret(plaintext.strip())
    rec.rotated_at = datetime.now(timezone.utc)
    rec.rotated_by = actor_id
    _audit("llm_secret.rotated", secret_id=str(secret_id), provider=rec.provider, actor=str(actor_id))
    return public_view(rec)


def public_view(rec: LlmSecretRecord) -> dict[str, Any]:
    """Vista administrativa — enmascarada; nunca incluye texto plano."""
    plain = decrypt_secret(rec.ciphertext)
    return {
        "id": str(rec.id),
        "provider": rec.provider,
        "environment": rec.environment,
        "label": rec.label,
        "api_key_masked": mask_secret(plain),
        "has_secret": True,
        "created_at": rec.created_at.isoformat(),
        "rotated_at": rec.rotated_at.isoformat() if rec.rotated_at else None,
        "active": rec.active,
        # Explícitamente ausente: api_key / plaintext
    }


def reveal_for_runtime(secret_id: UUID, *, environment: str) -> str:
    """Solo backend runtime — no devolver a frontend/API pública."""
    rec = _STORE.get(secret_id)
    if not rec or not rec.active:
        raise KeyError("Secreto no encontrado")
    if rec.environment != environment:
        raise PermissionError("El secreto no pertenece a este ambiente")
    _audit("llm_secret.runtime_reveal", secret_id=str(secret_id), environment=environment)
    return decrypt_secret(rec.ciphertext)


def list_public(*, environment: str | None = None) -> list[dict[str, Any]]:
    rows = list(_STORE.values())
    if environment:
        rows = [r for r in rows if r.environment == environment]
    return [public_view(r) for r in rows]


def audit_trail() -> list[dict[str, Any]]:
    return list(_AUDIT)
