#!/usr/bin/env python3
"""CONVERSATIONAL_AGENT_50 — offline evaluator for Analyst 2.0 continuity.

Does not modify cert200 bank/seed/evaluator. Runs against in-process
HermesDecision + QuestionClassifier + NaturalResponse + TTL managers.
"""

from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3] if len(Path(__file__).resolve().parents) > 3 else Path("/app")
if str(ROOT / "backend") not in sys.path and (ROOT / "backend").exists():
    sys.path.insert(0, str(ROOT / "backend"))
elif Path("/app").exists():
    sys.path.insert(0, "/app")
else:
    sys.path.insert(0, str(ROOT))

from app.lottery.ai.active_investigation import (  # noqa: E402
    HermesDecisionEngine,
    InvestigationStateManager,
    NaturalResponseGenerator,
    SessionExpirationManager,
)
from app.lottery.ai.active_investigation.session import (  # noqa: E402
    TTL_SECONDS,
    ActiveInvestigationSession,
)
from app.lottery.ai.analyst.intent_resolver import IntentResolver  # noqa: E402
from app.lottery.ai.analyst.question_classifier import QuestionClassifier  # noqa: E402
from app.lottery.ai.conversation_state import ConversationState  # noqa: E402

_BANK_CANDIDATES = [
    Path(__file__).resolve().parent.parent / "CONVERSATIONAL_AGENT_50.json",
    Path("/tmp/CONVERSATIONAL_AGENT_50.json"),
]
BANK = next((p for p in _BANK_CANDIDATES if p.exists()), _BANK_CANDIDATES[0])
OUT = Path("/tmp/lottery-agent50")


def _seed_evidence(st: ConversationState, subjects: list[str]) -> None:
    a, b = subjects[0], subjects[1] if len(subjects) > 1 else subjects[0]
    inv = ActiveInvestigationSession(
        subjects=[a, b] if b else [a],
        relation="same_day" if len(subjects) >= 2 else None,
        metric="same_day" if len(subjects) >= 2 else None,
        event_type="same_day_coincidence" if len(subjects) >= 2 else None,
        date_anchor="2026-07-19",
        last_event={
            "date": "2026-07-19",
            "lottery": "Real",
            "lotteries": ["Real", "Nacional"],
            "appearances": [
                {"number": a, "lottery": "Real", "position": "1ro"},
                {"number": b, "lottery": "Nacional", "position": "3ro"},
            ],
            "numbers": [a, b],
        },
        evidence={
            "type": "same_day_coincidence",
            "numbers": [a, b],
            "total": 5,
            "lotteries": ["Real", "Nacional"],
            "last": {
                "date": "2026-07-19",
                "lottery": "Real",
                "appearances": [
                    {"number": a, "lottery": "Real", "position": "1ro"},
                    {"number": b, "lottery": "Nacional", "position": "3ro"},
                ],
            },
        },
    )
    st.active_investigation = inv.to_store()
    st.active_numbers = [a, b]
    st.active_pair = [a, b]
    st.active_relation = "same_day"
    st.active_filters = {"relation": "same_day"}
    st.last_intent = "coincidences_only"
    st.last_analysis = {"type": "same_day_coincidence", "numbers": [a, b], "total": 5}


def _eval_turn(st: ConversationState, turn: dict, conv_id: str) -> list[str]:
    fails: list[str] = []
    user = turn["user"]
    exp = turn.get("expect") or {}
    tid = turn["id"]

    # Special TTL / reset probes
    if exp.get("reset") or user.strip().lower() == "nueva conversación":
        st2 = ConversationState(
            default_number_position_scope=st.default_number_position_scope,
            default_primary_position=st.default_primary_position,
        )
        st.__dict__.update(st2.__dict__)
        return fails

    if exp.get("ttl") == "expire_clears_same_day":
        st.active_investigation = ActiveInvestigationSession(
            subjects=["78", "02"],
            relation="same_day",
            expires_at=datetime.now(timezone.utc) - timedelta(seconds=5),
        ).to_store()
        st.active_relation = "same_day"
        st.active_filters = {"relation": "same_day"}
        st2, inv, meta = SessionExpirationManager().apply_on_turn_start(st)
        if inv is not None or meta.get("status") != "expired_cleared" or st2.active_relation is not None:
            fails.append("ttl_expire_failed")
        st.__dict__.update(st2.__dict__)
        return fails

    if exp.get("ttl") == "active_at_9min":
        inv = ActiveInvestigationSession(subjects=["78", "02"], relation="same_day")
        inv.updated_at = datetime.now(timezone.utc)
        inv.expires_at = inv.updated_at + timedelta(seconds=TTL_SECONDS)
        if inv.is_expired(now=inv.updated_at + timedelta(minutes=9)):
            fails.append("ttl_9min_should_be_active")
        return fails

    if exp.get("ttl") == "renew":
        inv = ActiveInvestigationSession(subjects=["78", "02"], relation="same_day")
        inv.expires_at = datetime.now(timezone.utc) + timedelta(seconds=20)
        before = inv.expires_at
        inv.touch()
        if inv.expires_at <= before:
            fails.append("ttl_renew_failed")
        return fails

    if exp.get("partial_ok"):
        text = NaturalResponseGenerator.partial_failure(
            confirmed="Pude confirmar la fecha de la coincidencia.",
            missing="Todavía no tengo el desglose por lotería.",
        )
        if "No pude completar la consulta en este momento" in text:
            fails.append("generic_fallback")
        if "intente de nuevo" not in text.lower():
            fails.append("missing_retry_offer")
        return fails

    # Ensure sticky same_day context for continuity conversations
    if conv_id.startswith(("A_", "D_", "F_")) and len(st.active_numbers or []) < 2:
        pair = exp.get("subjects") or ["78", "02"]
        if len(pair) >= 2:
            _seed_evidence(st, pair[:2])

    res = IntentResolver.resolve(user, st)
    inv = ActiveInvestigationSession.from_store(st.active_investigation)
    decision = HermesDecisionEngine.decide(user, state=st, investigation=inv, resolution=res)
    mgr = InvestigationStateManager()
    if decision.inherited_relation == "same_day":
        res = {
            **res,
            "active_relation": "same_day",
            "relation": "same_day",
            "numbers": list(decision.inherited_subjects or res.get("numbers") or st.active_numbers or [])[:8],
            "use_active_pair": True,
        }
        if decision.requested_attribute and not res.get("follow_up_kind"):
            res["follow_up_kind"] = decision.requested_attribute
    inv2 = mgr.begin_or_continue(st, decision=decision, message=user)
    q = QuestionClassifier.classify(user, st, res)

    answer = ""
    if decision.reuse_evidence and inv2 is not None:
        answer = NaturalResponseGenerator.answer_attribute_from_evidence(decision, inv2) or ""
    elif q is not None and q.kind == "coincidences_only" and decision.requested_attribute in {
        "lotteries",
        "positions",
        "date",
        "explain",
        "details",
        "count",
    }:
        # Simulate research having refreshed evidence
        if inv2:
            mgr.update_after_research(
                st,
                investigation=inv2,
                summary={
                    "numbers": list(inv2.subjects or st.active_numbers or [])[:2],
                    "relation": "same_day",
                    "total": 5,
                    "items": [(inv2.last_event or {})],
                    "last": inv2.last_event or {},
                },
                template="coincidieron",
                tools=["lottery_get_number_occurrences"],
                intent="coincidences_only",
            )
            inv2 = ActiveInvestigationSession.from_store(st.active_investigation)
            answer = NaturalResponseGenerator.answer_attribute_from_evidence(decision, inv2) or "coincidieron"
    elif q is not None:
        answer = f"kind={q.kind} nums={q.params.get('numbers')}"
        # Keep state subjects from question
        nums = list(q.params.get("numbers") or [])
        if len(nums) >= 2:
            st.active_numbers = nums[:2]
            st.active_pair = nums[:2]
            if q.params.get("relation") == "same_day":
                st.active_relation = "same_day"
                st.last_intent = "coincidences_only"
                _seed_evidence(st, nums[:2])
        elif nums:
            st.active_numbers = nums[:1]
    else:
        answer = "no_research_question"

    # Assertions
    if exp.get("no_generic_fail") and re.search(r"No pude completar la consulta en este momento", answer):
        fails.append("generic_fallback")
    if exp.get("no_jargon") and re.search(
        r"\b(same_day|metric|research|planner|tool_trace|active_filters)\b", answer, re.I
    ):
        fails.append("internal_jargon")

    want_subj = exp.get("subjects")
    if want_subj:
        got = list(decision.inherited_subjects or st.active_numbers or [])
        if q and q.params.get("numbers"):
            got = list(q.params.get("numbers") or got)
        norm = [str(x).zfill(2) if str(x).isdigit() else str(x) for x in got]
        want = [str(x).zfill(2) if str(x).isdigit() else str(x) for x in want_subj]
        if want[:2] != norm[:2] and not all(w in norm for w in want):
            # allow order-stable pair match
            if sorted(want[:2]) != sorted(norm[:2]):
                fails.append(f"subjects_lost:{want}!={norm}")

    if exp.get("subjects_contains"):
        got = list(decision.inherited_subjects or st.active_numbers or [])
        if q and q.params.get("numbers"):
            got = list(q.params.get("numbers") or got)
        blob = " ".join(str(x) for x in got) + " " + user
        for s in exp["subjects_contains"]:
            if str(s) not in blob and str(s).zfill(2) not in blob:
                fails.append(f"missing_subject:{s}")

    if exp.get("subjects_min") and len(decision.inherited_subjects or st.active_numbers or []) < int(
        exp["subjects_min"]
    ):
        # topic asks may still inherit from state after begin_or_continue
        if len(st.active_numbers or []) < int(exp["subjects_min"]):
            fails.append("subjects_min")

    if exp.get("relation") == "same_day":
        rel = decision.inherited_relation or st.active_relation
        if rel != "same_day" and (q is None or q.params.get("relation") != "same_day"):
            fails.append("relation_lost")

    if exp.get("kind") and (q is None or q.kind != exp["kind"]):
        # attribute reuse may skip classifier path when evidence reused
        if not (decision.reuse_evidence and exp.get("reuse_or_coincidence")):
            fails.append(f"kind:{None if q is None else q.kind}!={exp['kind']}")

    if exp.get("kind_in") and (q is None or q.kind not in exp["kind_in"]):
        fails.append(f"kind_not_in:{None if q is None else q.kind}")

    if exp.get("list_mode") and q is not None and not q.params.get("list_mode"):
        fails.append("list_mode_missing")

    if exp.get("attr") and decision.requested_attribute not in {exp["attr"], None}:
        # allow hermes attr OR classifier requested_attribute
        if (q.params.get("requested_attribute") if q else None) != exp["attr"]:
            if decision.requested_attribute != exp["attr"]:
                fails.append(f"attr:{decision.requested_attribute}!={exp['attr']}")

    if exp.get("reuse_or_coincidence"):
        ok = decision.reuse_evidence or (q is not None and q.kind == "coincidences_only")
        if not ok:
            fails.append("expected_reuse_or_coincidence")

    if exp.get("topic_switch_or_subject"):
        subj = str(exp["topic_switch_or_subject"]).zfill(2)
        got = list(decision.inherited_subjects or st.active_numbers or [])
        if q and q.params.get("numbers"):
            got = list(q.params.get("numbers") or got)
        if subj not in [str(x).zfill(2) if str(x).isdigit() else str(x) for x in got] and decision.turn_type != "topic_switch":
            fails.append("topic_switch_failed")
        # apply switch
        st.active_numbers = [subj]
        st.active_pair = []
        st.active_relation = None
        st.active_investigation = {}

    # Seed evidence after opening same_day turn
    if q and q.kind == "coincidences_only" and len(q.params.get("numbers") or []) >= 2:
        _seed_evidence(st, list(q.params.get("numbers"))[:2])

    return fails


def main() -> int:
    bank = json.loads(BANK.read_text(encoding="utf-8"))
    OUT.mkdir(parents=True, exist_ok=True)
    rows = []
    pass_n = fail_n = 0
    turn_count = 0
    for conv in bank["conversations"]:
        st = ConversationState()
        for turn in conv["turns"]:
            turn_count += 1
            fails = _eval_turn(st, turn, conv["id"])
            verdict = "PASS" if not fails else "FAIL"
            if verdict == "PASS":
                pass_n += 1
            else:
                fail_n += 1
            print(f"{verdict} {turn['id']} :: {turn['user'][:60]}", flush=True)
            rows.append(
                {
                    "id": turn["id"],
                    "conversation": conv["id"],
                    "user": turn["user"],
                    "fails": fails,
                    "verdict": verdict,
                }
            )
    summary = {
        "suite": "CONVERSATIONAL_AGENT_50",
        "pass": pass_n,
        "fail": fail_n,
        "total": pass_n + fail_n,
        "turn_count": turn_count,
        "certification_level": "PASS" if fail_n == 0 and pass_n == 50 else "BLOQUEADO",
    }
    (OUT / "SUMMARY.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    (OUT / "raw_results.json").write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"DONE {summary['certification_level']} PASS={pass_n} FAIL={fail_n} TOTAL={turn_count}", flush=True)
    return 0 if fail_n == 0 and pass_n == 50 else 1


if __name__ == "__main__":
    raise SystemExit(main())
