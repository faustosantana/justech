#!/usr/bin/env python3
"""QA funcional DGCP — flujo operativo real (no solo pytest).

Ejecutar desde backend con DB activa:
  .venv/bin/python scripts/dgcp_operational_qa.py
"""

from __future__ import annotations

import asyncio
import json
import sys
import uuid
from datetime import datetime, timezone

from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.db.session import AsyncSessionLocal
from app.main import app
from app.models.dgcp_bid_package import DGCPBidPackage
from app.models.dgcp_opportunity import DGCPOpportunity
from tests.dgcp_test_helpers import analyze_with_interest, ensure_operational_interest

LOGIN = {
    "email": "admin@justech.do",
    "password": "JaiosAdmin2026!",
    "tenant_slug": "justech",
}


def _section(title: str) -> None:
    print(f"\n{'=' * 60}\n{title}\n{'=' * 60}")


async def main() -> int:
    transport = ASGITransport(app=app)
    evidence: list[dict] = []

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        login = await client.post("/api/v1/auth/login", json=LOGIN)
        if login.status_code != 200:
            print("LOGIN FAIL", login.status_code, login.text)
            return 1
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

        list_res = await client.get("/api/v1/dgcp/opportunities?limit=50", headers=headers)
        items = list_res.json().get("items") or []
        opp = next((o for o in items if "MINERD" in o.get("code", "")), items[0] if items else None)
        if not opp:
            print("Sin oportunidades DGCP")
            return 1
        opp_id = opp["id"]
        code = opp["code"]
        print(f"Oportunidad: {code} ({opp_id})")

        _section("A. Antes de mostrar interés — analyze debe fallar")
        if opp.get("status") in ("detected", "to_review"):
            pre = await client.post(
                f"/api/v1/dgcp/opportunities/{opp_id}/requirements/analyze",
                headers=headers,
            )
            evidence.append({
                "step": "A_analyze_sin_interes",
                "endpoint": f"POST /api/v1/dgcp/opportunities/{opp_id}/requirements/analyze",
                "status": pre.status_code,
                "detail": pre.json().get("detail") if pre.status_code != 200 else pre.json(),
            })
            print("HTTP", pre.status_code, pre.json().get("detail", pre.text[:200]))
            assert pre.status_code == 400, "Analyze sin interés debe devolver 400"

        _section("B. Mostrar interés")
        await ensure_operational_interest(client, opp_id, headers)
        opp_after = await client.get(f"/api/v1/dgcp/opportunities/{opp_id}", headers=headers)
        print("Estado:", opp_after.json()["status"])
        evidence.append({
            "step": "B_mostrar_interes",
            "endpoint": f"POST /api/v1/dgcp/opportunities/{opp_id}/actions",
            "payload": {"action": "mostrar_interes"},
            "status_after": opp_after.json()["status"],
        })

        _section("C. Analizar + Docs. Proceso vs corporativo")
        analyze = await analyze_with_interest(client, opp_id, headers)
        print("Analyze HTTP", analyze.status_code)
        body = analyze.json()
        proc = await client.get(
            f"/api/v1/dgcp/opportunities/{opp_id}/process-documents",
            headers=headers,
        )
        proc_items = proc.json().get("items") or []
        corp_in_proc = [
            i for i in proc_items
            if i.get("source_type") not in ("portal", "dgcp_api", "portal_text", "process_file", "reference")
        ]
        matches = body.get("document_matches", {}).get("matches") or []
        justech = [m for m in matches if m.get("match_source") in (
            "knowledge_repository", "document_repository", "knowledge_template"
        )]
        print(f"Process docs: {len(proc_items)}, contaminación: {len(corp_in_proc)}")
        print(f"Documentos Justech en matches: {len(justech)}")
        evidence.append({
            "step": "C_separacion_documental",
            "process_documents": len(proc_items),
            "corporate_contamination": len(corp_in_proc),
            "justech_matches": len(justech),
        })

        _section("D/E. Validar + Nota + Tarea")
        checklist = await client.get(
            f"/api/v1/dgcp/opportunities/{opp_id}/checklist",
            headers=headers,
        )
        items_chk = checklist.json().get("items") or []
        target = next(
            (i for i in items_chk if i.get("document_id") or i.get("knowledge_asset_id")),
            items_chk[0],
        )
        item_id = target["id"]
        has_doc = bool(target.get("document_id") or target.get("knowledge_asset_id"))

        note_res = await client.post(
            f"/api/v1/dgcp/opportunities/{opp_id}/checklist/{item_id}/notes",
            headers=headers,
            json={"note": f"QA operacional {datetime.now(timezone.utc).isoformat()}"},
        )
        print("Nota HTTP", note_res.status_code)

        val_payload = {
            "status": "validado_manual" if has_doc else "no_aplica",
            "note": "Validación QA operacional",
        }
        val_res = await client.post(
            f"/api/v1/dgcp/opportunities/{opp_id}/checklist/{item_id}/manual-validation",
            headers=headers,
            json=val_payload,
        )
        print("Validar HTTP", val_res.status_code, val_res.json().get("new_status"))

        task1 = await client.post(
            f"/api/v1/dgcp/opportunities/{opp_id}/checklist/{item_id}/task",
            headers=headers,
        )
        task2 = await client.post(
            f"/api/v1/dgcp/opportunities/{opp_id}/checklist/{item_id}/task",
            headers=headers,
        )
        print("Tarea 1/2", task1.json().get("task_id"), task2.json().get("existing"))

        async with AsyncSessionLocal() as session:
            pkg = (
                await session.execute(
                    select(DGCPBidPackage).where(
                        DGCPBidPackage.opportunity_id == uuid.UUID(opp_id)
                    )
                )
            ).scalar_one_or_none()
            stored = next(i for i in (pkg.checklist or []) if str(i["id"]) == item_id)
            evidence.append({
                "step": "D_validar_nota_tarea_db",
                "note_history_len": len(stored.get("note_history") or []),
                "manual_validation": stored.get("manual_validation", {}).get("validated_by"),
                "task_id": stored.get("task_id"),
                "preparation_pct": (pkg.bid_package or {}).get("preparation_pct"),
            })

        _section("G. Persistencia tras recarga API")
        reload = await client.get(
            f"/api/v1/dgcp/opportunities/{opp_id}/checklist",
            headers=headers,
        )
        re_item = next(i for i in reload.json()["items"] if i["id"] == item_id)
        print("Notas persisten:", bool(re_item.get("note_history")))
        print("Task persist:", re_item.get("task_id"))

        exp = await client.get(
            f"/api/v1/dgcp/opportunities/{opp_id}/bid-package/status",
            headers=headers,
        )
        print("Expediente (solo interés, sin licitar):", exp.json().get("expediente_status"))

        out_path = ".qa/sprint-dgcp-operational-evidence.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                    "opportunity_code": code,
                    "opportunity_id": opp_id,
                    "evidence": evidence,
                },
                f,
                indent=2,
                ensure_ascii=False,
            )
        print(f"\nEvidencia escrita: {out_path}")
        return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
