import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

import bcrypt
from jose import JWTError, jwt

from app.config import settings

TOKEN_TYPE_ACCESS = "access"
TOKEN_TYPE_REFRESH = "refresh"


def hash_password(password: str) -> str:
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def create_access_token(
    *,
    subject: str,
    tenant_id: UUID | None = None,
    role: str | None = None,
    extra_claims: dict[str, Any] | None = None,
) -> str:
    expire = datetime.now(UTC) + timedelta(minutes=settings.jwt_access_token_expire_minutes)
    payload: dict[str, Any] = {
        "sub": subject,
        "exp": expire,
        "type": TOKEN_TYPE_ACCESS,
    }
    if tenant_id:
        payload["tenant_id"] = str(tenant_id)
    if role:
        payload["role"] = role
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def create_refresh_token_value() -> str:
    return secrets.token_urlsafe(48)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def decode_token(token: str) -> dict[str, Any]:
    return jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])


def verify_access_token(token: str) -> dict[str, Any] | None:
    payload, _reason = classify_access_token(token)
    return payload


def classify_access_token(token: str) -> tuple[dict[str, Any] | None, str | None]:
    """Return (payload, reject_reason). reject_reason is None when token is valid.

    Used for DEV auth telemetry; does not change acceptance rules vs verify_access_token.
    """
    if not (token or "").strip():
        return None, "token_missing"
    try:
        payload = decode_token(token)
        if payload.get("type") != TOKEN_TYPE_ACCESS:
            return None, "token_malformed"
        if not payload.get("sub"):
            return None, "subject_missing"
        return payload, None
    except JWTError as exc:
        msg = str(exc).lower()
        if "expired" in msg:
            return None, "token_expired"
        if "signature" in msg or "key" in msg:
            return None, "signature_invalid"
        return None, "token_malformed"


def generate_api_key() -> tuple[str, str, str]:
    """Returns (full_key, prefix, hash)."""
    raw = f"jaios_{secrets.token_urlsafe(32)}"
    prefix = raw[:12]
    key_hash = hashlib.sha256(raw.encode()).hexdigest()
    return raw, prefix, key_hash
