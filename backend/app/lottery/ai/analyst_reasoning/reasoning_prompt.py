"""Analyst Reasoning prompt — SEPARATE from Prompt Maestro (v6).

Prompt Runtime Integration 1.0: system content may come from Prompt Studio
when feature flags allow; default remains Analyst Reasoning 2.1 legacy text.
Does not replace or edit lottery_analyst_system_v6.
"""

from __future__ import annotations

import json
from typing import Any, Callable

from app.lottery.ai.analyst_reasoning.evidence_package import EvidencePackage
from app.lottery.ai.analyst_reasoning.reasoning_modes import MODE_INSTRUCTIONS, ReasoningMode
from app.lottery.ai.prompt_runtime.selector import PromptRuntimeSelection, PromptRuntimeSelector

REASONING_PROMPT_VERSION = "analyst-reasoning-v1.1"


def build_reasoning_messages(
    *,
    package: EvidencePackage,
    mode: ReasoningMode,
    conversation_id: str | None = None,
    load_studio: Callable[[], dict[str, Any] | None] | None = None,
) -> list[dict[str, str]]:
    mode_help = MODE_INSTRUCTIONS.get(mode, MODE_INSTRUCTIONS["explain_evidence"])
    selection = PromptRuntimeSelector.select(
        mode_label=str(mode),
        mode_help=mode_help,
        reasoning_prompt_version=REASONING_PROMPT_VERSION,
        conversation_id=conversation_id,
        load_studio=load_studio,
    )
    _emit_runtime_trace(selection)

    user = {
        "task": "Produce la respuesta analítica para el usuario.",
        "mode": mode,
        "evidence_package": package.to_llm_payload(),
    }
    messages = [
        {"role": "system", "content": selection.system_prompt},
        {
            "role": "user",
            "content": json.dumps(user, ensure_ascii=False, indent=2, default=str),
        },
    ]
    # Attach selection for callers that inspect message metadata (not sent to Huawei)
    messages[0]["_prompt_runtime"] = selection.to_trace_dict()  # type: ignore[typeddict-item]
    return messages


def select_reasoning_prompt(
    *,
    mode: ReasoningMode,
    conversation_id: str | None = None,
    load_studio: Callable[[], dict[str, Any] | None] | None = None,
) -> PromptRuntimeSelection:
    mode_help = MODE_INSTRUCTIONS.get(mode, MODE_INSTRUCTIONS["explain_evidence"])
    return PromptRuntimeSelector.select(
        mode_label=str(mode),
        mode_help=mode_help,
        reasoning_prompt_version=REASONING_PROMPT_VERSION,
        conversation_id=conversation_id,
        load_studio=load_studio,
    )


def _emit_runtime_trace(selection: PromptRuntimeSelection) -> None:
    try:
        from app.lottery.ai.forensics import ForensicTraceService, get_correlation_id

        tr = ForensicTraceService(get_correlation_id())
        if not tr.enabled:
            return
        extra = selection.to_trace_dict()
        tr.event(
            "prompt.runtime.selected",
            component="prompt_runtime",
            file="reasoning_prompt.py",
            function="build_reasoning_messages",
            extra=extra,
        )
        if selection.fallback_used:
            tr.event(
                "prompt.runtime.fallback",
                component="prompt_runtime",
                file="selector.py",
                function="select",
                extra=extra,
            )
        if selection.source == "studio":
            tr.event(
                "prompt.studio.loaded",
                component="prompt_runtime",
                file="selector.py",
                function="_load_studio_compiled",
                extra={
                    "prompt_version_id": selection.prompt_version_id,
                    "compiled_prompt_hash": selection.compiled_prompt_hash,
                },
            )
    except Exception:  # noqa: BLE001
        return
