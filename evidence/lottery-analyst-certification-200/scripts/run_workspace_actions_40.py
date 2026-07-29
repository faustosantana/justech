#!/usr/bin/env python3
"""WORKSPACE_ACTIONS_40 — Investigation Workspace 1.0 action suite.

Offline speech/Hermes checks + DEV-DB execution for flow/error cases.
Does not modify cert200 bank/seed/evaluators. Does not call Huawei for asset acts.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

ROOT = Path(__file__).resolve().parents[3]
BACKEND = ROOT / "backend"
if BACKEND.exists():
    sys.path.insert(0, str(BACKEND))
elif Path("/app").exists():
    sys.path.insert(0, "/app")

from app.lottery.ai.active_investigation.hermes_decision_engine import (  # noqa: E402
    HermesDecisionEngine,
)
from app.lottery.ai.active_investigation.session import (  # noqa: E402
    TTL_SECONDS,
    ActiveInvestigationSession,
)
from app.lottery.ai.conversation_state import ConversationState  # noqa: E402
from app.lottery.ai.investigation_workspace.handler import (  # noqa: E402
    execute_workspace_action,
    resolve_export_file,
)
from app.lottery.ai.investigation_workspace.materialize import (  # noqa: E402
    materialize_same_day_table,
)
from app.lottery.ai.investigation_workspace.schemas import (  # noqa: E402
    AssetFilters,
    WorkspaceActionDecision,
)
from app.lottery.ai.investigation_workspace.speech_acts import (  # noqa: E402
    WorkspaceSpeechActDetector,
)
from app.lottery.ai.investigation_workspace.store import (  # noqa: E402
    get_active_asset,
    save_asset,
)

BANK_CANDIDATES = [
    Path(__file__).resolve().parent.parent / "WORKSPACE_ACTIONS_40.json",
    Path("/tmp/WORKSPACE_ACTIONS_40.json"),
]
BANK = next((p for p in BANK_CANDIDATES if p.exists()), BANK_CANDIDATES[0])
OUT = Path(
    os.environ.get(
        "WORKSPACE_ACTIONS_OUT",
        str(ROOT / "evidence/lottery-investigation-workspace-mvp-20260728/WORKSPACE_ACTIONS_40"),
    )
)


def _sample_items() -> list[dict]:
    return [
        {
            "date": "2024-01-15",
            "appearances": [
                {"number": "35", "lottery": "Quiniela Loteka", "position": 1},
                {"number": "14", "lottery": "Quiniela Loteka", "position": 2},
            ],
        },
        {
            "date": "2023-06-01",
            "appearances": [
                {"number": "35", "lottery": "Quiniela Leidsa", "position": 1},
                {"number": "14", "lottery": "Quiniela Real", "position": 3},
            ],
        },
        {
            "date": "2025-03-10",
            "appearances": [
                {"number": "35", "lottery": "Loteria Nacional", "position": 2},
                {"number": "14", "lottery": "Quiniela Loteka", "position": 1},
            ],
        },
        {
            "date": "2022-11-02",
            "appearances": [
                {"number": "35", "lottery": "Gana Mas", "position": 1},
                {"number": "14", "lottery": "Gana Mas", "position": 2},
            ],
        },
    ]


def _seed_state(subjects: list[str] | None = None) -> tuple[ConversationState, ActiveInvestigationSession]:
    subjects = subjects or ["35", "14"]
    st = ConversationState(
        active_numbers=list(subjects),
        active_pair=list(subjects[:2]),
        active_relation="same_day",
        active_filters={"relation": "same_day"},
    )
    inv = ActiveInvestigationSession(
        subjects=list(subjects[:2]),
        relation="same_day",
        metric="same_day",
    )
    asset = materialize_same_day_table(
        items=_sample_items(),
        subjects=subjects[:2],
        investigation_id=inv.investigation_id,
    )
    save_asset(st, asset)
    st.active_investigation = inv.to_store()
    return st, inv


def _check_speech(case: dict) -> list[str]:
    fails: list[str] = []
    exp = case.get("expect") or {}
    st, _inv = _seed_state()
    d = WorkspaceSpeechActDetector.detect(
        case["user"],
        has_active_asset=True,
        has_active_investigation=True,
    )
    if d is None:
        return [f"{case['id']}:speech_none"]
    if exp.get("action") and d.action != exp["action"]:
        fails.append(f"{case['id']}:action:{d.action}!={exp['action']}")
    if exp.get("lottery") and (d.filters.lottery or "") != exp["lottery"]:
        fails.append(f"{case['id']}:lottery:{d.filters.lottery}!={exp['lottery']}")
    if exp.get("clear") and d.reason_code != "clear_filters" and d.filters.lottery:
        fails.append(f"{case['id']}:expected_clear got lottery={d.filters.lottery}")
    if exp.get("field") and (d.sort is None or d.sort.field != exp["field"]):
        fails.append(f"{case['id']}:field")
    if exp.get("direction") and (d.sort is None or d.sort.direction != exp["direction"]):
        fails.append(f"{case['id']}:direction:{getattr(d.sort,'direction',None)}")
    if exp.get("page") is not None and (
        d.pagination is None or d.pagination.page != exp["page"]
    ):
        fails.append(f"{case['id']}:page")
    return fails


def _check_hermes(case: dict) -> list[str]:
    fails: list[str] = []
    exp = case.get("expect") or {}
    st, inv = _seed_state()
    hd = HermesDecisionEngine.decide(case["user"], state=st, investigation=inv)
    if exp.get("hermes_turn") and hd.turn_type != exp["hermes_turn"]:
        fails.append(f"{case['id']}:hermes_turn:{hd.turn_type}")
    if exp.get("requires_research") is False and hd.requires_research:
        fails.append(f"{case['id']}:requires_research_true")
    if exp.get("requires_huawei") is False:
        wa = hd.workspace_action or {}
        if wa.get("requires_huawei") is True:
            fails.append(f"{case['id']}:requires_huawei")
        if hd.reasoning_mode not in {None, "skip"}:
            # asset_action forces skip
            if hd.turn_type == "asset_action" and hd.reasoning_mode != "skip":
                fails.append(f"{case['id']}:reasoning_mode:{hd.reasoning_mode}")
    return fails


async def _exec_kind(case: dict, tmp_exports: Path) -> list[str]:
    from app.config import settings

    settings.lottery_exports_path = str(tmp_exports)
    fails: list[str] = []
    kind = case.get("kind")
    st, inv = _seed_state()
    query = SimpleNamespace(
        same_day_number_coincidences=AsyncMock(
            return_value={"items": _sample_items(), "total": len(_sample_items())}
        )
    )

    async def act(msg: str):
        d = WorkspaceSpeechActDetector.detect(
            msg, has_active_asset=True, has_active_investigation=True
        )
        assert d is not None, msg
        return await execute_workspace_action(
            st, d, query_service=query, investigation=inv, conversation_id="wa40"
        )

    if kind == "exec_flow_filter_export":
        r1 = await act("Muéstrame esos resultados")
        r2 = await act("Filtra solo Loteka")
        r3 = await act("Exporta a Excel")
        a2 = (r2.get("structured_content") or {}).get("asset") or {}
        if a2.get("row_count", 0) < 1:
            fails.append(f"{case['id']}:filter_empty")
        if (r3.get("structured_content") or {}).get("type") != "investigation_workspace_export":
            fails.append(f"{case['id']}:export_type")
        storage = (r3.get("structured_content") or {}).get("storage_name")
        path = resolve_export_file(storage or "")
        if path is None or not path.is_file():
            fails.append(f"{case['id']}:export_missing_file")
        else:
            from openpyxl import load_workbook

            wb = load_workbook(path)
            n = wb["Resultados"].max_row - 1
            if n != a2.get("row_count"):
                fails.append(f"{case['id']}:excel_rows:{n}!={a2.get('row_count')}")

    elif kind == "exec_flow_sort_export":
        await act("Muéstrame esos resultados")
        r2 = await act("Ordénalos por fecha")
        r3 = await act("Exporta a Excel")
        asset = get_active_asset(st)
        if not asset or asset.sort.field != "fecha":
            fails.append(f"{case['id']}:sort_field")
        if (r3.get("structured_content") or {}).get("type") != "investigation_workspace_export":
            fails.append(f"{case['id']}:export_type")

    elif kind == "exec_clear_filter_restores":
        await act("Muéstrame esos resultados")
        base = get_active_asset(st)
        base_n = base.row_count if base else -1
        await act("Filtra solo Loteka")
        filt = get_active_asset(st)
        if not filt or filt.row_count >= base_n:
            fails.append(f"{case['id']}:filter_did_not_reduce")
        await act("Quita el filtro")
        cleared = get_active_asset(st)
        if not cleared or cleared.row_count != base_n:
            fails.append(
                f"{case['id']}:clear_restore:{getattr(cleared,'row_count',None)}!={base_n}"
            )

    elif kind == "expired_asset_rematerializes":
        asset = get_active_asset(st)
        assert asset
        asset.expires_at = datetime.now(timezone.utc) - timedelta(seconds=5)
        asset.source_rows = []  # force rematerialize
        save_asset(st, asset)
        r = await act("Muéstrame esos resultados")
        if not (r.get("tool_payload") or {}).get("ok"):
            fails.append(f"{case['id']}:rematerialize_failed")
        anew = get_active_asset(st)
        if not anew or not anew.source_rows:
            fails.append(f"{case['id']}:no_rows_after_rematerialize")

    elif kind == "export_missing_404":
        path = resolve_export_file("ws_does_not_exist_zzzz.xlsx")
        if path is not None:
            fails.append(f"{case['id']}:expected_none")

    elif kind == "invalid_filter_zero_or_safe":
        await act("Muéstrame esos resultados")
        # Apply impossible lottery filter via decision (not speech)
        d = WorkspaceActionDecision(
            action="filter_results",
            filters=AssetFilters(lottery="Haiti Bolet"),
            reason_code="filter_lottery",
        )
        r = await execute_workspace_action(
            st, d, query_service=query, investigation=inv, conversation_id="wa40"
        )
        asset = (r.get("structured_content") or {}).get("asset") or {}
        # Safe: 0 rows, no crash, still workspace table
        if (r.get("structured_content") or {}).get("type") != "investigation_workspace_table":
            fails.append(f"{case['id']}:not_table")
        if asset.get("row_count") not in {0, None}:
            # Haiti should not match official rows
            if asset.get("row_count", 0) > 0:
                fails.append(f"{case['id']}:unexpected_rows:{asset.get('row_count')}")

    elif kind == "active_investigation_10min":
        inv2 = ActiveInvestigationSession(subjects=["35", "14"], relation="same_day")
        inv2.updated_at = datetime.now(timezone.utc)
        inv2.expires_at = inv2.updated_at + timedelta(seconds=TTL_SECONDS)
        if inv2.is_expired():
            fails.append(f"{case['id']}:should_be_active")
        # 9 minutes later still active
        inv2.updated_at = datetime.now(timezone.utc) - timedelta(minutes=9)
        inv2.expires_at = inv2.updated_at + timedelta(seconds=TTL_SECONDS)
        if inv2.is_expired():
            fails.append(f"{case['id']}:expired_at_9min")

    elif kind == "two_investigations_switch":
        st1, inv1 = _seed_state(["35", "14"])
        a1 = get_active_asset(st1)
        st2, inv2 = _seed_state(["22", "38"])
        a2 = get_active_asset(st2)
        if not a1 or not a2:
            fails.append(f"{case['id']}:missing_assets")
        elif a1.asset_id == a2.asset_id:
            fails.append(f"{case['id']}:same_asset_id")
        elif a1.subjects == a2.subjects:
            fails.append(f"{case['id']}:subjects_not_switched")
        # return to previous: restore st1 asset
        save_asset(st2, a1)
        back = get_active_asset(st2)
        if not back or back.subjects != ["35", "14"]:
            fails.append(f"{case['id']}:return_previous_failed")

    else:
        fails.append(f"{case['id']}:unknown_kind:{kind}")
    return fails


async def main() -> int:
    bank = json.loads(BANK.read_text(encoding="utf-8"))
    cases = bank["cases"]
    assert len(cases) == 40, f"expected 40 cases, got {len(cases)}"
    OUT.mkdir(parents=True, exist_ok=True)
    results = []
    pass_n = fail_n = 0
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        for case in cases:
            cid = case["id"]
            fails: list[str] = []
            try:
                if case.get("kind"):
                    fails = await _exec_kind(case, tmp)
                elif "hermes_turn" in (case.get("expect") or {}) or case.get("group") == "hermes":
                    fails = _check_hermes(case)
                else:
                    fails = _check_speech(case)
            except Exception as exc:  # noqa: BLE001
                fails = [f"{cid}:exception:{type(exc).__name__}:{exc}"]
            ok = not fails
            if ok:
                pass_n += 1
            else:
                fail_n += 1
            results.append({"id": cid, "pass": ok, "fails": fails, "group": case.get("group")})
            print(f"{'PASS' if ok else 'FAIL'} {cid} {fails or ''}")

    summary = {
        "suite": "WORKSPACE_ACTIONS_40",
        "pass": pass_n,
        "fail": fail_n,
        "total": len(cases),
        "finished_at": datetime.now(timezone.utc).isoformat(),
        "results": results,
    }
    (OUT / "SUMMARY.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    (OUT / "raw_results.json").write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({"pass": pass_n, "fail": fail_n, "total": len(cases)}, indent=2))
    return 0 if fail_n == 0 else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
