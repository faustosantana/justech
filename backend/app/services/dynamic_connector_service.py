"""CRUD y pruebas de conectores dinámicos."""

from __future__ import annotations

import json
import re
import uuid
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urljoin

import httpx
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.integration_connector import (
    IntegrationAuditLog,
    IntegrationEndpoint,
    IntegrationProvider,
    IntegrationTestLog,
    IntegrationUserLink,
)
from app.models.user import User
from app.services.credential_vault_service import CredentialVaultService


def _slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug[:80] or "connector"


def _status(provider: IntegrationProvider) -> str:
    if not provider.base_url:
        return "not_configured"
    if provider.last_test_ok is False:
        return "credential_error"
    if provider.connected:
        return "read_only" if provider.read_only else "read_write"
    if provider.base_url:
        return "configured"
    return "not_configured"


class DynamicConnectorService:
    SECRET_KEYS = (
        "api_key",
        "token",
        "client_secret",
        "password",
        "bearer_token",
        "verify_token",
        "access_token",
    )

    def __init__(self, db: AsyncSession, tenant_id: uuid.UUID, actor_id: uuid.UUID | None = None):
        self.db = db
        self.tenant_id = tenant_id
        self.actor_id = actor_id
        self.vault = CredentialVaultService(db)

    async def _audit(self, action: str, *, provider_id: uuid.UUID | None = None, details: dict | None = None) -> None:
        self.db.add(
            IntegrationAuditLog(
                tenant_id=self.tenant_id,
                provider_id=provider_id,
                user_id=self.actor_id,
                action=action,
                details=details or {},
            )
        )

    async def list_providers(self) -> list[dict]:
        result = await self.db.execute(
            select(IntegrationProvider)
            .where(IntegrationProvider.tenant_id == self.tenant_id, IntegrationProvider.is_builtin.is_(False))
            .order_by(IntegrationProvider.name)
        )
        rows = list(result.scalars().all())
        out = []
        for row in rows:
            ep_count = await self.db.scalar(
                select(func.count()).select_from(IntegrationEndpoint).where(IntegrationEndpoint.provider_id == row.id)
            )
            link_count = await self.db.scalar(
                select(func.count()).select_from(IntegrationUserLink).where(IntegrationUserLink.provider_id == row.id)
            )
            out.append(self._summary(row, endpoint_count=int(ep_count or 0), user_link_count=int(link_count or 0)))
        return out

    def _summary(self, row: IntegrationProvider, *, endpoint_count: int = 0, user_link_count: int = 0) -> dict:
        return {
            "id": str(row.id),
            "slug": row.slug,
            "name": row.name,
            "connector_type": row.connector_type,
            "auth_method": row.auth_method,
            "base_url": row.base_url,
            "is_active": row.is_active,
            "is_builtin": row.is_builtin,
            "is_dynamic": not row.is_builtin,
            "connected": row.connected,
            "status": _status(row),
            "read_only": row.read_only,
            "environment": row.environment,
            "user_link_mode": row.user_link_mode,
            "last_test_at": row.last_test_at,
            "last_test_ok": row.last_test_ok,
            "last_test_message": row.last_test_message,
            "endpoint_count": endpoint_count,
            "user_link_count": user_link_count,
        }

    async def get_provider(self, provider_id: uuid.UUID) -> dict:
        row = await self._get_row(provider_id)
        eps = await self._endpoints(provider_id)
        logs = await self._recent_tests(provider_id, limit=10)
        secrets_plain = self.vault.decrypt_secrets_map(row.secrets_encrypted)
        return {
            "id": row.id,
            "slug": row.slug,
            "name": row.name,
            "connector_type": row.connector_type,
            "auth_method": row.auth_method,
            "base_url": row.base_url,
            "config": row.config or {},
            "secrets_masked": {k: self.vault.mask(v) for k, v in secrets_plain.items()},
            "is_active": row.is_active,
            "is_builtin": row.is_builtin,
            "user_link_mode": row.user_link_mode,
            "documentation": row.documentation,
            "read_only": row.read_only,
            "environment": row.environment,
            "connected": row.connected,
            "status": _status(row),
            "last_test_at": row.last_test_at,
            "last_test_ok": row.last_test_ok,
            "last_test_message": row.last_test_message,
            "endpoints": eps,
            "recent_test_logs": logs,
        }

    async def create_provider(self, payload: dict) -> dict:
        base_slug = _slugify(payload["name"])
        slug = base_slug
        n = 1
        while await self._slug_exists(slug):
            slug = f"{base_slug}-{n}"
            n += 1

        secrets = self.vault.encrypt_secrets_map(payload.get("secrets") or {})
        row = IntegrationProvider(
            tenant_id=self.tenant_id,
            slug=slug,
            name=payload["name"],
            connector_type=payload.get("connector_type", "rest_api"),
            auth_method=payload.get("auth_method", "api_key"),
            base_url=payload.get("base_url"),
            config=payload.get("config") or {},
            secrets_encrypted=secrets,
            user_link_mode=payload.get("user_link_mode", "none"),
            documentation=payload.get("documentation"),
            read_only=bool(payload.get("read_only", True)),
            environment=payload.get("environment") or settings.app_env or "development",
            created_by=self.actor_id,
            updated_by=self.actor_id,
        )
        self.db.add(row)
        await self.db.flush()

        for i, ep in enumerate(payload.get("endpoints") or []):
            self.db.add(
                IntegrationEndpoint(
                    provider_id=row.id,
                    name=ep["name"],
                    path=ep["path"],
                    http_method=ep.get("http_method", "GET"),
                    query_params=ep.get("query_params") or {},
                    body_template=ep.get("body_template"),
                    headers=ep.get("headers") or {},
                    response_hint=ep.get("response_hint") or {},
                    transform=ep.get("transform") or {},
                    assistant_enabled=bool(ep.get("assistant_enabled", False)),
                    sort_order=ep.get("sort_order", i),
                )
            )

        await self._audit("connector.created", provider_id=row.id, details={"name": row.name, "slug": slug})
        await self.db.commit()
        return await self.get_provider(row.id)

    async def update_provider(self, provider_id: uuid.UUID, payload: dict) -> dict:
        row = await self._get_row(provider_id)
        for field in ("name", "connector_type", "auth_method", "base_url", "user_link_mode", "documentation", "environment"):
            if payload.get(field) is not None:
                setattr(row, field, payload[field])
        if payload.get("read_only") is not None:
            row.read_only = bool(payload["read_only"])
        if payload.get("is_active") is not None:
            row.is_active = bool(payload["is_active"])
        if payload.get("connected") is not None:
            row.connected = bool(payload["connected"])
        if payload.get("config") is not None:
            row.config = {**(row.config or {}), **payload["config"]}
        enc = dict(row.secrets_encrypted or {})
        for k in payload.get("delete_secrets") or []:
            enc.pop(k, None)
        for k, v in (payload.get("secrets") or {}).items():
            if v:
                enc[k] = self.vault.encrypt(v)
                await self.vault.rotate_credential(
                    provider_id=provider_id, credential_key=k, new_value=v, actor_id=self.actor_id
                )
        row.secrets_encrypted = enc
        row.updated_by = self.actor_id
        await self._audit("connector.updated", provider_id=row.id, details={"fields": list(payload.keys())})
        await self.db.commit()
        return await self.get_provider(provider_id)

    async def delete_provider(self, provider_id: uuid.UUID) -> None:
        row = await self._get_row(provider_id)
        if row.is_builtin:
            raise ValueError("No se puede eliminar un conector integrado del sistema")
        await self._audit("connector.deleted", provider_id=row.id, details={"name": row.name})
        await self.db.delete(row)
        await self.db.commit()

    async def test_provider(self, provider_id: uuid.UUID) -> dict:
        row = await self._get_row(provider_id)
        url = (row.base_url or "").rstrip("/")
        if not url:
            return {"ok": False, "message": "Indique la URL base del conector", "http_status": None, "response_preview": None, "details": {}}

        headers = dict((row.config or {}).get("custom_headers") or {})
        headers.update(self._auth_headers(row))
        timeout = float((row.config or {}).get("timeout") or 30)
        req_summary = f"{row.auth_method} GET {url}"

        try:
            async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
                resp = await client.get(url, headers=headers)
            preview = (resp.text or "")[:2000]
            ok = resp.status_code < 400
            message = f"HTTP {resp.status_code}" if ok else f"Error HTTP {resp.status_code}"
            row.last_test_at = datetime.now(timezone.utc)
            row.last_test_ok = ok
            row.last_test_message = message
            row.connected = ok
            self.db.add(
                IntegrationTestLog(
                    provider_id=row.id,
                    ok=ok,
                    http_status=resp.status_code,
                    request_summary=req_summary,
                    response_summary=preview[:500],
                    error_message=None if ok else message,
                    tested_by=self.actor_id,
                )
            )
            await self._audit("connector.tested", provider_id=row.id, details={"ok": ok, "http_status": resp.status_code})
            await self.db.commit()
            return {
                "ok": ok,
                "message": message,
                "http_status": resp.status_code,
                "response_preview": preview,
                "details": {"headers_sent": list(headers.keys())},
            }
        except Exception as exc:
            row.last_test_at = datetime.now(timezone.utc)
            row.last_test_ok = False
            row.last_test_message = str(exc)
            row.connected = False
            self.db.add(
                IntegrationTestLog(
                    provider_id=row.id,
                    ok=False,
                    request_summary=req_summary,
                    error_message=str(exc),
                    tested_by=self.actor_id,
                )
            )
            await self._audit("connector.test_failed", provider_id=row.id, details={"error": str(exc)})
            await self.db.commit()
            return {"ok": False, "message": str(exc), "http_status": None, "response_preview": None, "details": {}}

    async def test_endpoint(self, provider_id: uuid.UUID, endpoint_id: uuid.UUID, variables: dict | None = None) -> dict:
        row = await self._get_row(provider_id)
        ep = await self._get_endpoint(endpoint_id, provider_id)
        base = (row.base_url or "").rstrip("/") + "/"
        path = self._render_template(ep.path, variables or {})
        url = urljoin(base, path.lstrip("/"))
        headers = dict((row.config or {}).get("custom_headers") or {})
        headers.update(ep.headers or {})
        headers.update(self._auth_headers(row))
        method = ep.http_method.upper()
        timeout = float((row.config or {}).get("timeout") or 30)
        body = self._render_template(ep.body_template, variables or {}) if ep.body_template else None
        req_summary = f"{method} {url}"

        try:
            async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
                resp = await client.request(method, url, headers=headers, content=body, params=ep.query_params or {})
            preview = (resp.text or "")[:2000]
            ok = resp.status_code < 400
            self.db.add(
                IntegrationTestLog(
                    provider_id=row.id,
                    endpoint_id=ep.id,
                    ok=ok,
                    http_status=resp.status_code,
                    request_summary=req_summary,
                    response_summary=preview[:500],
                    error_message=None if ok else f"HTTP {resp.status_code}",
                    tested_by=self.actor_id,
                )
            )
            await self.db.commit()
            return {
                "ok": ok,
                "message": f"HTTP {resp.status_code}",
                "http_status": resp.status_code,
                "response_preview": preview,
                "details": {"endpoint": ep.name},
            }
        except Exception as exc:
            self.db.add(
                IntegrationTestLog(
                    provider_id=row.id,
                    endpoint_id=ep.id,
                    ok=False,
                    request_summary=req_summary,
                    error_message=str(exc),
                    tested_by=self.actor_id,
                )
            )
            await self.db.commit()
            return {"ok": False, "message": str(exc), "http_status": None, "response_preview": None, "details": {}}

    def _auth_headers(self, row: IntegrationProvider) -> dict[str, str]:
        secrets = self.vault.decrypt_secrets_map(row.secrets_encrypted)
        cfg = row.config or {}
        auth = row.auth_method
        headers: dict[str, str] = {}
        header_name = cfg.get("header_name") or "Authorization"

        if auth == "api_key":
            key = secrets.get("api_key") or secrets.get("token")
            if key:
                if header_name.lower() == "authorization":
                    headers["Authorization"] = f"Bearer {key}" if not key.startswith("Bearer ") else key
                else:
                    headers[header_name] = key
        elif auth == "bearer_token":
            token = secrets.get("bearer_token") or secrets.get("token") or secrets.get("api_key")
            if token:
                headers["Authorization"] = f"Bearer {token}" if not token.startswith("Bearer ") else token
        elif auth == "basic_auth":
            import base64

            user = cfg.get("username") or secrets.get("username") or ""
            pwd = secrets.get("password") or secrets.get("api_key") or ""
            if user or pwd:
                raw = base64.b64encode(f"{user}:{pwd}".encode()).decode()
                headers["Authorization"] = f"Basic {raw}"
        return headers

    @staticmethod
    def _render_template(template: str | None, variables: dict) -> str:
        if not template:
            return ""
        out = template
        for key, val in variables.items():
            out = out.replace(f"{{{{{key}}}}}", str(val))
        return out

    async def list_endpoints(self, provider_id: uuid.UUID) -> list[dict]:
        return await self._endpoints(provider_id)

    async def create_endpoint(self, provider_id: uuid.UUID, payload: dict) -> dict:
        await self._get_row(provider_id)
        allowed = {
            "name", "path", "http_method", "query_params", "body_template",
            "headers", "response_hint", "transform", "assistant_enabled", "sort_order",
        }
        ep = IntegrationEndpoint(provider_id=provider_id, **{k: v for k, v in payload.items() if k in allowed})
        self.db.add(ep)
        await self._audit("connector.endpoint_created", provider_id=provider_id, details={"name": payload.get("name")})
        await self.db.commit()
        await self.db.refresh(ep)
        return self._endpoint_dict(ep)

    async def update_endpoint(self, provider_id: uuid.UUID, endpoint_id: uuid.UUID, payload: dict) -> dict:
        ep = await self._get_endpoint(endpoint_id, provider_id)
        for k, v in payload.items():
            if v is not None and hasattr(ep, k):
                setattr(ep, k, v)
        await self.db.commit()
        await self.db.refresh(ep)
        return self._endpoint_dict(ep)

    async def delete_endpoint(self, provider_id: uuid.UUID, endpoint_id: uuid.UUID) -> None:
        ep = await self._get_endpoint(endpoint_id, provider_id)
        await self.db.delete(ep)
        await self.db.commit()

    async def list_user_links(self, provider_id: uuid.UUID) -> list[dict]:
        await self._get_row(provider_id)
        result = await self.db.execute(
            select(IntegrationUserLink, User)
            .join(User, User.id == IntegrationUserLink.user_id)
            .where(IntegrationUserLink.provider_id == provider_id)
            .order_by(IntegrationUserLink.linked_at.desc())
        )
        return [
            {
                "id": link.id,
                "user_id": link.user_id,
                "user_email": user.email,
                "user_name": user.full_name,
                "external_account_id": link.external_account_id,
                "external_account_label": link.external_account_label,
                "status": link.status,
                "is_active": link.is_active,
                "last_used_at": link.last_used_at,
                "linked_at": link.linked_at,
            }
            for link, user in result.all()
        ]

    async def link_user(self, provider_id: uuid.UUID, user_id: uuid.UUID, payload: dict) -> dict:
        await self._get_row(provider_id)
        result = await self.db.execute(
            select(IntegrationUserLink).where(
                IntegrationUserLink.provider_id == provider_id,
                IntegrationUserLink.user_id == user_id,
            )
        )
        row = result.scalar_one_or_none()
        if row:
            row.external_account_id = payload.get("external_account_id") or row.external_account_id
            row.external_account_label = payload.get("external_account_label") or row.external_account_label
            row.link_metadata = {**(row.link_metadata or {}), **(payload.get("metadata") or {})}
            row.is_active = True
            row.status = "linked"
        else:
            row = IntegrationUserLink(
                provider_id=provider_id,
                user_id=user_id,
                external_account_id=payload.get("external_account_id"),
                external_account_label=payload.get("external_account_label"),
                link_metadata=payload.get("metadata") or {},
            )
            self.db.add(row)
        await self._audit("connector.user_linked", provider_id=provider_id, details={"user_id": str(user_id)})
        await self.db.commit()
        links = await self.list_user_links(provider_id)
        return next(l for l in links if l["user_id"] == user_id)

    async def unlink_user(self, provider_id: uuid.UUID, user_id: uuid.UUID) -> None:
        result = await self.db.execute(
            select(IntegrationUserLink).where(
                IntegrationUserLink.provider_id == provider_id,
                IntegrationUserLink.user_id == user_id,
            )
        )
        row = result.scalar_one_or_none()
        if row:
            row.is_active = False
            row.status = "unlinked"
            await self._audit("connector.user_unlinked", provider_id=provider_id, details={"user_id": str(user_id)})
            await self.db.commit()

    async def get_logs(self, provider_id: uuid.UUID, *, limit: int = 50) -> dict:
        await self._get_row(provider_id)
        tests = await self._recent_tests(provider_id, limit=limit)
        result = await self.db.execute(
            select(IntegrationAuditLog)
            .where(IntegrationAuditLog.provider_id == provider_id)
            .order_by(IntegrationAuditLog.created_at.desc())
            .limit(limit)
        )
        audits = [
            {
                "id": r.id,
                "action": r.action,
                "user_id": r.user_id,
                "details": r.details or {},
                "created_at": r.created_at,
            }
            for r in result.scalars().all()
        ]
        return {"test_logs": tests, "audit_logs": audits, "total": len(tests) + len(audits)}

    async def _get_row(self, provider_id: uuid.UUID) -> IntegrationProvider:
        result = await self.db.execute(
            select(IntegrationProvider).where(
                IntegrationProvider.id == provider_id,
                IntegrationProvider.tenant_id == self.tenant_id,
            )
        )
        row = result.scalar_one_or_none()
        if not row:
            raise ValueError("Conector no encontrado")
        return row

    async def _slug_exists(self, slug: str) -> bool:
        result = await self.db.execute(
            select(IntegrationProvider.id).where(
                IntegrationProvider.tenant_id == self.tenant_id,
                IntegrationProvider.slug == slug,
            )
        )
        return result.scalar_one_or_none() is not None

    async def _endpoints(self, provider_id: uuid.UUID) -> list[dict]:
        result = await self.db.execute(
            select(IntegrationEndpoint)
            .where(IntegrationEndpoint.provider_id == provider_id)
            .order_by(IntegrationEndpoint.sort_order, IntegrationEndpoint.name)
        )
        return [self._endpoint_dict(r) for r in result.scalars().all()]

    async def _get_endpoint(self, endpoint_id: uuid.UUID, provider_id: uuid.UUID) -> IntegrationEndpoint:
        result = await self.db.execute(
            select(IntegrationEndpoint).where(
                IntegrationEndpoint.id == endpoint_id,
                IntegrationEndpoint.provider_id == provider_id,
            )
        )
        ep = result.scalar_one_or_none()
        if not ep:
            raise ValueError("Endpoint no encontrado")
        return ep

    async def _recent_tests(self, provider_id: uuid.UUID, *, limit: int) -> list[dict]:
        result = await self.db.execute(
            select(IntegrationTestLog)
            .where(IntegrationTestLog.provider_id == provider_id)
            .order_by(IntegrationTestLog.created_at.desc())
            .limit(limit)
        )
        return [
            {
                "id": r.id,
                "ok": r.ok,
                "http_status": r.http_status,
                "request_summary": r.request_summary,
                "response_summary": r.response_summary,
                "error_message": r.error_message,
                "endpoint_id": r.endpoint_id,
                "created_at": r.created_at,
            }
            for r in result.scalars().all()
        ]

    @staticmethod
    def _endpoint_dict(ep: IntegrationEndpoint) -> dict:
        return {
            "id": ep.id,
            "provider_id": ep.provider_id,
            "name": ep.name,
            "path": ep.path,
            "http_method": ep.http_method,
            "query_params": ep.query_params or {},
            "body_template": ep.body_template,
            "headers": ep.headers or {},
            "response_hint": ep.response_hint or {},
            "transform": ep.transform or {},
            "assistant_enabled": ep.assistant_enabled,
            "sort_order": ep.sort_order,
            "created_at": ep.created_at,
            "updated_at": ep.updated_at,
        }
