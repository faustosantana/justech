# -*- coding: utf-8 -*-
"""BUGFIX-QUOTATION-TERMS-1 validation (TEST or PROD)."""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone

from odoo.tools import is_html_empty

DB = env.cr.dbname
EXPECTED = os.environ.get("BUGFIX_QT_DB", "")
if EXPECTED and DB != EXPECTED:
    raise SystemExit(f"ABORT: expected {EXPECTED}, got {DB}")

report = {
    "phase": "BUGFIX-QUOTATION-TERMS-1",
    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    "database": DB,
    "ok": True,
    "checks": {},
    "errors": [],
}


def fail(k, msg):
    report["ok"] = False
    report["errors"].append(f"{k}: {msg}")
    report["checks"][k] = {"status": "FAIL", "detail": msg}
    print("FAIL", k, msg)


def ok(k, detail=""):
    report["checks"][k] = {"status": "PASS", "detail": detail}
    print("PASS", k, detail)


SO = env["sale.order"]
Company = env.company

# 1) hasattr
has_method = hasattr(SO, "jt_quotation_note_for_report")
has_field = "jt_quotation_note_html" in SO._fields
if has_method:
    ok("hasattr_method", True)
else:
    fail("hasattr_method", False)
if has_field:
    ok("hasattr_field", True)
else:
    fail("hasattr_field", False)

# 2) existing quote preview/pdf
old = SO.search([], order="id asc", limit=1)
old_note = str(old.note) if old else None
if not old:
    fail("existing_quote", "none")
else:
    try:
        html = env["ir.actions.report"]._render_qweb_html(
            "sale.action_report_saleorder", old.ids
        )
        body = html[0] if isinstance(html, (list, tuple)) else html
        text = body.decode("utf-8", "ignore") if isinstance(body, (bytes, bytearray)) else str(body)
        if "&lt;br" in text:
            fail("preview_no_escaped_br", "escaped br in html")
        else:
            ok("preview_html", f"order={old.id}")
    except Exception as e:
        fail("preview_html", f"{type(e).__name__}: {e}")
    try:
        pdf, _ = env["ir.actions.report"]._render_qweb_pdf(
            "sale.action_report_saleorder", res_ids=old.ids
        )
        if pdf[:4] == b"%PDF":
            ok("pdf", f"size={len(pdf)}")
            out = os.environ.get("BUGFIX_QT_PDF", "")
            if out:
                open(out, "wb").write(pdf)
        else:
            fail("pdf", "not pdf")
    except Exception as e:
        fail("pdf", f"{type(e).__name__}: {e}")

    rendered = str(old.jt_quotation_note_for_report() or "")
    if "&lt;br" in rendered:
        fail("terms_format", rendered[:120])
    elif rendered and ("<li>" in rendered or "<p>" in rendered or "<ul>" in rendered):
        ok("terms_format", rendered[:120])
    elif not rendered:
        ok("terms_format", "empty_ok")
    else:
        ok("terms_format", rendered[:120])

# 3) new quote autoload
partner = env["res.partner"].create({"name": "BUGFIX-QT-1 Cliente"})
so1 = SO.create({"partner_id": partner.id})
if is_html_empty(so1.note):
    fail("autoload", "empty")
elif "&lt;br" in str(so1.note):
    fail("autoload", "escaped")
else:
    ok("autoload", str(so1.note)[:120])

# 4) config change → new quote
marker = f"BFQT-{datetime.now(timezone.utc).strftime('%H%M%S')}"
Company.hellenia_quotation_terms = f"<ul><li>{marker}</li><li>Segundo.</li></ul>"
so2 = SO.create({"partner_id": partner.id})
if marker in str(so2.note):
    ok("new_uses_config", str(so2.note)[:120])
else:
    fail("new_uses_config", str(so2.note)[:120])

# 5) old preserves
if old and str(old.note) == old_note:
    ok("old_preserved", f"id={old.id}")
elif old:
    fail("old_preserved", "changed")
else:
    ok("old_preserved", "n/a")

# 6) empty terms quote still renders
so3 = SO.create({"partner_id": partner.id, "note": False})
# create may refill note — force empty
so3.write({"note": False})
try:
    pdf3, _ = env["ir.actions.report"]._render_qweb_pdf(
        "sale.action_report_saleorder", res_ids=so3.ids
    )
    ok("empty_terms_pdf", f"size={len(pdf3)}")
except Exception as e:
    fail("empty_terms_pdf", f"{type(e).__name__}: {e}")

# restore company terms default
if hasattr(Company, "hellenia_get_quotation_terms_html"):
    from odoo.addons.hellenia_reports.models.res_company import (
        DEFAULT_HELLENIA_QUOTATION_TERMS_HTML,
    )

    Company.hellenia_quotation_terms = DEFAULT_HELLENIA_QUOTATION_TERMS_HTML

# cleanup
for so in (so1, so2, so3):
    try:
        so.unlink()
    except Exception:
        pass
try:
    partner.unlink()
except Exception:
    partner.action_archive()

mods = env["ir.module.module"].sudo().search(
    [("name", "in", ("justech_report_design", "hellenia_reports"))]
)
report["modules"] = {m.name: m.latest_version for m in mods}
print(json.dumps(report, ensure_ascii=False, indent=2, default=str))
env.cr.commit()
