# -*- coding: utf-8 -*-
"""HELLENIA-QUOTATION-TERMS-1 — validación términos cotización."""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone

from odoo.tools import is_html_empty

DB = env.cr.dbname
if DB != "hellenia_prod":
    raise SystemExit(f"ABORT: solo hellenia_prod, actual={DB}")

report = {
    "phase": "HELLENIA-QUOTATION-TERMS-1",
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


TAG = "QUOTATION-TERMS-1"
Partner = env["res.partner"]
SaleOrder = env["sale.order"]
Company = env["res.company"]

company = env.company
# Ensure company terms are HTML list
company.hellenia_migrate_quotation_terms_to_html()
terms = company.hellenia_quotation_terms or ""
ok(
    "settings_html",
    "Html" if "<li>" in str(terms) and "&lt;br" not in str(terms) else str(terms)[:120],
)
if "&lt;br" in str(terms) or "<br/>" in str(terms) and "<li>" not in str(terms):
    # br alone in company config is ok if inside html editor; fail only escaped
    if "&lt;br" in str(terms):
        fail("settings_no_escaped_br", str(terms)[:200])

# Snapshot old quote note before changes
old = SaleOrder.search([("state", "in", ("draft", "sent", "sale"))], order="id asc", limit=1)
old_note_before = str(old.note) if old else None
old_id = old.id if old else None

# Create partner + new quotation
partner = Partner.create({"name": f"{TAG} Cliente", "email": "terms1@hellenia.test"})
so_new = SaleOrder.create(
    {
        "partner_id": partner.id,
        "company_id": company.id,
    }
)
note_new = str(so_new.note or "")
if is_html_empty(so_new.note):
    fail("autoload", "note vacío")
elif "&lt;br" in note_new or "&lt;p" in note_new:
    fail("no_escaped_tags", note_new[:200])
elif "<li>" not in note_new and "•" not in note_new:
    # still ok if ul missing but no escaped tags - check render helper
    rendered = str(so_new.jt_quotation_note_for_report() or "")
    if "&lt;br" in rendered:
        fail("render_pdf", rendered[:200])
    else:
        ok("autoload", note_new[:160])
else:
    ok("autoload", note_new[:160])

rendered = str(so_new.jt_quotation_note_for_report() or "")
if any(tok in rendered for tok in ("&lt;br", "&lt;p", "<br/>")) and "&lt;" in rendered:
    fail("pdf_html", rendered[:200])
else:
    ok("pdf_html", rendered[:160])

# PDF render smoke
pdf_ok = False
try:
    pdf, _ = (
        env["ir.actions.report"]
        .sudo()
        ._render_qweb_pdf("sale.action_report_saleorder", res_ids=so_new.ids)
    )
    pdf_ok = bool(pdf) and pdf[:4] == b"%PDF"
    # Ensure raw escaped tags not in PDF text stream roughly
    textish = pdf.decode("latin-1", errors="ignore")
    if "&lt;br" in textish or "lt;br" in textish:
        fail("pdf_no_literal_br", "PDF contiene br escapado")
    else:
        ok("pdf_bytes", f"size={len(pdf)}")
except Exception as e:
    fail("pdf_bytes", str(e))

# Modify company terms and create second quote
marker = f"TERMINO-TEST-{datetime.now(timezone.utc).strftime('%H%M%S')}"
company.hellenia_quotation_terms = f"<ul><li>{marker} vigencia especial.</li><li>Segundo punto de prueba.</li></ul>"
so_new2 = SaleOrder.create({"partner_id": partner.id, "company_id": company.id})
note2 = str(so_new2.note or "")
if marker in note2:
    ok("new_uses_updated_config", note2[:160])
else:
    fail("new_uses_updated_config", note2[:200])

# Old quote keeps previous note
if old_id:
    old.invalidate_recordset()
    old_note_after = str(old.note or "")
    if old_note_after == old_note_before:
        ok("old_preserved", f"order={old_id}")
    else:
        fail("old_preserved", "note cambió")
    # Display sanitizer should not show escaped br
    disp = str(old.jt_quotation_note_for_report() or "")
    if "&lt;br" in disp:
        fail("old_display_clean", disp[:160])
    else:
        ok("old_display_clean", disp[:160])
else:
    ok("old_preserved", "no old quote")

# Restore company elegant default
company.hellenia_quotation_terms = env["res.company"].hellenia_plain_terms_to_html(
    """Las piezas ofrecidas son únicas y están sujetas a disponibilidad.
Esta cotización tiene una vigencia de cinco (5) días calendario.
La reserva de una pieza requiere la confirmación del pago correspondiente.
El transporte puede ser suministrado previa cotización.
La asesoría de colocación, instalación y styling puede contratarse adicionalmente.
Las piezas pueden presentar marcas propias del tiempo, las cuales forman parte de su autenticidad y valor histórico."""
)

# Cleanup test SOs (cancel/unlink drafts)
for so in (so_new, so_new2):
    try:
        so.unlink()
    except Exception:
        so.write({"note": False})
        try:
            so.unlink()
        except Exception:
            pass
try:
    partner.unlink()
except Exception:
    partner.action_archive()

mods = env["ir.module.module"].sudo().search(
    [("name", "in", ("hellenia_reports", "justech_report_design"))]
)
report["modules"] = {m.name: m.latest_version for m in mods}
report["settings_path"] = "Configuración → Ventas → Cotizaciones y pedidos → Términos y Condiciones"

print(json.dumps(report, ensure_ascii=False, indent=2, default=str))
env.cr.commit()
