"""Lottery IA conversational settings — DB-driven; OpenAI keys via credential_vault."""
from __future__ import annotations

import json
import re
import time
import uuid
from datetime import datetime, timezone
from typing import Any

import httpx
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.lottery.ai.conversational_orchestrator.conversation_provider_factory import (
    build_provider,
    invalidate_provider_cache,
    set_runtime_settings_cache,
)
from app.lottery.ai.conversational_orchestrator.schema import (
    ORCHESTRATOR_JSON_SCHEMA_HINT,
    parse_orchestrator_decision,
)
from app.models.lottery import LotteryAiSettings
from app.services.credential_vault import (
    decrypt_secret,
    encrypt_secret,
    redact_for_logs,
)

SUGGESTED_MODELS: dict[str, list[str]] = {
    "huawei": [
        "deepseek-v4-flash",
        "deepseek-v3",
        "DeepSeek-V3.2",
        "DeepSeek-V3",
    ],
    "openai": [
        "gpt-5",
        "gpt-5-mini",
        "gpt-4.1",
        "gpt-4o",
    ],
}

DEFAULTS: dict[str, Any] = {
    "conversation_provider": "huawei",
    "conversation_model": "deepseek-v4-flash",
    "temperature": 0.0,
    "max_tokens": 700,
    "timeout_seconds": 45,
    "openai_base_url": "https://api.openai.com/v1",
}


def _mask_openai_key(plain: str | None) -> str | None:
    if not plain:
        return None
    if plain.startswith("sk-") and len(plain) > 8:
        return f"sk-••••••••{plain[-4:]}"
    if len(plain) <= 8:
        return "••••"
    return f"{plain[:2]}••••••••{plain[-4:]}"


def _public_dict(row: LotteryAiSettings) -> dict[str, Any]:
    """API-safe payload — never includes plaintext or ciphertext of the API key."""
    configured = bool(getattr(row, "openai_api_key_encrypted", None))
    mask = None
    if configured:
        try:
            mask = _mask_openai_key(decrypt_secret(str(row.openai_api_key_encrypted)))
        except Exception:  # noqa: BLE001
            mask = "sk-••••••••****"
    return {
        "id": str(row.id),
        "conversation_provider": row.conversation_provider,
        "conversation_model": row.conversation_model,
        "temperature": float(row.temperature or 0),
        "max_tokens": int(row.max_tokens or 700),
        "timeout_seconds": int(row.timeout_seconds or 45),
        "is_active": bool(row.is_active),
        "openai_key_configured": configured,
        "openai_key_mask": mask,
        "openai_base_url": row.openai_base_url or DEFAULTS["openai_base_url"],
        "openai_organization": row.openai_organization,
        "openai_project": row.openai_project,
        "credential_updated_at": row.credential_updated_at.isoformat()
        if row.credential_updated_at
        else None,
        "credential_updated_by": str(row.credential_updated_by)
        if row.credential_updated_by
        else None,
        "last_test_at": row.last_test_at.isoformat() if row.last_test_at else None,
        "last_test_ok": row.last_test_ok,
        "last_test_latency_ms": float(row.last_test_latency_ms)
        if row.last_test_latency_ms is not None
        else None,
        "last_test_model": row.last_test_model,
        "last_test_error": row.last_test_error,
        "last_test_message": (row.last_test_message or "")[:500] if row.last_test_message else None,
        "updated_by": str(row.updated_by) if row.updated_by else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
        "suggested_models": SUGGESTED_MODELS,
        "catalog": SUGGESTED_MODELS,
    }


def _cache_from_row(row: LotteryAiSettings) -> dict[str, Any]:
    """In-process cache payload (includes encrypted blob, never plaintext)."""
    return {
        "conversation_provider": row.conversation_provider,
        "conversation_model": row.conversation_model,
        "temperature": float(row.temperature or 0),
        "max_tokens": int(row.max_tokens or 700),
        "timeout_seconds": int(row.timeout_seconds or 45),
        "openai_api_key_encrypted": getattr(row, "openai_api_key_encrypted", None),
        "openai_base_url": row.openai_base_url,
        "openai_organization": row.openai_organization,
        "openai_project": row.openai_project,
    }


def _validate_payload(body: dict[str, Any]) -> dict[str, Any]:
    provider = str(body.get("conversation_provider") or "huawei").strip().lower()
    if provider not in {"huawei", "openai"}:
        raise ValueError("conversation_provider debe ser huawei u openai")
    model = str(body.get("conversation_model") or "").strip()
    if not model:
        model = SUGGESTED_MODELS[provider][0]
    try:
        temperature = float(body.get("temperature", DEFAULTS["temperature"]))
    except (TypeError, ValueError) as e:
        raise ValueError("temperature inválida") from e
    temperature = max(0.0, min(2.0, temperature))
    try:
        max_tokens = int(body.get("max_tokens", DEFAULTS["max_tokens"]))
    except (TypeError, ValueError) as e:
        raise ValueError("max_tokens inválido") from e
    max_tokens = max(64, min(8192, max_tokens))
    try:
        timeout_seconds = int(body.get("timeout_seconds", DEFAULTS["timeout_seconds"]))
    except (TypeError, ValueError) as e:
        raise ValueError("timeout_seconds inválido") from e
    timeout_seconds = max(5, min(300, timeout_seconds))
    base_url = str(body.get("openai_base_url") or DEFAULTS["openai_base_url"]).strip()
    org = str(body.get("openai_organization") or "").strip() or None
    project = str(body.get("openai_project") or "").strip() or None
    # Form key — never logged; empty means keep existing
    form_key = body.get("openai_api_key")
    if form_key is not None:
        form_key = str(form_key).strip() or None
    return {
        "conversation_provider": provider,
        "conversation_model": model,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "timeout_seconds": timeout_seconds,
        "openai_base_url": base_url,
        "openai_organization": org,
        "openai_project": project,
        "openai_api_key": form_key,
    }


class LotteryAiConversationSettingsService:
    def __init__(self, db: AsyncSession, *, user_id: uuid.UUID | None = None):
        self.db = db
        self.user_id = user_id

    async def _active_row(self) -> LotteryAiSettings | None:
        return (
            await self.db.execute(
                select(LotteryAiSettings)
                .where(LotteryAiSettings.is_active.is_(True))
                .order_by(LotteryAiSettings.updated_at.desc())
                .limit(1)
            )
        ).scalar_one_or_none()

    async def get_or_create_active(self) -> dict[str, Any]:
        row = await self._active_row()
        if row is None:
            row = LotteryAiSettings(
                id=uuid.uuid4(),
                conversation_provider=DEFAULTS["conversation_provider"],
                conversation_model=DEFAULTS["conversation_model"],
                temperature=DEFAULTS["temperature"],
                max_tokens=DEFAULTS["max_tokens"],
                timeout_seconds=DEFAULTS["timeout_seconds"],
                openai_base_url=DEFAULTS["openai_base_url"],
                is_active=True,
                updated_by=self.user_id,
            )
            self.db.add(row)
            await self.db.flush()
            await self.db.refresh(row)
        set_runtime_settings_cache(_cache_from_row(row))
        invalidate_provider_cache()
        return _public_dict(row)

    def _build_for_test(self, cfg: dict[str, Any], row: LotteryAiSettings | None):
        key = cfg.get("openai_api_key")
        if cfg["conversation_provider"] == "openai" and not key and row is not None:
            # use stored encrypted via cache
            set_runtime_settings_cache(_cache_from_row(row))
        return build_provider(
            cfg["conversation_provider"],
            model=cfg["conversation_model"],
            timeout_sec=float(cfg["timeout_seconds"]),
            api_key=key,
            base_url=cfg.get("openai_base_url"),
            organization=cfg.get("openai_organization"),
            project=cfg.get("openai_project"),
        )

    async def test_connection(self, body: dict[str, Any] | None = None) -> dict[str, Any]:
        """Real provider call with 'Hola'. Does not persist provider activation."""
        row = await self._active_row()
        if row is None:
            await self.get_or_create_active()
            row = await self._active_row()
        active_pub = _public_dict(row) if row else {}
        cfg = _validate_payload({**active_pub, **(body or {})})
        # Ensure cache has encrypted key for fallback when form omits key
        if row is not None:
            set_runtime_settings_cache(_cache_from_row(row))

        if cfg["conversation_provider"] == "openai":
            has_form = bool(cfg.get("openai_api_key"))
            has_db = bool(row and row.openai_api_key_encrypted)
            if not has_form and not has_db:
                from app.config import settings as app_settings

                if not (app_settings.openai_api_key or "").strip():
                    return {
                        "ok": False,
                        "provider": "openai",
                        "model": cfg["conversation_model"],
                        "latency_ms": 0,
                        "total_ms": 0,
                        "status": "provider_unavailable",
                        "message_received": None,
                        "schema_valid": False,
                        "credential_source": "none",
                        "errors": ["Falta API Key de OpenAI (ingrésala en el formulario)"],
                    }

        provider = self._build_for_test(cfg, row)
        cred_source = getattr(provider, "credential_source", "n/a")
        t0 = time.perf_counter()
        if not provider.available():
            return {
                "ok": False,
                "provider": cfg["conversation_provider"],
                "model": cfg["conversation_model"],
                "latency_ms": 0,
                "total_ms": round((time.perf_counter() - t0) * 1000, 1),
                "status": "provider_unavailable",
                "message_received": None,
                "schema_valid": False,
                "credential_source": cred_source,
                "errors": ["Credenciales del proveedor no disponibles"],
            }
        system = (
            "Eres un orquestador. Responde SOLO JSON con este schema:\n"
            + ORCHESTRATOR_JSON_SCHEMA_HINT
            + "\nPara el saludo 'Hola' usa turn_type=social_chitchat y subjects=[]."
        )
        result = provider.decide(
            system_prompt=system,
            messages=[{"role": "user", "content": "Hola"}],
            schema=ORCHESTRATOR_JSON_SCHEMA_HINT,
            temperature=float(cfg["temperature"]),
            max_tokens=min(400, int(cfg["max_tokens"])),
        )
        total_ms = round((time.perf_counter() - t0) * 1000, 1)
        errors: list[str] = []
        schema_valid = False
        decision = None
        if result.provider_unavailable:
            errors.append(result.error or "provider_unavailable")
        elif result.error and not result.content:
            errors.append(redact_for_logs(result.error))
        else:
            try:
                raw = (result.content or "").strip()
                if raw.startswith("```"):
                    raw = re.sub(r"^```(?:json)?\s*", "", raw)
                    raw = re.sub(r"\s*```$", "", raw)
                obj = json.loads(raw) if raw.startswith("{") else None
                if obj is None:
                    m = re.search(r"\{.*\}", result.content or "", flags=re.S)
                    obj = json.loads(m.group(0)) if m else None
                decision, err = parse_orchestrator_decision(obj or {})
                if decision is None:
                    errors.append(err or "schema_invalid")
                else:
                    schema_valid = True
            except Exception as e:  # noqa: BLE001
                errors.append(redact_for_logs(f"json_parse_failed:{e}"))

        ok = bool(schema_valid and not errors and not result.provider_unavailable)
        if row is not None:
            row.last_test_at = datetime.now(timezone.utc)
            row.last_test_ok = ok
            row.last_test_latency_ms = result.latency_ms or total_ms
            row.last_test_model = result.model or cfg["conversation_model"]
            row.last_test_error = "; ".join(errors) if errors else None
            # Never store raw provider responses that might echo secrets
            row.last_test_message = (result.content or "")[:2000]
            row.updated_at = datetime.now(timezone.utc)
            await self.db.flush()
            await self.db.refresh(row)
            set_runtime_settings_cache(_cache_from_row(row))

        return {
            "ok": ok,
            "provider": cfg["conversation_provider"],
            "model": result.model or cfg["conversation_model"],
            "latency_ms": result.latency_ms or total_ms,
            "total_ms": total_ms,
            "status": "ok" if ok else "failed",
            "message_received": (result.content or "")[:2000],
            "schema_valid": schema_valid,
            "decision": decision.model_dump() if decision else None,
            "errors": errors,
            "usage": result.usage,
            "credential_source": cred_source,
        }

    async def save(self, body: dict[str, Any], *, require_test_ok: bool = True) -> dict[str, Any]:
        prev = await self._active_row()
        cfg = _validate_payload(body)

        # OpenAI requires a key in form OR already stored
        if cfg["conversation_provider"] == "openai":
            if not cfg.get("openai_api_key") and not (
                prev and prev.openai_api_key_encrypted
            ):
                raise ValueError("OpenAI requiere API Key (ingrésala antes de guardar)")

        probe = await self.test_connection({**cfg, **(body or {})})
        if require_test_ok and not probe.get("ok"):
            raise ValueError(
                "Prueba de conexión falló; no se guardaron cambios: "
                + ", ".join(probe.get("errors") or ["unknown"])
            )

        # Resolve credential for new row
        new_enc = None
        cred_updated = False
        if cfg.get("openai_api_key"):
            new_enc = encrypt_secret(cfg["openai_api_key"])
            cred_updated = True
        elif prev and prev.openai_api_key_encrypted:
            new_enc = prev.openai_api_key_encrypted

        await self.db.execute(
            update(LotteryAiSettings)
            .where(LotteryAiSettings.is_active.is_(True))
            .values(is_active=False)
        )
        now = datetime.now(timezone.utc)
        row = LotteryAiSettings(
            id=uuid.uuid4(),
            conversation_provider=cfg["conversation_provider"],
            conversation_model=cfg["conversation_model"],
            temperature=cfg["temperature"],
            max_tokens=cfg["max_tokens"],
            timeout_seconds=cfg["timeout_seconds"],
            is_active=True,
            updated_by=self.user_id,
            openai_api_key_encrypted=new_enc,
            openai_base_url=cfg.get("openai_base_url"),
            openai_organization=cfg.get("openai_organization"),
            openai_project=cfg.get("openai_project"),
            credential_updated_at=now
            if cred_updated
            else (prev.credential_updated_at if prev else None),
            credential_updated_by=self.user_id
            if cred_updated
            else (prev.credential_updated_by if prev else None),
            last_test_at=now,
            last_test_ok=True,
            last_test_latency_ms=probe.get("latency_ms"),
            last_test_model=probe.get("model"),
            last_test_error=None,
            last_test_message=(probe.get("message_received") or "")[:2000],
            updated_at=now,
        )
        self.db.add(row)
        await self.db.flush()
        await self.db.refresh(row)
        set_runtime_settings_cache(_cache_from_row(row))
        invalidate_provider_cache()
        return {"settings": _public_dict(row), "probe": probe}

    async def delete_openai_credential(self) -> dict[str, Any]:
        row = await self._active_row()
        if row is None:
            raise ValueError("No hay configuración activa")
        row.openai_api_key_encrypted = None
        row.openai_organization = None
        row.openai_project = None
        row.credential_updated_at = datetime.now(timezone.utc)
        row.credential_updated_by = self.user_id
        if row.conversation_provider == "openai":
            row.conversation_provider = "huawei"
            row.conversation_model = DEFAULTS["conversation_model"]
        row.updated_at = datetime.now(timezone.utc)
        row.updated_by = self.user_id
        await self.db.flush()
        await self.db.refresh(row)
        set_runtime_settings_cache(_cache_from_row(row))
        invalidate_provider_cache()
        return _public_dict(row)

    async def list_openai_models(self, body: dict[str, Any] | None = None) -> dict[str, Any]:
        """Optional: list models from OpenAI using form or stored credential."""
        row = await self._active_row()
        if row is not None:
            set_runtime_settings_cache(_cache_from_row(row))
        body = body or {}
        form_key = str(body.get("openai_api_key") or "").strip() or None
        base = str(
            body.get("openai_base_url")
            or (row.openai_base_url if row else None)
            or DEFAULTS["openai_base_url"]
        ).rstrip("/")
        provider = build_provider(
            "openai",
            api_key=form_key,
            base_url=base,
            organization=body.get("openai_organization")
            or (row.openai_organization if row else None),
            project=body.get("openai_project") or (row.openai_project if row else None),
        )
        if not provider.available():
            raise ValueError("Credencial OpenAI no disponible")
        key = getattr(provider, "_api_key", None)
        url = base if base.endswith("/v1") else base.rstrip("/") + "/v1"
        if not url.endswith("/models"):
            url = url.rstrip("/") + "/models"
        with httpx.Client(timeout=30.0) as client:
            resp = client.get(
                url,
                headers={"Authorization": f"Bearer {key}"},
            )
            resp.raise_for_status()
            data = resp.json()
        ids = sorted(
            {
                str(it.get("id"))
                for it in (data.get("data") or [])
                if isinstance(it, dict) and it.get("id")
            }
        )
        return {
            "models": ids,
            "suggested": SUGGESTED_MODELS["openai"],
            "credential_source": getattr(provider, "credential_source", "none"),
        }
