"""Vault de credenciales — Fernet con clave maestra fuera de la BD.

Pre-J11A: restaura el módulo referenciado por resolvers (Odoo/M365/LLM)
y prioriza `JAIOS_CREDENTIAL_ENCRYPTION_KEY` sobre el derivado de app_secret_key.
"""

from __future__ import annotations

import base64
import hashlib
import logging
import re

from cryptography.fernet import Fernet, InvalidToken

from app.config import settings

logger = logging.getLogger(__name__)

# Nunca loguear valores; solo eventos.
_REDACT = re.compile(r"(api[_-]?key|secret|token|password)\s*[:=]\s*\S+", re.I)


def _master_material() -> bytes:
    explicit = (getattr(settings, "jaios_credential_encryption_key", None) or "").strip()
    if explicit:
        # Acepta clave Fernet urlsafe-base64 o cualquier secreto → SHA-256 → Fernet key
        try:
            key = explicit.encode("ascii")
            Fernet(key)  # valida formato Fernet
            return key
        except Exception:
            return base64.urlsafe_b64encode(hashlib.sha256(explicit.encode("utf-8")).digest())
    # Fallback legacy (entornos antiguos) — documentado; preferir JAIOS_CREDENTIAL_ENCRYPTION_KEY
    digest = hashlib.sha256(settings.app_secret_key.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest)


def _fernet() -> Fernet:
    return Fernet(_master_material())


def encrypt_secret(value: str) -> str:
    if not value:
        raise ValueError("No se puede cifrar un secreto vacío")
    return _fernet().encrypt(value.encode("utf-8")).decode("ascii")


def decrypt_secret(token: str) -> str:
    try:
        return _fernet().decrypt(token.encode("ascii")).decode("utf-8")
    except InvalidToken as exc:
        raise ValueError("No se pudo descifrar la credencial almacenada") from exc


def mask_secret(value: str | None, *, visible: int = 4) -> str | None:
    if not value:
        return None
    if len(value) <= visible * 2:
        return "••••"
    return f"{value[:visible]}…{value[-visible:]}"


def redact_for_logs(message: str) -> str:
    return _REDACT.sub(r"\1=[REDACTED]", message)
