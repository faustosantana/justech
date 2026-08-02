"""Lottery IA conversational settings — single active row in DB (not ENV)."""
from __future__ import annotations

import json
import time
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.lottery.ai.conversational_orchestrator.conversation_provider_factory import (
    build_provider,
    set_runtime_settings_cache,
)
from app.lottery.ai.conversational_orchestrator.schema import (
    ORCHESTRATOR_JSON_SCHEMA_HINT,
    parse_orchestrator_decision,
)
from app.models.lottery import LotteryAiSettings

PROVIDER_MODELS: dict[str, list[str]] = {
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
}


def _row_dict(row: LotteryAiSettings) -> dict[str, Any]:
    return {
        "id": str(row.id),
        "conversation_provider": row.conversation_provider,
        "conversation_model": row.conversation_model,
        "temperature": float(row.temperature or 0),
        "max_tokens": int(row.max_tokens or 700),
        "timeout_seconds": int(row.timeout_seconds or 45),
        "is_active": bool(row.is_active),
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
        "catalog": PROVIDER_MODELS,
    }


def _validate_payload(body: dict[str, Any]) -> dict[str, Any]:
    provider = str(body.get("conversation_provider") or "huawei").strip().lower()
    if provider not in PROVIDER_MODELS:
        raise ValueError("conversation_provider debe ser huawei u openai")
    model = str(body.get("conversation_model") or "").strip()
    allowed = PROVIDER_MODELS[provider]
    if model not in allowed:
        # allow custom model string if non-empty (forward compatible)
        if not model:
            model = allowed[0]
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
    return {
        "conversation_provider": provider,
        "conversation_model": model,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "timeout_seconds": timeout_seconds,
    }


class LotteryAiConversationSettingsService:
    def __init__(self, db: AsyncSession, *, user_id: uuid.UUID | None = None):
        self.db = db
        self.user_id = user_id

    async def get_or_create_active(self) -> dict[str, Any]:
        row = (
            await self.db.execute(
                select(LotteryAiSettings)
                .where(LotteryAiSettings.is_active.is_(True))
                .order_by(LotteryAiSettings.updated_at.desc())
                .limit(1)
            )
        ).scalar_one_or_none()
        if row is None:
            row = LotteryAiSettings(
                id=uuid.uuid4(),
                conversation_provider=DEFAULTS["conversation_provider"],
                conversation_model=DEFAULTS["conversation_model"],
                temperature=DEFAULTS["temperature"],
                max_tokens=DEFAULTS["max_tokens"],
                timeout_seconds=DEFAULTS["timeout_seconds"],
                is_active=True,
                updated_by=self.user_id,
            )
            self.db.add(row)
            await self.db.flush()
        data = _row_dict(row)
        set_runtime_settings_cache(data)
        return data

    async def test_connection(self, body: dict[str, Any] | None = None) -> dict[str, Any]:
        """Real provider call with message 'Hola'; does not persist settings."""
        active = await self.get_or_create_active()
        cfg = _validate_payload({**active, **(body or {})})
        provider = build_provider(
            cfg["conversation_provider"],
            model=cfg["conversation_model"],
            timeout_sec=float(cfg["timeout_seconds"]),
        )
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
                "errors": ["Credenciales del proveedor no disponibles en el entorno"],
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
            errors.append(result.error)
        else:
            try:
                raw = (result.content or "").strip()
                if raw.startswith("```"):
                    raw = raw.strip("`")
                    if raw.startswith("json"):
                        raw = raw[4:]
                obj = json.loads(raw) if raw.startswith("{") else None
                if obj is None:
                    # reuse adapter extractor lightly
                    import re

                    m = re.search(r"\{.*\}", result.content or "", flags=re.S)
                    obj = json.loads(m.group(0)) if m else None
                decision, err = parse_orchestrator_decision(obj or {})
                if decision is None:
                    errors.append(err or "schema_invalid")
                else:
                    schema_valid = True
            except Exception as e:  # noqa: BLE001
                errors.append(f"json_parse_failed:{e}")

        ok = bool(schema_valid and not errors and not result.provider_unavailable)
        # Persist test diagnostics on active row (not the draft provider unless saved)
        row = (
            await self.db.execute(
                select(LotteryAiSettings).where(LotteryAiSettings.is_active.is_(True)).limit(1)
            )
        ).scalar_one_or_none()
        if row is not None:
            row.last_test_at = datetime.now(timezone.utc)
            row.last_test_ok = ok
            row.last_test_latency_ms = result.latency_ms or total_ms
            row.last_test_model = result.model or cfg["conversation_model"]
            row.last_test_error = "; ".join(errors) if errors else None
            row.last_test_message = (result.content or "")[:2000]
            row.updated_at = datetime.now(timezone.utc)
            await self.db.flush()
            await self.db.refresh(row)
            set_runtime_settings_cache(_row_dict(row))

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
        }

    async def save(self, body: dict[str, Any], *, require_test_ok: bool = True) -> dict[str, Any]:
        cfg = _validate_payload(body)
        # Test first — do not save on failure
        probe = await self.test_connection(cfg)
        if require_test_ok and not probe.get("ok"):
            raise ValueError(
                "Prueba de conexión falló; no se guardaron cambios: "
                + ", ".join(probe.get("errors") or ["unknown"])
            )

        # Deactivate previous actives
        await self.db.execute(
            update(LotteryAiSettings).where(LotteryAiSettings.is_active.is_(True)).values(is_active=False)
        )
        row = LotteryAiSettings(
            id=uuid.uuid4(),
            conversation_provider=cfg["conversation_provider"],
            conversation_model=cfg["conversation_model"],
            temperature=cfg["temperature"],
            max_tokens=cfg["max_tokens"],
            timeout_seconds=cfg["timeout_seconds"],
            is_active=True,
            updated_by=self.user_id,
            last_test_at=datetime.now(timezone.utc),
            last_test_ok=True,
            last_test_latency_ms=probe.get("latency_ms"),
            last_test_model=probe.get("model"),
            last_test_error=None,
            last_test_message=(probe.get("message_received") or "")[:2000],
        )
        row.updated_at = datetime.now(timezone.utc)
        self.db.add(row)
        await self.db.flush()
        await self.db.refresh(row)
        data = _row_dict(row)
        set_runtime_settings_cache(data)
        return {"settings": data, "probe": probe}
