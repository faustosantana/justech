"""Experimental conversational orchestrator adapter (structured decisions only).

Vendor transport is delegated to ConversationProvider — this module never
branches on huawei/openai/claude/gemini.
"""
from __future__ import annotations

import json
import re
import time
from typing import Any

from app.lottery.ai.conversational_orchestrator.conversation_provider_factory import (
    get_conversation_provider,
)
from app.lottery.ai.conversational_orchestrator.guard import conversational_integrity_guard
from app.lottery.ai.conversational_orchestrator.schema import (
    ORCHESTRATOR_JSON_SCHEMA_HINT,
    OrchestratorDecision,
    parse_orchestrator_decision,
)
from app.lottery.ai.investigation_workspace.store import get_active_asset
from app.lottery.ai.turn_policy import extract_subject_numbers

SYSTEM_PROMPT = """Eres un ORQUESTADOR conversacional de loterías. NO eres un analista de hechos.
NO inventes fechas, conteos ni resultados. NO escribas respuestas al usuario.
Solo decides enrutamiento estructurado (JSON estricto).

Reglas:
- Si el turno trae sujetos explícitos nuevos, subjects debe coincidir exactamente y reuse_asset=false.
- reuse_asset solo si el asset activo tiene los mismos subjects/relation/scope.
- social_chitchat: subjects=[].
- workspace_action solo para show_dates|show_results|filter_results|sort_results|export|breakdown_positions o null.
- tool_plan es lista de nombres de herramientas, no prosa.
- Responde ÚNICAMENTE con un objeto JSON válido que cumpla este schema:
""" + ORCHESTRATOR_JSON_SCHEMA_HINT


def _extract_json_object(text: str) -> dict[str, Any] | None:
    raw = (text or "").strip()
    if not raw:
        return None
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
    try:
        obj = json.loads(raw)
        return obj if isinstance(obj, dict) else None
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", raw, flags=re.S)
        if not m:
            return None
        try:
            obj = json.loads(m.group(0))
            return obj if isinstance(obj, dict) else None
        except json.JSONDecodeError:
            return None


def _state_snapshot(state: Any, investigation: Any | None, asset: Any | None) -> dict[str, Any]:
    return {
        "active_numbers": list(getattr(state, "active_numbers", None) or []),
        "active_pair": list(getattr(state, "active_pair", None) or []),
        "active_relation": getattr(state, "active_relation", None),
        "pending_intent": getattr(state, "pending_intent", None),
        "investigation_subjects": list(getattr(investigation, "subjects", None) or [])
        if investigation
        else [],
        "investigation_relation": getattr(investigation, "relation", None) if investigation else None,
        "active_asset": {
            "id": getattr(asset, "asset_id", None) or getattr(asset, "id", None),
            "subjects": list(getattr(asset, "subjects", None) or []),
            "relation": getattr(asset, "relation", None),
            "scope": getattr(asset, "scope", None),
        }
        if asset
        else None,
        "parsed_message_subjects": extract_subject_numbers(
            getattr(state, "_ab_message", "") or ""
        ),
    }


class GptConversationalOrchestrator:
    """LLM orchestrator — decisions only; never factual answers."""

    @classmethod
    def decide(
        cls,
        message: str,
        *,
        state: Any,
        investigation: Any | None = None,
        timeout_sec: float = 45.0,
    ) -> dict[str, Any]:
        """Return shadow/execution payload with decision or rejection + fallback marker."""
        del timeout_sec  # reserved; provider uses its own timeout
        t0 = time.perf_counter()
        asset = get_active_asset(state) if state is not None else None
        provider, provider_meta = get_conversation_provider()
        temperature = float(provider_meta.get("temperature") or 0.0)
        max_tokens = int(provider_meta.get("max_tokens") or 700)
        out: dict[str, Any] = {
            "provider": provider_meta.get("provider") or provider.name,
            "requested_provider": provider_meta.get("requested_provider"),
            "provider_unavailable": bool(provider_meta.get("provider_unavailable")),
            "fallback": provider_meta.get("fallback"),
            "settings_source": provider_meta.get("source"),
            "model": provider_meta.get("model"),
            "schema_valid": False,
            "guard_pass": False,
            "decision_rejected": True,
            "fallback_hermes": True,
            "decision": None,
            "guard": None,
            "error": None,
            "latency_ms": 0.0,
            "usage": {},
            "raw_text": None,
        }

        user_payload = {
            "message": message,
            "state": _state_snapshot(state, investigation, asset),
            "instruction": "Return ONLY the JSON decision object. No markdown. No prose.",
        }
        messages = [
            {
                "role": "user",
                "content": json.dumps(user_payload, ensure_ascii=False),
            }
        ]
        try:
            result = provider.decide(
                system_prompt=SYSTEM_PROMPT,
                messages=messages,
                schema=ORCHESTRATOR_JSON_SCHEMA_HINT,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            out["model"] = result.model
            out["usage"] = result.usage or {}
            out["raw_text"] = (result.content or "")[:4000]
            if result.provider_unavailable:
                out["provider_unavailable"] = True
                out["error"] = result.error or "provider_unavailable"
                out["latency_ms"] = round((time.perf_counter() - t0) * 1000, 1)
                return out
            if result.error and not result.content:
                out["error"] = result.error
                out["latency_ms"] = round((time.perf_counter() - t0) * 1000, 1)
                return out
            obj = _extract_json_object(result.content or "")
            if obj is None:
                out["error"] = "json_parse_failed"
                out["latency_ms"] = round((time.perf_counter() - t0) * 1000, 1)
                return out
            decision, err = parse_orchestrator_decision(obj)
            if decision is None:
                out["error"] = err or "schema_invalid"
                out["latency_ms"] = round((time.perf_counter() - t0) * 1000, 1)
                return out
            out["schema_valid"] = True
            guard = conversational_integrity_guard(
                decision, message=message, state=state, active_asset=asset
            )
            out["guard"] = guard
            out["guard_pass"] = bool(guard.get("guard_pass"))
            out["decision_rejected"] = bool(guard.get("decision_rejected"))
            out["decision"] = decision.model_dump()
            out["fallback_hermes"] = bool(out["decision_rejected"])
            if out["decision_rejected"]:
                out["error"] = "guard_rejected:" + ",".join(guard.get("reason_codes") or [])
        except Exception as e:  # noqa: BLE001
            out["error"] = f"llm_call_failed:{type(e).__name__}:{str(e)[:180]}"
        out["latency_ms"] = round((time.perf_counter() - t0) * 1000, 1)
        return out

    @classmethod
    def to_hermes_compatible(cls, decision: OrchestratorDecision | dict[str, Any]) -> dict[str, Any]:
        """Map orchestrator decision onto HermesDecision-like fields (for gpt mode)."""
        d = decision if isinstance(decision, dict) else decision.model_dump()
        conf = float(d.get("confidence") or 0)
        conf_l = "high" if conf >= 0.8 else "medium" if conf >= 0.5 else "low"
        wa = d.get("workspace_action")
        wa_dict = None
        if wa:
            wa_dict = {
                "action": wa,
                "turn_type": "asset_action",
                "reason_code": wa,
            }
        return {
            "turn_type": d.get("turn_type") or "new_investigation",
            "inherited_subjects": list(d.get("subjects") or []),
            "inherited_relation": d.get("relation"),
            "inherited_metric": d.get("relation"),
            "requires_research": d.get("turn_type")
            in {"new_investigation", "topic_switch", "contextual_follow_up"},
            "reuse_evidence": bool(d.get("reuse_asset")),
            "confidence": conf_l,
            "reason_code": (d.get("reason_codes") or ["gpt_orchestrator"])[0],
            "ambiguous": bool(d.get("needs_clarification")),
            "workspace_action": wa_dict,
            "requested_attribute": wa if d.get("turn_type") == "asset_action" else None,
        }
