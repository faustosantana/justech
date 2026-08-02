"""Deterministic Conversational Integrity Guard for LLM orchestrator decisions."""
from __future__ import annotations

from typing import Any

from app.lottery.ai.conversational_integrity import (
    asset_matches_current,
    explicit_subjects_override,
    normalize_subjects,
)
from app.lottery.ai.conversational_orchestrator.schema import OrchestratorDecision
from app.lottery.ai.turn_policy import extract_subject_numbers


def conversational_integrity_guard(
    decision: OrchestratorDecision,
    *,
    message: str,
    state: Any,
    active_asset: Any | None,
) -> dict[str, Any]:
    """Validate GPT/LLM orchestrator decision before acceptance.

    Returns a report with decision_rejected / reason_codes. Does not mutate inputs.
    """
    reasons: list[str] = []
    msg_subjects = normalize_subjects(extract_subject_numbers(message), limit=8)
    active_pair = normalize_subjects(
        getattr(state, "active_pair", None)
        or getattr(state, "active_numbers", None)
        or [],
        limit=8,
    )
    override = explicit_subjects_override(msg_subjects, active_pair)
    dec_subjects = normalize_subjects(decision.subjects, limit=8)

    # 1) Explicit new subjects must match exactly
    if override is not None:
        if sorted(dec_subjects[: len(override)]) != sorted(override):
            reasons.append("explicit_subjects_mismatch")
        if decision.reuse_asset:
            reasons.append("reuse_with_explicit_new_subjects")

    # 2) reuse_asset only if asset matches subjects/relation/scope
    if decision.reuse_asset:
        if active_asset is None:
            reasons.append("reuse_without_asset")
        else:
            scope = None
            if decision.lottery_scope:
                scope = "official_seven"
            if not asset_matches_current(
                active_asset,
                subjects=dec_subjects or normalize_subjects(getattr(active_asset, "subjects", None)),
                relation=decision.relation,
                scope=scope,
            ):
                # Allow match on decision subjects vs asset alone
                if not asset_matches_current(
                    active_asset,
                    subjects=dec_subjects,
                    relation=decision.relation or getattr(active_asset, "relation", None),
                ):
                    reasons.append("reuse_asset_incompatible")

    # 3) workspace_action requires compatible asset or explicit table/export act
    wa = (decision.workspace_action or "").strip().lower()
    table_acts = {
        "show_dates",
        "show_results",
        "filter_results",
        "sort_results",
        "export",
        "export_excel",
        "export_csv",
        "paginate",
        "desglosar",
        "breakdown_positions",
    }
    if wa:
        if wa not in table_acts and wa not in {"none", "null"}:
            # unknown action string — still require asset if reuse-like
            pass
        if active_asset is None and not decision.needs_clarification:
            # Boot without asset is allowed only for explicit show phrases that
            # Hermes would materialize — still reject incompatible reuse claims.
            if decision.reuse_asset:
                reasons.append("workspace_action_without_compatible_asset")
        elif active_asset is not None and dec_subjects:
            if not asset_matches_current(
                active_asset,
                subjects=dec_subjects,
                relation=decision.relation or getattr(active_asset, "relation", None),
            ):
                # Workspace on sticky asset while decision subjects differ
                if override is not None:
                    reasons.append("workspace_action_wrong_subjects")

    # 4) social_chitchat never inherits subjects
    if decision.turn_type == "social_chitchat" and dec_subjects:
        reasons.append("chitchat_inherited_subjects")

    # 5) Hard ban: narrative / factual answer fields (schema forbids extras, but
    #    reason_codes/tool_plan must not smuggle prose answers)
    for code in decision.reason_codes or []:
        if isinstance(code, str) and len(code) > 120:
            reasons.append("reason_code_looks_like_prose")
            break
    for step in decision.tool_plan or []:
        if isinstance(step, str) and (
            "respuesta" in step.lower() or "el número salió" in step.lower()
        ):
            reasons.append("tool_plan_proposes_facts")
            break

    # New investigation treated as follow-up when override present
    if override is not None and decision.turn_type in {
        "contextual_follow_up",
        "attribute_of_last_event",
        "asset_action",
        "reuse_evidence",
    }:
        reasons.append("new_subjects_treated_as_followup")

    rejected = bool(reasons)
    return {
        "decision_rejected": rejected,
        "reason_codes": reasons,
        "parsed_subjects": msg_subjects,
        "override_subjects": override,
        "decision_subjects": dec_subjects,
        "guard_pass": not rejected,
    }
