#!/usr/bin/env python3
"""DEV E2E Bid Center — PROCURADURIA-DAF-CM-2026-0117 (real, no mocks)."""

from __future__ import annotations

import json
import sys
import time
import zipfile
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path

import httpx

BASE = "http://127.0.0.1:8022/api/v1"
CODE = "PROCURADURIA-DAF-CM-2026-0117"
EMAIL = "admin@justech.do"
PASSWORD = "JaiosAdmin2026!"
OUT = Path("evidence/dgcp-schema-hotfix-20260803/e2e")
OUT.mkdir(parents=True, exist_ok=True)

report: dict = {
    "started_at": datetime.now(timezone.utc).isoformat(),
    "process_code": CODE,
    "steps": [],
    "http_500": 0,
    "pass_criteria": {},
}


def save(name: str, data):
    p = OUT / name
    if isinstance(data, (bytes, bytearray)):
        p.write_bytes(data)
    else:
        p.write_text(json.dumps(data, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    return str(p)


def step(name: str, ok: bool, detail: dict | str | None = None, status: int | None = None):
    entry = {"name": name, "ok": ok, "status": status, "detail": detail}
    report["steps"].append(entry)
    print(f"[{'PASS' if ok else 'FAIL'}] {name} status={status} {detail if isinstance(detail, str) else ''}")
    if status == 500:
        report["http_500"] += 1


def main() -> int:
    t0 = time.time()
    client = httpx.Client(base_url=BASE, timeout=180.0)
    r = client.post("/auth/login", json={"email": EMAIL, "password": PASSWORD})
    step("login", r.status_code == 200, status=r.status_code)
    if r.status_code != 200:
        save("REPORT.json", report)
        return 1
    token = r.json()["access_token"]
    client.headers.update({"Authorization": f"Bearer {token}"})

    # Schema / health gates
    for path, label in [
        ("/health", "api_health"),
        ("/dgcp/opportunities?limit=1", "dgcp_opportunities"),
        ("/dgcp/bid-copilot/executive-dashboard", "executive_dashboard"),
    ]:
        rr = client.get(path)
        step(label, rr.status_code == 200, status=rr.status_code)
        save(f"{label}.json", rr.json() if rr.headers.get("content-type", "").startswith("application/json") else {"raw": rr.text[:2000]})

    # Sync smoke (already validated; keep small)
    rr = client.post("/dgcp/sync", json={"max_pages": 1, "page_size": 10})
    step("dgcp_sync", rr.status_code in (200, 202) and rr.json().get("status") == "completed", rr.json(), rr.status_code)
    save("sync.json", rr.json())

    # Resolve opportunity (search + include_expired; direct id fallback)
    oid_known = "15090dc8-c90e-41cd-a86a-77903a5b4a0a"
    rr = client.get(
        "/dgcp/opportunities",
        params={"search": CODE, "limit": 50, "include_expired": True},
    )
    items = rr.json().get("items") if rr.status_code == 200 else []
    opp = next((i for i in items if i.get("code") == CODE), None)
    if not opp:
        rr = client.get(f"/dgcp/opportunities/{oid_known}")
        body = rr.json() if rr.status_code == 200 else {}
        opp = body if body.get("code") == CODE else None
    step(
        "opportunity_found",
        bool(opp),
        {"id": opp.get("id") if opp else None, "status": opp.get("status") if opp else None},
        rr.status_code,
    )
    if not opp:
        report["elapsed_s"] = round(time.time() - t0, 1)
        save("REPORT.json", report)
        return 2
    oid = opp["id"]
    report["opportunity_id"] = oid
    report["opportunity_status"] = opp.get("status")
    save("opportunity.json", opp)

    # 1) Mostrar interés
    rr = client.post(f"/dgcp/opportunities/{oid}/actions", json={"action": "mostrar_interes", "notes": "E2E hotfix schema"})
    step("mostrar_interes", rr.status_code == 200, {"status": rr.json().get("status") if rr.status_code == 200 else rr.text[:500]}, rr.status_code)
    save("mostrar_interes.json", rr.json() if rr.status_code == 200 else {"error": rr.text})

    # Refresh portal documents + analyze requirements (can be long)
    rr = client.post(f"/dgcp/opportunities/{oid}/process-documents/refresh")
    step("refresh_portal_docs", rr.status_code == 200, rr.json() if rr.status_code == 200 else rr.text[:500], rr.status_code)
    save("refresh_docs.json", rr.json() if rr.status_code < 500 else {"error": rr.text})

    rr = client.get(f"/dgcp/opportunities/{oid}/process-documents")
    docs = rr.json() if rr.status_code == 200 else {}
    step("list_process_documents", rr.status_code == 200, {"count": len(docs.get("items") or docs.get("documents") or [])}, rr.status_code)
    save("process_documents.json", docs)
    published = docs.get("items") or docs.get("documents") or docs.get("portal_documents") or []
    if isinstance(docs, dict) and "summary" in docs:
        report["docs_summary"] = docs.get("summary")

    # Analyze all documents / requirements (async when force=true)
    rr = client.post(f"/dgcp/opportunities/{oid}/requirements/analyze", params={"force": "true"})
    step("analyze_requirements", rr.status_code in (200, 202, 409), rr.json() if rr.status_code < 500 else rr.text[:800], rr.status_code)
    save("analyze.json", rr.json() if rr.status_code < 500 else {"error": rr.text})

    job = rr.json() if rr.status_code < 500 else {}
    job_id = job.get("job_id") or (job.get("detail") or {}).get("job_id") if isinstance(job.get("detail"), dict) else None
    if rr.status_code == 202 and job_id:
        for _ in range(90):
            time.sleep(5)
            st = client.get(f"/dgcp/opportunities/{oid}/analysis-jobs/{job_id}")
            body = st.json() if st.status_code == 200 else {}
            status = body.get("status") or body.get("state")
            print(f"  analysis poll: {status}")
            if status in {"completed", "done", "success", "failed", "error"}:
                step("analysis_job_complete", status in {"completed", "done", "success"}, body, st.status_code)
                save("analysis_job.json", body)
                break
        else:
            step("analysis_job_complete", False, "timeout", None)
    elif rr.status_code == 200:
        step("analysis_job_complete", True, {"sync": True}, 200)
    elif rr.status_code == 409:
        step("analysis_job_complete", True, {"already": True, "body": job}, 409)

    st = client.get(f"/dgcp/opportunities/{oid}/analysis-status")
    step("analysis_status", st.status_code == 200, status=st.status_code)
    save("analysis_status.json", st.json() if st.status_code == 200 else {"error": st.text})

    st = client.get(f"/dgcp/opportunities/{oid}/requirements")
    step("requirements", st.status_code == 200, status=st.status_code)
    save("requirements.json", st.json() if st.status_code == 200 else {"error": st.text})
    reqs = st.json() if st.status_code == 200 else {}
    req_items = reqs.get("items") or reqs.get("requirements") or []
    report["requirements_count"] = len(req_items) if isinstance(req_items, list) else None

    # Checklist / dashboard pieces
    for path, label in [
        (f"/dgcp/opportunities/{oid}/checklist", "checklist"),
        (f"/dgcp/opportunities/{oid}/bid-package/status", "bid_package_status"),
        (f"/dgcp/bid-copilot/executive-dashboard", "executive_dashboard_after"),
    ]:
        rr = client.get(path)
        step(label, rr.status_code == 200, status=rr.status_code)
        save(f"{label}.json", rr.json() if rr.status_code < 500 else {"error": rr.text})

    # Upload a small test document (PDF-like text payload)
    pdfish = b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\nE2E test anexo Justech\n"
    rr = client.post(
        f"/dgcp/opportunities/{oid}/process-documents/upload",
        params={"doc_role": "anexo"},
        files={"file": ("e2e_anexo_prueba.pdf", pdfish, "application/pdf")},
    )
    step("upload_test_doc", rr.status_code in (200, 201), rr.json() if rr.status_code < 500 else rr.text[:500], rr.status_code)
    save("upload_test_doc.json", rr.json() if rr.status_code < 500 else {"error": rr.text})

    # Document validation
    rr = client.get(f"/dgcp/opportunities/{oid}/bid-package/document-validation", params={"company_key": "justech"})
    step("document_validation", rr.status_code == 200, status=rr.status_code)
    save("document_validation.json", rr.json() if rr.status_code < 500 else {"error": rr.text})

    # Similar purchases (real)
    rr = client.post(
        f"/dgcp/opportunities/{oid}/historical-similar/search",
        json={"refresh": True, "limit": 10},
    )
    step("historical_similar", rr.status_code == 200, status=rr.status_code)
    save("historical_similar.json", rr.json() if rr.status_code < 500 else {"error": rr.text})

    # Bid Copilot
    rr = client.get(f"/dgcp/opportunities/{oid}/bid-copilot")
    step("bid_copilot", rr.status_code == 200, status=rr.status_code)
    save("bid_copilot.json", rr.json() if rr.status_code < 500 else {"error": rr.text})

    # Validate expediente
    rr = client.post(f"/dgcp/opportunities/{oid}/expediente/validate")
    step("expediente_validate", rr.status_code in (200, 201), status=rr.status_code)
    save("expediente_validate.json", rr.json() if rr.status_code < 500 else {"error": rr.text})

    # Prepare + download ZIP (bid-package)
    rr = client.post(f"/dgcp/opportunities/{oid}/bid-package/prepare", params={"company_key": "justech"})
    step("prepare_bid_package", rr.status_code in (200, 201, 409), rr.json() if rr.status_code < 500 else rr.text[:800], rr.status_code)
    save("prepare.json", rr.json() if rr.status_code < 500 else {"error": rr.text})

    rr = client.get(f"/dgcp/opportunities/{oid}/bid-package/download")
    zip_ok = False
    zip_meta: dict = {}
    if rr.status_code == 200 and rr.content[:2] == b"PK":
        zpath = OUT / "expediente_export.zip"
        zpath.write_bytes(rr.content)
        try:
            with zipfile.ZipFile(BytesIO(rr.content)) as zf:
                names = zf.namelist()
                zip_meta = {
                    "filename": rr.headers.get("content-disposition"),
                    "entries": names,
                    "has_manifest": any("manifest" in n.lower() for n in names),
                    "has_index": any("indice" in n.lower() or "index" in n.lower() for n in names),
                    "has_pdf": any(n.lower().endswith(".pdf") for n in names),
                    "has_validation": any("valid" in n.lower() for n in names),
                }
                zip_ok = True
        except zipfile.BadZipFile as exc:
            zip_meta = {"error": str(exc)}
    step("export_zip", zip_ok, zip_meta, rr.status_code)
    save("export_zip_meta.json", zip_meta)

    # Also try real-expediente download path
    rr = client.get(f"/dgcp/opportunities/{oid}/real-expediente/download")
    step("real_expediente_download", rr.status_code in (200, 404, 409), status=rr.status_code)
    if rr.status_code == 200:
        (OUT / "real_expediente.zip").write_bytes(rr.content)

    # Re-list docs after flow
    rr = client.get(f"/dgcp/opportunities/{oid}/process-documents")
    docs2 = rr.json() if rr.status_code == 200 else {}
    save("process_documents_final.json", docs2)

    report["elapsed_s"] = round(time.time() - t0, 1)
    report["finished_at"] = datetime.now(timezone.utc).isoformat()
    fails = [s for s in report["steps"] if not s["ok"]]
    report["failed_steps"] = [s["name"] for s in fails]
    report["verdict"] = "PASS" if not fails and report["http_500"] == 0 else (
        "PARTIAL" if report["http_500"] == 0 else "FAIL"
    )
    save("REPORT.json", report)
    print(json.dumps({"verdict": report["verdict"], "failed": report["failed_steps"], "elapsed_s": report["elapsed_s"]}, indent=2))
    return 0 if report["verdict"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
