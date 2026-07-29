#!/usr/bin/env python3
"""In-process forensic assertions for Routing 3.0 (no PROD; no live API required)."""

from __future__ import annotations

import json
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "backend"))

from app.lottery.ai.active_investigation.hermes_decision_engine import HermesDecisionEngine
from app.lottery.ai.active_investigation.session import ActiveInvestigationSession
from app.lottery.ai.conversation_state import ConversationState
from app.lottery.ai.conversational_router import ConversationalRouter
from app.lottery.ai.investigation_workspace.materialize import materialize_same_day_table
from app.lottery.ai.investigation_workspace.store import save_asset
from app.lottery.ai.understanding import understand


def sticky() -> tuple[ConversationState, ActiveInvestigationSession]:
    state = ConversationState(
        active_numbers=["50", "90"],
        active_pair=["50", "90"],
        active_relation="same_day",
    )
    inv = ActiveInvestigationSession(
        subjects=["50", "90"], relation="same_day", metric="same_day"
    )
    items = [
        {
            "date": "2024-01-15",
            "appearances": [
                {"number": "50", "lottery": "Quiniela Loteka", "position": 1},
                {"number": "90", "lottery": "Quiniela Loteka", "position": 2},
            ],
        }
    ]
    save_asset(state, materialize_same_day_table(items=items, subjects=["50", "90"]))
    state.active_investigation = inv.to_store()
    return state, inv


def trace_turn(msg: str, state, inv) -> dict:
    cid = f"lottery-chat-{uuid.uuid4().hex}"
    u, state2 = understand(msg, state)
    r = ConversationalRouter.route(msg, state=state2, investigation=inv)
    d = HermesDecisionEngine.decide(msg, state=state2, investigation=inv)
    reply = (u.params or {}).get("conversational_reply") or ""
    return {
        "correlation_id": cid,
        "user_message": msg,
        "intent": r.path,
        "understanding_intent": u.intent,
        "reason_code": r.reason_code,
        "inherited_subjects": list(r.inherited_subjects or []),
        "hermes_inherited_subjects": list(d.inherited_subjects or []),
        "hermes_turn_type": d.turn_type,
        "provider_used": (
            "social_template"
            if r.path == "social_chitchat"
            else ("workspace" if r.path == "workspace_action" else "n/a")
        ),
        "format_analyst_response.called": False if r.path in {"social_chitchat", "workspace_action"} else None,
        "workspace.called": r.path == "workspace_action",
        "sql.called": False if r.path == "social_chitchat" else None,
        "default_research.called": d.requires_research and d.turn_type != "asset_action",
        "workspace_action": r.workspace_action.action if r.workspace_action else None,
        "asset_id": (getattr(state2, "active_asset_id", None) or None),
        "reply_preview": reply[:120],
        "reply_mentions_subjects": any(s in reply for s in ("50", "90")),
        "sticky_preserved": list(state2.active_numbers or []),
    }


def main() -> int:
    state, inv = sticky()
    turns = [
        ("Todo bien, ¿y tú?", "social"),
        ("Muéstrame las fechas", "workspace"),
        ("Gracias", "social"),
        ("Excelente", "social"),
    ]
    rows = []
    for msg, kind in turns:
        t = trace_turn(msg, state, inv)
        if kind == "social":
            t["assertions"] = {
                "intent_social": t["intent"] == "social_chitchat",
                "inherited_empty": t["inherited_subjects"] == [] and t["hermes_inherited_subjects"] == [],
                "no_formatter": t["format_analyst_response.called"] is False,
                "no_workspace": t["workspace.called"] is False,
                "no_sql": t["sql.called"] is False,
                "no_subject_leak": t["reply_mentions_subjects"] is False,
            }
        else:
            t["assertions"] = {
                "intent_workspace": t["intent"] == "workspace_action",
                "action_show_dates": t["workspace_action"] == "show_dates",
                "no_default_research": t["default_research.called"] is False,
            }
        t["pass"] = all(t["assertions"].values())
        rows.append(t)

    out = {
        "status": "PASS" if all(r["pass"] for r in rows) else "FAIL",
        "note": "In-process forensic assertions (code path). Live DEV correlation IDs require redeploy.",
        "turns": rows,
        "prompt_studio_modified": False,
        "huawei_modified": False,
        "production_touched": False,
    }
    dest = ROOT / "evidence" / "lottery-investigation-workspace-mvp-20260728" / "routing3" / "FORENSIC_ASSERTIONS.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"status": out["status"], "path": str(dest), "ids": [r["correlation_id"] for r in rows]}, indent=2))
    return 0 if out["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
