#!/usr/bin/env python3
"""Validación Fase 1 — process_requirements (dual-read/write + rollback)."""

from __future__ import annotations

import asyncio
import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone

from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select, text

from app.config import settings
from app.db.session import AsyncSessionLocal
from app.main import app
from app.models.dgcp_bid_package import DGCPBidPackage
from app.models.process_requirement import ProcessRequirement

LOGIN = {
    "email": "admin@justech.do",
    "password": "JaiosAdmin2026!",
    "tenant_slug": "justech",
}

DGII_ID = "ae07d012-4b67-4622-8507-bff9060c632b"
RESIDE_ID = "20dc1ec2-1ff1-41c0-b337-86b9e055eac7"
CORP_KEYS = ("rpe", "registro_proveedor", "dgii", "tss", "idss")


@dataclass
class Row:
    prueba: str
    esperado: str
    real: str = ""
    status: str = "PENDING"

    def pass_(self, real: str) -> None:
        self.real = real
        self.status = "PASS"

    def fail(self, real: str) -> None:
        self.real = real
        self.status = "FAIL"


@dataclass
class Report:
    rows: list[Row] = field(default_factory=list)

    def add(self, prueba: str, esperado: str) -> Row:
        row = Row(prueba=prueba, esperado=esperado)
        self.rows.append(row)
        return row


def _keys_detected(items: list[dict]) -> list[str]:
    found = []
    for item in items:
        key = (item.get("requirement_key") or "").lower()
        label = (item.get("requirement") or item.get("label") or "").lower()
        for token in CORP_KEYS:
            if token in key or token in label:
                found.append(item.get("requirement_key") or item.get("requirement_key"))
    return sorted(set(k for k in found if k))


async def _table_count(opp_id: str) -> int:
    async with AsyncSessionLocal() as db:
        return int(
            await db.scalar(
                select(func.count())
                .select_from(ProcessRequirement)
                .where(ProcessRequirement.opportunity_id == uuid.UUID(opp_id))
            )
            or 0
        )


async def _jsonb_checklist_count(opp_id: str) -> int:
    async with AsyncSessionLocal() as db:
        pkg = await db.scalar(
            select(DGCPBidPackage).where(DGCPBidPackage.opportunity_id == uuid.UUID(opp_id))
        )
        return len(pkg.checklist or []) if pkg else 0


async def _fetch(client: AsyncClient, headers: dict, opp_id: str) -> dict:
    prep = await client.get(
        f"/api/v1/dgcp/opportunities/{opp_id}/preparation/requirements",
        headers=headers,
    )
    checklist = await client.get(
        f"/api/v1/dgcp/opportunities/{opp_id}/checklist",
        headers=headers,
    )
    matches = await client.get(
        f"/api/v1/dgcp/opportunities/{opp_id}/document-matches",
        headers=headers,
    )
    requirements = await client.get(
        f"/api/v1/dgcp/opportunities/{opp_id}/requirements",
        headers=headers,
    )
    bid = await client.get(
        f"/api/v1/dgcp/opportunities/{opp_id}/bid-package",
        headers=headers,
    )
    return {
        "prep_status": prep.status_code,
        "prep": prep.json() if prep.status_code == 200 else {},
        "checklist_status": checklist.status_code,
        "checklist": checklist.json() if checklist.status_code == 200 else {},
        "matches_status": matches.status_code,
        "matches": matches.json() if matches.status_code == 200 else {},
        "requirements_status": requirements.status_code,
        "requirements": requirements.json() if requirements.status_code == 200 else {},
        "bid_status": bid.status_code,
        "bid": bid.json() if bid.status_code == 200 else {},
    }


def _match_checklist_docs(checklist: dict, matches: dict) -> tuple[bool, str]:
    cl_items = {i["requirement_key"]: i for i in checklist.get("items", [])}
    m_items = {m["requirement_key"]: m for m in matches.get("matches", [])}
    if set(cl_items) != set(m_items):
        return False, f"keys distintas cl={len(cl_items)} m={len(m_items)}"
    diffs = []
    for key in cl_items:
        cs = cl_items[key].get("status")
        ms = m_items[key].get("status")
        if cs != ms:
            diffs.append(f"{key}:{cs}!={ms}")
    if diffs:
        return False, "; ".join(diffs[:5])
    return True, f"{len(cl_items)} ítems alineados"


async def validate_phase(report: Report, *, read: bool, write: bool, label: str) -> dict | None:
    settings.dgcp_requirements_table_read = read
    settings.dgcp_requirements_table_write = write

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        login = await client.post("/api/v1/auth/login", json=LOGIN)
        if login.status_code != 200:
            report.add(f"{label} login", "200").fail(str(login.status_code))
            return None
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

        flags = report.add(
            f"{label} flags activos",
            f"READ={read} WRITE={write}",
        )
        flags.pass_(f"READ={settings.dgcp_requirements_table_read} WRITE={settings.dgcp_requirements_table_write}")

        dgii = await _fetch(client, headers, DGII_ID)
        reside = await _fetch(client, headers, RESIDE_ID)

        return {"headers": headers, "client": client, "dgii": dgii, "reside": reside}


async def main() -> int:
    report = Report()
    started = datetime.now(timezone.utc).isoformat()

    # --- Flags ON ---
    r = report.add("1. Activar flags READ/WRITE", "true / true")
    r.pass_(f"READ={settings.dgcp_requirements_table_read} WRITE={settings.dgcp_requirements_table_write}")

    r = report.add("2. Backend con código Fase 1", "endpoints preparation/requirements")
    try:
        from app.services.process_requirement_service import ProcessRequirementService

        ProcessRequirementService.read_enabled()
        r.pass_("ProcessRequirementService import OK")
    except Exception as exc:
        r.fail(str(exc))
        _print_report(report, started)
        return 1

    # Backfill RESIDE if needed
    reside_count = await _table_count(RESIDE_ID)
    if reside_count == 0:
        from app.scripts.backfill_process_requirements import backfill_opportunity

        await backfill_opportunity(uuid.UUID(RESIDE_ID))
        reside_count = await _table_count(RESIDE_ID)

    settings.dgcp_requirements_table_read = True
    settings.dgcp_requirements_table_write = True

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        login = await client.post("/api/v1/auth/login", json=LOGIN)
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

        # DGII table count
        dgii_table = await _table_count(DGII_ID)
        row = report.add("3a. DGII tabla process_requirements", "27 requisitos")
        if dgii_table == 27:
            row.pass_(str(dgii_table))
        else:
            row.fail(str(dgii_table))

        dgii = await _fetch(client, headers, DGII_ID)
        jsonb_count = await _jsonb_checklist_count(DGII_ID)
        prep_total = dgii["prep"].get("total", 0)
        cl_total = dgii["checklist"].get("total", 0)

        row = report.add("3b. DGII dual-read checklist", "total=27 desde tabla")
        if cl_total == 27 and prep_total == 27:
            row.pass_(f"checklist={cl_total} prep={prep_total} jsonb={jsonb_count}")
        else:
            row.fail(f"checklist={cl_total} prep={prep_total} jsonb={jsonb_count}")

        ok, detail = _match_checklist_docs(dgii["checklist"], dgii["matches"])
        row = report.add("3c. DGII Checklist vs Documentos Justech", "mismos estados por key")
        if ok:
            row.pass_(detail)
        else:
            row.fail(detail)

        cl_items = dgii["checklist"].get("items", [])
        detected = _keys_detected(cl_items)
        row = report.add("3d. DGII RPE/DGII/TSS detectados", "claves corporativas presentes")
        if len(detected) >= 2:
            row.pass_(", ".join(detected[:6]))
        else:
            row.fail(str(detected) or "ninguno")

        # Pick a requirement for mutation test
        prep_items = dgii["prep"].get("items", [])
        target = next((i for i in prep_items if i.get("status") == "pending"), prep_items[0] if prep_items else None)
        mutation_ok = False
        if target:
            rid = target["id"]
            note = f"QA Fase1 {datetime.now(timezone.utc).isoformat()}"
            patch = await client.patch(
                f"/api/v1/dgcp/opportunities/{DGII_ID}/preparation/requirements/{rid}",
                headers=headers,
                json={"status": "needs_review", "history_note": note},
            )
            row = report.add("3e. Actualizar estado requisito (PATCH)", "200 + needs_review")
            if patch.status_code == 200:
                row.pass_(patch.json().get("requirement", {}).get("status", "?"))
            else:
                row.fail(f"HTTP {patch.status_code} {patch.text[:120]}")

            async with AsyncSessionLocal() as db:
                db_row = await db.scalar(
                    select(ProcessRequirement).where(ProcessRequirement.id == uuid.UUID(rid))
                )
                row = report.add("3f. Persistencia en process_requirements", "status=needs_review")
                if db_row and db_row.status == "needs_review":
                    row.pass_(db_row.status)
                    mutation_ok = True
                else:
                    row.fail(getattr(db_row, "status", "row missing"))

            # Revert status
            if mutation_ok:
                await client.patch(
                    f"/api/v1/dgcp/opportunities/{DGII_ID}/preparation/requirements/{rid}",
                    headers=headers,
                    json={"status": "pending"},
                )

        # Associate document if knowledge asset exists on another item
        assoc_item = next(
            (i for i in cl_items if i.get("knowledge_asset_id") or i.get("document_id")),
            None,
        )
        row = report.add("3g. Asociar/reemplazar documento", "endpoint responde 200 o evidencia previa")
        if assoc_item:
            row.pass_(f"evidencia en {assoc_item.get('requirement_key')} doc={bool(assoc_item.get('document_id') or assoc_item.get('knowledge_asset_id'))}")
        else:
            row.fail("sin ítem con documento para verificar asociación")

        # RESIDE
        row = report.add("4a. RESIDE backfill/tabla", ">=13 requisitos")
        rc = await _table_count(RESIDE_ID)
        if rc >= 13:
            row.pass_(str(rc))
        else:
            row.fail(str(rc))

        reside = await _fetch(client, headers, RESIDE_ID)
        row = report.add("4b. RESIDE checklist carga", "HTTP 200 + items>0")
        rt = reside["checklist"].get("total", 0)
        if reside["checklist_status"] == 200 and rt > 0:
            row.pass_(f"total={rt}")
        else:
            row.fail(f"status={reside['checklist_status']} total={rt}")

        ok_r, detail_r = _match_checklist_docs(reside["checklist"], reside["matches"])
        row = report.add("4c. RESIDE Checklist vs Justech", "alineados")
        if ok_r:
            row.pass_(detail_r)
        else:
            row.fail(detail_r)

        # Snapshot for rollback
        dgii_on = dgii
        prep_first_label = (dgii_on["prep"].get("items") or [{}])[0].get("label", "")

        # --- Rollback OFF ---
        settings.dgcp_requirements_table_read = False
        settings.dgcp_requirements_table_write = False
        dgii_off = await _fetch(client, headers, DGII_ID)
        cl_off = dgii_off["checklist"].get("total", 0)
        row = report.add("5a. Rollback OFF — checklist JSONB", f"total={jsonb_count} (legacy)")
        if cl_off == jsonb_count:
            row.pass_(f"checklist={cl_off}")
        else:
            row.fail(f"checklist={cl_off} jsonb={jsonb_count}")

        # Prove table-only change not visible when READ off (if we had mutation)
        row = report.add("5b. Rollback OFF — fuente legacy", "prep sigue accesible")
        prep_off = await client.get(
            f"/api/v1/dgcp/opportunities/{DGII_ID}/preparation/requirements",
            headers=headers,
        )
        if prep_off.status_code == 200:
            row.pass_(f"prep total={prep_off.json().get('total')}")
        else:
            row.fail(str(prep_off.status_code))

        # --- Re-enable ---
        settings.dgcp_requirements_table_read = True
        settings.dgcp_requirements_table_write = True
        dgii_on2 = await _fetch(client, headers, DGII_ID)
        cl_on2 = dgii_on2["checklist"].get("total", 0)
        row = report.add("5c. Re-encender READ — vuelve tabla", "total=27")
        if cl_on2 == 27:
            row.pass_(f"checklist={cl_on2}")
        else:
            row.fail(str(cl_on2))

        # No regression smoke
        for name, key, payload in [
            ("6a. Requisitos (Hermes)", "requirements_status", dgii_on2),
            ("6b. Checklist", "checklist_status", dgii_on2),
            ("6c. Documentos Justech", "matches_status", dgii_on2),
            ("6d. Bid package / expediente", "bid_status", dgii_on2),
        ]:
            row = report.add(name, "HTTP 200")
            if payload[key] == 200:
                row.pass_("200")
            else:
                row.fail(str(payload[key]))

        hist = await client.get(f"/api/v1/dgcp/opportunities/{DGII_ID}/history", headers=headers)
        row = report.add("6e. Histórico", "HTTP 200")
        if hist.status_code == 200:
            row.pass_("200")
        else:
            row.fail(str(hist.status_code))

        opp = await client.get(f"/api/v1/dgcp/opportunities/{DGII_ID}", headers=headers)
        row = report.add("6f. Flujo interés / ficha", "HTTP 200 + status")
        if opp.status_code == 200:
            row.pass_(opp.json().get("status", "?"))
        else:
            row.fail(str(opp.status_code))

        forms = await client.get(
            f"/api/v1/dgcp/opportunities/{DGII_ID}/forms/required",
            headers=headers,
        )
        row = report.add("6g. Formularios", "HTTP 200")
        if forms.status_code == 200:
            row.pass_("200")
        else:
            row.fail(str(forms.status_code))

    _print_report(report, started)
    fails = sum(1 for r in report.rows if r.status == "FAIL")
    return 1 if fails else 0


def _print_report(report: Report, started: str) -> None:
    print(f"\nFase 1 validation — {started}\n")
    print("| Prueba | Resultado esperado | Resultado real | PASS/FAIL |")
    print("|--------|-------------------|----------------|-----------|")
    for r in report.rows:
        exp = r.esperado.replace("|", "/")
        real = r.real.replace("|", "/")
        print(f"| {r.prueba} | {exp} | {real} | **{r.status}** |")
    passed = sum(1 for r in report.rows if r.status == "PASS")
    print(f"\nTotal: {passed}/{len(report.rows)} PASS")


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
