"""EvidenceAggregator — normalize tool payloads into investigation evidence."""

from __future__ import annotations

from typing import Any


class EvidenceAggregator:
    @staticmethod
    def from_same_day_summary(summary: dict[str, Any] | None) -> dict[str, Any]:
        s = summary or {}
        items = list(s.get("items") or s.get("dates") or [])
        last = s.get("last") if isinstance(s.get("last"), dict) else (items[0] if items else {})
        if not isinstance(last, dict):
            last = {}
        appearances = list(last.get("appearances") or last.get("entries") or [])
        # Drop any leftover out-of-scope lottery rows (pre-hotfix / global pollution)
        from app.lottery.ai.official_lottery_scope import is_official_lottery

        appearances = [
            e
            for e in appearances
            if isinstance(e, dict)
            and (not e.get("lottery") or is_official_lottery(str(e.get("lottery"))))
        ]
        lotteries: list[str] = []
        positions: list[str] = []
        for e in appearances:
            if not isinstance(e, dict):
                continue
            lot = e.get("lottery") or last.get("lottery")
            if lot and is_official_lottery(str(lot)) and str(lot) not in lotteries:
                lotteries.append(str(lot))
            pos = e.get("position_label") or e.get("position")
            if pos is not None and str(pos) not in positions:
                positions.append(str(pos))
        if last.get("lottery") and is_official_lottery(str(last["lottery"])) and str(last["lottery"]) not in lotteries:
            lotteries.insert(0, str(last["lottery"]))
        return {
            "type": "same_day_coincidence",
            "numbers": list(s.get("numbers") or [])[:8],
            "total": s.get("total"),
            "items": items[:20],
            "last": last,
            "lotteries": lotteries,
            "positions": positions,
            "summary_text": None,
            "official_scope": True,
        }

    @staticmethod
    def build_last_event(evidence: dict[str, Any]) -> dict[str, Any]:
        last = dict(evidence.get("last") or {})
        if not last and evidence.get("items"):
            first = evidence["items"][0]
            if isinstance(first, dict):
                last = dict(first)
        appearances = list(last.get("appearances") or last.get("entries") or [])
        return {
            "date": str(last.get("date") or last.get("draw_date") or "")[:10] or None,
            "lottery": last.get("lottery"),
            "lotteries": list(evidence.get("lotteries") or []),
            "appearances": appearances,
            "positions": list(evidence.get("positions") or []),
            "numbers": list(evidence.get("numbers") or []),
        }

    @staticmethod
    def merge_tool_trace(tools_used: list[str], new_tools: list[str]) -> list[str]:
        out = list(tools_used or [])
        for t in new_tools or []:
            if t and t not in out:
                out.append(t)
        return out[:24]
