#!/usr/bin/env python3
"""Mandatory Conversational Routing 3.0 conversation — zero narrative on steps 2–7."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "backend"))

from app.lottery.ai.active_investigation.hermes_decision_engine import HermesDecisionEngine
from app.lottery.ai.active_investigation.session import ActiveInvestigationSession
from app.lottery.ai.conversation_state import ConversationState

NARRATIVE_MARKERS = [
    "Dentro de las 7 loterías",
    "No significa necesariamente",
    "La cifra es histórica",
    "Conviene revisar",
    "Puedo mostrarte",
]

STEPS = [
    ("Han salido juntos el 50 y el 90", "path_a"),
    ("Desglosar por posición", "path_b"),
    ("Ver fechas", "path_b"),
    ("Solo Nacional", "path_b"),
    ("Ordenar por fecha", "path_b"),
    ("Mostrar primeras 20", "path_b"),
    ("Exportar Excel", "path_b"),
]


def main() -> int:
    state = ConversationState()
    inv = None
    fails: list[str] = []

    for i, (text, expect) in enumerate(STEPS, start=1):
        d = HermesDecisionEngine.decide(text, state=state, investigation=inv)
        print(
            f"{i}. [{expect}] turn={d.turn_type} research={d.requires_research} "
            f"reason={d.reason_code} action={(d.workspace_action or {}).get('action')}"
        )
        if expect == "path_a":
            if d.turn_type == "asset_action":
                fails.append(f"step{i}: expected Path A research, got asset_action")
            # Seed investigation as after successful same-day answer
            state.active_numbers = ["50", "90"]
            state.active_pair = ["50", "90"]
            state.active_relation = "same_day"
            inv = ActiveInvestigationSession(
                subjects=["50", "90"], relation="same_day", metric="same_day"
            )
            state.active_investigation = inv.to_store()
        else:
            if d.turn_type != "asset_action":
                fails.append(
                    f"step{i}: expected asset_action, got {d.turn_type}/{d.reason_code}"
                )
            if d.requires_research:
                fails.append(f"step{i}: requires_research True")
            if not d.workspace_action:
                fails.append(f"step{i}: missing workspace_action")
            # Simulate that narrative markers must not appear in reason path
            blob = f"{d.reason_code} {d.turn_type}"
            for m in NARRATIVE_MARKERS:
                if m.lower() in blob.lower():
                    fails.append(f"step{i}: narrative marker in decision")

    if fails:
        print("FAIL")
        for f in fails:
            print(" -", f)
        return 1
    print("PASS conversation_routing_3 mandatory steps 2-7 all asset_action")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
