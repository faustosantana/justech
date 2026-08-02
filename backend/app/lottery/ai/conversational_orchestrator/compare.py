"""Hermes vs GPT orchestrator comparison metrics."""
from __future__ import annotations

from typing import Any

from app.lottery.ai.conversational_integrity import normalize_subjects


def _wa(hermes: Any) -> str | None:
    if hermes is None:
        return None
    if isinstance(hermes, dict):
        wa = hermes.get("workspace_action")
    else:
        wa = getattr(hermes, "workspace_action", None)
    if isinstance(wa, dict):
        return wa.get("action")
    return wa


def _subjects_h(hermes: Any) -> list[str]:
    if hermes is None:
        return []
    if isinstance(hermes, dict):
        return normalize_subjects(hermes.get("inherited_subjects"))
    return normalize_subjects(getattr(hermes, "inherited_subjects", None))


def _turn(hermes: Any) -> str | None:
    if hermes is None:
        return None
    if isinstance(hermes, dict):
        return hermes.get("turn_type")
    return getattr(hermes, "turn_type", None)


def compare_orchestrators(
    *,
    hermes: Any,
    gpt_payload: dict[str, Any],
    hard_fail_if_gpt_prose: bool = True,
) -> dict[str, Any]:
    gpt_dec = gpt_payload.get("decision") or {}
    h_subj = _subjects_h(hermes)
    g_subj = normalize_subjects(gpt_dec.get("subjects"))
    h_turn = _turn(hermes)
    g_turn = gpt_dec.get("turn_type")
    h_wa = _wa(hermes)
    g_wa = gpt_dec.get("workspace_action")
    h_rel = (
        hermes.get("inherited_relation")
        if isinstance(hermes, dict)
        else getattr(hermes, "inherited_relation", None)
    )
    g_rel = gpt_dec.get("relation")
    h_reuse = bool(
        hermes.get("reuse_evidence")
        if isinstance(hermes, dict)
        else getattr(hermes, "reuse_evidence", False)
    ) or (h_turn == "asset_action")
    g_reuse = bool(gpt_dec.get("reuse_asset"))

    subject_match = sorted(h_subj) == sorted(g_subj)
    turn_match = h_turn == g_turn
    relation_match = (h_rel or None) == (g_rel or None) or (
        (h_rel in (None, "same_day")) and (g_rel in (None, "same_day")) and h_turn == g_turn
    )
    reuse_match = h_reuse == g_reuse
    wa_match = (h_wa or None) == (g_wa or None)

    hard_fails: list[str] = []
    if gpt_payload.get("schema_valid") is False:
        hard_fails.append("schema_invalid")
    if gpt_payload.get("guard_pass") is False and gpt_payload.get("decision") is not None:
        hard_fails.append("guard_failed")
    if gpt_payload.get("error") == "llm_credentials_missing":
        hard_fails.append("llm_unavailable")
    if gpt_dec and not subject_match and g_subj:
        # GPT subjects wrong vs Hermes when Hermes has subjects OR override case
        if h_subj and sorted(g_subj) != sorted(h_subj):
            hard_fails.append("subjects_disagree")
    raw = gpt_payload.get("raw_text") or ""
    if hard_fail_if_gpt_prose and gpt_payload.get("schema_valid") and len(raw) > 800:
        # overly long raw may indicate narrative
        if "coincide" in raw.lower() and "fecha" in raw.lower() and "{" not in raw[:20]:
            hard_fails.append("gpt_proposes_narrative")

    scores = {
        "subject_accuracy": 1.0 if subject_match else 0.0,
        "routing_accuracy": 1.0 if turn_match else 0.0,
        "asset_integrity": 1.0
        if (reuse_match and (not g_reuse or gpt_payload.get("guard_pass")))
        else 0.0,
        "scope_accuracy": 1.0 if relation_match else 0.5,
        "clarification_correctness": 1.0
        if bool(gpt_dec.get("needs_clarification"))
        == bool(
            hermes.get("ambiguous")
            if isinstance(hermes, dict)
            else getattr(hermes, "ambiguous", False)
        )
        else 0.0,
        "deterministic_guard_pass": 1.0 if gpt_payload.get("guard_pass") else 0.0,
        "schema_validity": 1.0 if gpt_payload.get("schema_valid") else 0.0,
        "context_continuity": 1.0 if (turn_match or subject_match) else 0.0,
        "workspace_action_match": 1.0 if wa_match else 0.0,
    }
    gpt_better_or_equal = (
        scores["subject_accuracy"] >= 1.0
        and scores["schema_validity"] >= 1.0
        and scores["deterministic_guard_pass"] >= 1.0
        and not hard_fails
    )
    return {
        "hermes": {
            "turn_type": h_turn,
            "subjects": h_subj,
            "relation": h_rel,
            "reuse_asset": h_reuse,
            "workspace_action": h_wa,
            "reason_code": hermes.get("reason_code")
            if isinstance(hermes, dict)
            else getattr(hermes, "reason_code", None),
        },
        "gpt": {
            "turn_type": g_turn,
            "subjects": g_subj,
            "relation": g_rel,
            "reuse_asset": g_reuse,
            "workspace_action": g_wa,
            "reason_codes": gpt_dec.get("reason_codes"),
            "provider": gpt_payload.get("provider"),
            "model": gpt_payload.get("model"),
            "latency_ms": gpt_payload.get("latency_ms"),
            "usage": gpt_payload.get("usage"),
            "schema_valid": gpt_payload.get("schema_valid"),
            "guard_pass": gpt_payload.get("guard_pass"),
            "decision_rejected": gpt_payload.get("decision_rejected"),
            "error": gpt_payload.get("error"),
        },
        "scores": scores,
        "hard_fails": hard_fails,
        "hard_fail": bool(hard_fails),
        "gpt_better_or_equal": gpt_better_or_equal,
        "agreement": {
            "subjects": subject_match,
            "turn_type": turn_match,
            "relation": relation_match,
            "reuse": reuse_match,
            "workspace_action": wa_match,
        },
    }
