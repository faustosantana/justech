"""Helpers compartidos para tests DGCP — flujo operativo con «Mostrar interés»."""

from __future__ import annotations

from httpx import AsyncClient

INTEREST_STATUSES = frozenset({"interested", "to_bid", "won", "lost"})


async def ensure_operational_interest(
    client: AsyncClient,
    opp_id: str,
    headers: dict[str, str],
) -> None:
    opp = await client.get(f"/api/v1/dgcp/opportunities/{opp_id}", headers=headers)
    assert opp.status_code == 200, opp.text
    if opp.json().get("status") not in INTEREST_STATUSES:
        action = await client.post(
            f"/api/v1/dgcp/opportunities/{opp_id}/actions",
            headers=headers,
            json={"action": "mostrar_interes"},
        )
        assert action.status_code == 200, action.text


async def analyze_with_interest(
    client: AsyncClient,
    opp_id: str,
    headers: dict[str, str],
):
    await ensure_operational_interest(client, opp_id, headers)
    return await client.post(
        f"/api/v1/dgcp/opportunities/{opp_id}/requirements/analyze",
        headers=headers,
    )


async def find_opportunity_for_expediente_test(
    client: AsyncClient,
    headers: dict[str, str],
) -> str | None:
    """Oportunidad sin expediente preparado — evita estado compartido entre tests."""
    list_res = await client.get("/api/v1/dgcp/opportunities?limit=50", headers=headers)
    if list_res.status_code != 200:
        return None
    items = list_res.json().get("items") or []

    for item in items:
        if item.get("status") in ("detected", "to_review"):
            return item["id"]

    for item in items:
        if item.get("status") != "interested":
            continue
        opp_id = item["id"]
        exp = await client.get(
            f"/api/v1/dgcp/opportunities/{opp_id}/bid-package/status",
            headers=headers,
        )
        if exp.status_code != 200:
            continue
        body = exp.json()
        if body.get("expediente_status") == "sin_preparar" and (body.get("preparation_pct") or 0) == 0:
            return opp_id

    return None
