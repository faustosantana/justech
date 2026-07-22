"""Utilidades Graph compartidas."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Callable


async def graph_list(
    client: Any,
    path: str,
    *,
    limit: int,
    map_row: Callable[[dict[str, Any]], Any],
    params: dict | None = None,
    use_top: bool = True,
    headers: dict[str, str] | None = None,
) -> list[Any]:
    graph = client.graph()
    if not graph.connected:
        return []
    q = dict(params or {})
    if use_top:
        q["$top"] = str(min(limit, 50))
    data = await graph.request("GET", path, params=q, headers=headers or {})
    rows = [map_row(row) for row in data.get("value", [])]
    return rows[:limit]


def parse_graph_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))
