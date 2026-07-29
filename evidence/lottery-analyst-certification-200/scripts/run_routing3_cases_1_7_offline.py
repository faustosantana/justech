#!/usr/bin/env python3
"""Offline Conversational Routing 3.0 — mandatory cases 1–7 (no HTTP / no PROD)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "backend"))

from app.lottery.ai.active_investigation.hermes_decision_engine import HermesDecisionEngine
from app.lottery.ai.active_investigation.session import ActiveInvestigationSession
from app.lottery.ai.conversation_state import ConversationState
from app.lottery.ai.conversational_router import ConversationalRouter, detect_social_chitchat
from app.lottery.ai.investigation_workspace.materialize import materialize_same_day_table
from app.lottery.ai.investigation_workspace.store import save_asset
from app.lottery.ai.understanding import understand


def _sticky() -> tuple[ConversationState, ActiveInvestigationSession]:
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
        },
        {
            "date": "2023-06-01",
            "appearances": [
                {"number": "50", "lottery": "Quiniela Leidsa", "position": 1},
                {"number": "90", "lottery": "Gana Más", "position": 2},
            ],
        },
    ]
    save_asset(state, materialize_same_day_table(items=items, subjects=["50", "90"]))
    state.active_investigation = inv.to_store()
    return state, inv


def _check(name: str, cond: bool, detail: str = "") -> dict:
    return {"name": name, "pass": bool(cond), "detail": detail}


def case1() -> list[dict]:
    """Clean social turns — no investigation."""
    results = []
    state = ConversationState()
    for msg in ("Hola", "Todo bien, ¿y tú?"):
        u, state = understand(msg, state)
        r = ConversationalRouter.route(msg, state=state, investigation=None)
        reply = (u.params or {}).get("conversational_reply") or ""
        results.append(
            _check(
                f"C1:{msg}",
                r.path == "social_chitchat"
                and r.inherited_subjects == []
                and "Hallazgos" not in reply
                and "50" not in reply,
                f"path={r.path} reply={reply[:60]!r}",
            )
        )
    return results


def case2() -> list[dict]:
    """Contaminated session — social after sticky 50/90."""
    state, inv = _sticky()
    results = []
    # T1 research already done (sticky). T2/T3 social.
    for msg in ("Hola", "Todo bien, ¿y tú?"):
        u, state = understand(msg, state)
        r = ConversationalRouter.route(msg, state=state, investigation=inv)
        d = HermesDecisionEngine.decide(msg, state=state, investigation=inv)
        reply = (u.params or {}).get("conversational_reply") or ""
        results.append(
            _check(
                f"C2:{msg}",
                r.path == "social_chitchat"
                and d.inherited_subjects == []
                and "50" not in reply
                and "90" not in reply
                and "Hallazgos" not in reply
                and state.active_numbers == ["50", "90"],  # preserved internally
                f"path={r.path} hermes={d.turn_type} reply={reply[:50]!r}",
            )
        )
    return results


def case3() -> list[dict]:
    """Thanks social then show dates → workspace."""
    state, inv = _sticky()
    results = []
    r2 = ConversationalRouter.route("Gracias.", state=state, investigation=inv)
    results.append(_check("C3:Gracias", r2.path == "social_chitchat"))
    r3 = ConversationalRouter.route("Muéstrame las fechas.", state=state, investigation=inv)
    d3 = HermesDecisionEngine.decide("Muéstrame las fechas.", state=state, investigation=inv)
    results.append(
        _check(
            "C3:Muéstrame las fechas",
            r3.path == "workspace_action"
            and r3.workspace_action
            and r3.workspace_action.action == "show_dates"
            and d3.turn_type == "asset_action"
            and d3.requires_research is False,
            f"path={r3.path} action={getattr(r3.workspace_action,'action',None)} hermes={d3.turn_type}",
        )
    )
    return results


def case4() -> list[dict]:
    """Ops T2–T5 on same asset — no narrative research."""
    state, inv = _sticky()
    ops = [
        ("Muéstrame las fechas.", "show_dates"),
        ("Desglosa por posición.", "sort_results"),
        ("Solo Gana Más.", "filter_results"),
        ("Ordénalo desde la más reciente.", "sort_results"),
    ]
    results = []
    for msg, action in ops:
        r = ConversationalRouter.route(msg, state=state, investigation=inv)
        d = HermesDecisionEngine.decide(msg, state=state, investigation=inv)
        results.append(
            _check(
                f"C4:{msg}",
                r.path == "workspace_action"
                and r.workspace_action
                and r.workspace_action.action == action
                and d.turn_type == "asset_action"
                and d.requires_research is False,
                f"path={r.path} got={getattr(r.workspace_action,'action',None)} expect={action}",
            )
        )
    return results


def case5() -> list[dict]:
    state, inv = _sticky()
    r = ConversationalRouter.route("Ahora analiza el 35.", state=state, investigation=inv)
    d = HermesDecisionEngine.decide("Ahora analiza el 35.", state=state, investigation=inv)
    return [
        _check(
            "C5:Ahora analiza el 35",
            r.path == "explicit_new_investigation"
            and d.turn_type != "asset_action"
            and "35" in (d.inherited_subjects or []),
            f"path={r.path} hermes={d.turn_type} subjects={d.inherited_subjects}",
        )
    ]


def case6() -> list[dict]:
    state = ConversationState(
        pending_intent="last_occurrence",
        pending_slots=["lottery"],
        clarification_question="¿Qué lotería deseas consultar?",
    )
    r = ConversationalRouter.route(
        "Gana Más.", state=state, investigation=None, pending_clarification=True
    )
    return [
        _check(
            "C6:Gana Más pending",
            r.path == "analytical_clarification"
            and r.reason_code == "PENDING_CLARIFICATION_MATCH",
            f"path={r.path} reason={r.reason_code}",
        )
    ]


def case7() -> list[dict]:
    m = detect_social_chitchat("Excelente.")
    r = ConversationalRouter.route("Excelente.", state=ConversationState(), investigation=None)
    return [
        _check(
            "C7:Excelente",
            m is not None
            and r.path == "social_chitchat"
            and r.reason_code == "SOCIAL_CHITCHAT_MATCH",
            f"path={r.path} reason={r.reason_code}",
        )
    ]


def main() -> int:
    all_rows: list[dict] = []
    for fn in (case1, case2, case3, case4, case5, case6, case7):
        all_rows.extend(fn())
    passed = sum(1 for r in all_rows if r["pass"])
    failed = [r for r in all_rows if not r["pass"]]
    out = {
        "suite": "conversational_routing_3_cases_1_7",
        "passed": passed,
        "failed": len(failed),
        "total": len(all_rows),
        "status": "PASS" if not failed else "FAIL",
        "results": all_rows,
    }
    out_dir = ROOT / "evidence" / "lottery-investigation-workspace-mvp-20260728" / "routing3"
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "CASES_1_7_OFFLINE.json"
    path.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"status": out["status"], "passed": passed, "failed": len(failed), "path": str(path)}, indent=2))
    for f in failed:
        print("FAIL", f)
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
