"""Contexto de sesión conversacional Lotería IA (por tenant/usuario/sesión)."""

from __future__ import annotations

from datetime import date
from typing import Any

from pydantic import BaseModel, Field


class LotterySessionContext(BaseModel):
    last_lottery: str | None = None
    compared_lotteries: list[str] = Field(default_factory=list)
    base_date: date | None = None
    last_from_date: date | None = None
    last_to_date: date | None = None
    last_days: int | None = None
    last_draw_count: int | None = None
    last_numbers: list[str] = Field(default_factory=list)
    last_number_type: str | None = None
    last_position: int | None = None
    last_game: str | None = None
    last_operation: str | None = None
    last_tool: str | None = None
    last_result_reference: str | None = None
    last_query_semantics: str | None = None
    pending_ambiguity: dict[str, Any] | None = None
    saved_query_id: str | None = None

    def to_store(self) -> dict[str, Any]:
        return self.model_dump(mode="json")

    @classmethod
    def from_store(cls, data: dict[str, Any] | None) -> LotterySessionContext:
        if not data:
            return cls()
        return cls.model_validate(data)


def merge_context_after_tool(
    ctx: LotterySessionContext,
    *,
    tool: str,
    params: dict[str, Any],
    result_summary: dict[str, Any] | None = None,
) -> LotterySessionContext:
    """Actualiza contexto de forma determinística tras una tool exitosa."""
    data = ctx.model_dump()
    data["last_tool"] = tool
    data["last_operation"] = tool.replace("lottery_", "")

    if lot := params.get("lottery"):
        data["last_lottery"] = lot
    if lots := params.get("lotteries"):
        data["compared_lotteries"] = list(lots)
        if lots:
            data["last_lottery"] = lots[0]
    if d := params.get("date") or params.get("base_date"):
        data["base_date"] = d
    if params.get("from_date") or params.get("from"):
        data["last_from_date"] = params.get("from_date") or params.get("from")
    if params.get("to_date") or params.get("to"):
        data["last_to_date"] = params.get("to_date") or params.get("to")
    if params.get("days") is not None:
        data["last_days"] = params["days"]
    if params.get("count") is not None:
        data["last_draw_count"] = params["count"]
    if params.get("number"):
        data["last_numbers"] = [str(params["number"])]
    if params.get("number_type"):
        data["last_number_type"] = params["number_type"]
    if params.get("position") is not None:
        data["last_position"] = params["position"]
    if params.get("game"):
        data["last_game"] = params["game"]

    if result_summary:
        if sem := result_summary.get("semantics"):
            data["last_query_semantics"] = sem
        if ref := result_summary.get("source_reference"):
            data["last_result_reference"] = ref
        if nums := result_summary.get("numbers"):
            data["last_numbers"] = [str(n) for n in nums]
        if amb := result_summary.get("pending_ambiguity"):
            data["pending_ambiguity"] = amb
        else:
            data["pending_ambiguity"] = None
        # Propagate effective range from calendar windows
        if result_summary.get("calendar_from"):
            data["last_from_date"] = result_summary["calendar_from"]
        if result_summary.get("calendar_to"):
            data["last_to_date"] = result_summary["calendar_to"]
        if sq := result_summary.get("saved_query_id"):
            data["saved_query_id"] = str(sq)
        # Persist derived last-occurrence date into sticky base_date
        if result_summary.get("last_occurrence_date") or result_summary.get("base_date"):
            data["base_date"] = (
                result_summary.get("last_occurrence_date") or result_summary.get("base_date")
            )

    return LotterySessionContext.model_validate(data)
