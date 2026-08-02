"""Shadow / mode wiring for conversational orchestrator A/B."""
from __future__ import annotations

from typing import Any

from app.config import settings
from app.lottery.ai.conversational_orchestrator.compare import compare_orchestrators
from app.lottery.ai.conversational_orchestrator.gpt_adapter import GptConversationalOrchestrator


def orchestrator_mode() -> str:
    mode = (getattr(settings, "lottery_conversational_orchestrator_mode", None) or "hermes").strip().lower()
    if mode not in {"hermes", "gpt_shadow", "gpt"}:
        return "hermes"
    return mode


def run_gpt_shadow(
    message: str,
    *,
    state: Any,
    investigation: Any | None,
    hermes_decision: Any,
) -> dict[str, Any]:
    """Call GPT orchestrator in parallel; never affects user-facing Hermes path."""
    gpt_payload = GptConversationalOrchestrator.decide(
        message, state=state, investigation=investigation
    )
    comparison = compare_orchestrators(hermes=hermes_decision, gpt_payload=gpt_payload)
    return {
        "mode": "gpt_shadow",
        "hermes_visible": True,
        "gpt_affects_user": False,
        "gpt": gpt_payload,
        "comparison": comparison,
    }


def maybe_apply_gpt_decision(
    message: str,
    *,
    state: Any,
    investigation: Any | None,
    hermes_decision: Any,
) -> tuple[Any, dict[str, Any]]:
    """Return (effective_hermes_decision, telemetry).

    - hermes: Hermes only
    - gpt_shadow: Hermes executed; GPT compared in telemetry
    - gpt: accept GPT if schema+guard pass; else fallback Hermes
    """
    mode = orchestrator_mode()
    telemetry: dict[str, Any] = {
        "orchestrator_mode": mode,
        "hermes_visible": True,
        "gpt_affects_user": False,
    }
    if mode == "hermes":
        return hermes_decision, telemetry

    shadow = run_gpt_shadow(
        message, state=state, investigation=investigation, hermes_decision=hermes_decision
    )
    telemetry.update(shadow)

    if mode == "gpt_shadow":
        # Hermes remains the executed decision
        telemetry["executed_by"] = "hermes"
        return hermes_decision, telemetry

    # mode == gpt — experimental; still DEV-only via flag
    gpt_payload = shadow.get("gpt") or {}
    if (
        gpt_payload.get("schema_valid")
        and gpt_payload.get("guard_pass")
        and gpt_payload.get("decision")
    ):
        mapped = GptConversationalOrchestrator.to_hermes_compatible(gpt_payload["decision"])
        # Patch HermesDecision fields in-place copy
        try:
            patched = hermes_decision.model_copy(update={
                "turn_type": mapped["turn_type"],
                "inherited_subjects": mapped["inherited_subjects"],
                "inherited_relation": mapped["inherited_relation"],
                "inherited_metric": mapped["inherited_metric"],
                "requires_research": mapped["requires_research"],
                "reuse_evidence": mapped["reuse_evidence"],
                "confidence": mapped["confidence"],
                "reason_code": mapped["reason_code"],
                "ambiguous": mapped["ambiguous"],
                "workspace_action": mapped["workspace_action"],
                "requested_attribute": mapped["requested_attribute"],
            })
            telemetry["gpt_affects_user"] = True
            telemetry["executed_by"] = "gpt"
            telemetry["fallback_hermes"] = False
            return patched, telemetry
        except Exception as e:  # noqa: BLE001
            telemetry["gpt_apply_error"] = str(e)[:200]
    telemetry["executed_by"] = "hermes"
    telemetry["fallback_hermes"] = True
    telemetry["gpt_affects_user"] = False
    return hermes_decision, telemetry
