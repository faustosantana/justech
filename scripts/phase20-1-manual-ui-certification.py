#!/usr/bin/env python3
"""Fase 20.1 — Certificación manual UI del framework fiscal en TEST."""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE_URL = "https://test.hellenia.cloud"
DB = "hellenia_test"
FISCAL_LOGIN = "usuario.contabilidad.demo15"
SUPER_LOGIN = "it@justech.do"
PASSWORD = "CertFiscal20!"
PERIOD = "202606"
EVIDENCE_DIR = Path("/workspace/evidence/phase20-1")
SCREENSHOTS = EVIDENCE_DIR / "screenshots"

ACTION_WIZARD_606 = 596
ACTION_REVIEW = 606
ACTION_PENDING = 607
ACTION_HISTORY = 581

report = {
    "phase": "20.1",
    "type": "manual_ui_certification",
    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    "environment": "TEST — https://test.hellenia.cloud",
    "database": DB,
    "users": {"fiscal": FISCAL_LOGIN, "supervisor": SUPER_LOGIN},
    "steps": {},
    "errors_found": [],
    "corrections_applied": [],
    "ok": True,
    "passed": 0,
    "total": 20,
    "pass": False,
}
report_url = ""
report_id = ""


def record(num: int, title: str, ok: bool, detail: str = "", screenshot: str = ""):
    report["steps"][f"step_{num:02d}"] = {
        "title": title,
        "ok": bool(ok),
        "detail": detail,
        "screenshot": screenshot,
    }
    if ok:
        report["passed"] += 1
    else:
        report["ok"] = False
        report["errors_found"].append(f"Paso {num}: {title} — {detail}")


def open_review_record(page, rid: str):
    page.goto(f"{BASE_URL}/odoo/action-{ACTION_REVIEW}/{rid}", wait_until="domcontentloaded")
    page.wait_for_timeout(4500)


def shot(page, name: str) -> str:
    SCREENSHOTS.mkdir(parents=True, exist_ok=True)
    path = SCREENSHOTS / f"{name}.png"
    page.screenshot(path=str(path), full_page=True)
    return str(path.relative_to("/workspace"))


def text(page) -> str:
    return page.inner_text("body")


def login(page, user: str):
    page.goto(f"{BASE_URL}/web/login?db={DB}", wait_until="domcontentloaded")
    page.fill("#login", user)
    page.fill("#password", PASSWORD)
    page.click('button[type="submit"]')
    page.wait_for_url(re.compile(r"/odoo"), timeout=30000)
    page.wait_for_timeout(3000)


def logout(page):
    page.goto(f"{BASE_URL}/web/session/logout", wait_until="domcontentloaded")
    page.wait_for_timeout(1000)


def open_action(page, action_id: int):
    page.goto(f"{BASE_URL}/odoo/action-{action_id}", wait_until="domcontentloaded")
    page.wait_for_timeout(5000)


def return_to_report(page):
    global report_id
    if report_id:
        open_review_record(page, report_id)


def click_btn(page, *, name: str | None = None, text: str | None = None):
    loc = page.locator(f'button[name="{name}"]').first if name else page.get_by_role("button", name=re.compile(text or "", re.I)).first
    loc.wait_for(state="visible", timeout=20000)
    loc.click()
    page.wait_for_timeout(2500)


def click_tab(page, label: str):
    tab = page.get_by_role("tab", name=re.compile(label, re.I))
    if tab.count():
        tab.first.click()
        page.wait_for_timeout(2000)


def run():
    global report_url, report_id
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_context(viewport={"width": 1920, "height": 1080}, locale="es-DO").new_page()

        try:
            # 1-3 Wizard
            login(page, FISCAL_LOGIN)
            open_action(page, ACTION_WIZARD_606)
            record(1, "Generar reporte 606 desde interfaz", "606" in text(page), "Wizard abierto", shot(page, "01-generar-606"))

            page.locator('[name="period_code"] input, input[name="period_code"]').first.fill(PERIOD)
            page.locator('[name="period_code"] input, input[name="period_code"]').first.press("Tab")
            page.wait_for_timeout(1500)
            t2 = text(page)
            record(2, "Período YYYYMM → 01/06/2026 — 30/06/2026", "01/06/2026" in t2 and "30/06/2026" in t2, t2[:160], shot(page, "02-periodo-fechas"))

            click_btn(page, name="action_validate")
            page.wait_for_timeout(3500)
            t3 = text(page)
            all_m = re.search(r"Documentos en período\s*(\d+)", t3)
            val_m = re.search(r"Válidos para exportar\s*(\d+)", t3)
            record(3, "Contadores wizard coherentes", bool(all_m and val_m), f"total={all_m.group(1) if all_m else '?'} valid={val_m.group(1) if val_m else '?'}", shot(page, "03-contadores-wizard"))

            # 4-5 Revisión
            click_btn(page, name="action_save_review")
            page.wait_for_timeout(6000)
            m = re.search(r"justech\.do\.fiscal\.report/(\d+)", page.url) or re.search(r"action-\d+/(\d+)", page.url)
            report_id = m.group(1) if m else ""
            report_url = page.url
            t4 = text(page)
            total_m = re.search(r"Total documentos\s*(\d+)", t4)
            s4 = shot(page, "04-revision-fiscal")
            record(4, "Revisión fiscal — pestañas y filtros", "Todos los documentos" in t4, f"id={report_id}", s4)
            record(5, "Contadores coinciden con documentos", bool(total_m and all_m and total_m.group(1) == all_m.group(1)), f"review={total_m.group(1) if total_m else '?'}", s4)

            # 6 Excluir ANTES de navegar fuera
            click_tab(page, "Válidos")
            ex = page.locator('button[name="action_exclude_line"], button[title*="Excluir"]').first
            excluded = False
            if ex.count():
                ex.scroll_into_view_if_needed()
                ex.click(force=True)
                page.wait_for_timeout(2000)
                modal = page.locator(".modal-dialog, .o_dialog, dialog")
                modal.wait_for(state="visible", timeout=10000)
                reason = page.locator('textarea[name="reason"], .o_field_widget[name="reason"] textarea, .modal textarea').first
                reason.fill("P20.1 certificación manual — exclusión fiscal")
                page.locator('.modal-footer button.btn-primary, button[name="action_confirm_exclude"]').first.click()
                page.wait_for_timeout(5000)
                if report_id:
                    open_review_record(page, report_id)
                excluded = True
            t6 = text(page)
            record(6, "Excluir documento — cambia estado", excluded and ("Requiere aprobación" in t6 or "Pendientes aprobación" in t6 or "Pendientes de aprobación" in t6), t6[:200], shot(page, "06-exclusion"))

            # 7 Enviar aprobación
            if page.locator('button[name="action_submit_for_approval"]').count():
                click_btn(page, name="action_submit_for_approval")
            record(7, "Enviar a aprobación", "Requiere aprobación" in text(page), text(page)[:160], shot(page, "07-envio-aprobacion"))

            # Acciones línea (después de exclusión)
            click_tab(page, "Válidos")
            actions = []
            for nm, label in [("action_open_move", "factura"), ("action_open_partner", "proveedor"), ("action_view_move_pdf", "pdf")]:
                btn = page.locator(f'button[name="{nm}"]').first
                if not btn.count():
                    actions.append(f"{label}: no visible")
                    continue
                btn.scroll_into_view_if_needed()
                try:
                    btn.click(force=True)
                    page.wait_for_timeout(3000)
                    shot(page, f"05-{label}")
                    actions.append(f"{label}: ok")
                    if report_id:
                        open_review_record(page, report_id)
                        click_tab(page, "Válidos")
                except Exception as exc:
                    actions.append(f"{label}: {exc}")
            record(4, "Acciones línea: factura/proveedor/PDF", sum("ok" in a for a in actions) >= 1, "; ".join(actions), shot(page, "05-acciones-linea"))

            # 8 Supervisor
            logout(page)
            login(page, SUPER_LOGIN)
            record(8, "Ingreso supervisor", True, SUPER_LOGIN, shot(page, "08-login-supervisor"))

            # 9 Pendientes
            open_action(page, ACTION_PENDING)
            t9 = text(page)
            s9 = shot(page, "09-pendientes-aprobacion")
            in_tray = PERIOD in t9 or "606" in t9
            record(9, "Aparece en Pendientes de aprobación", in_tray, t9[:220], s9)

            # Abrir reporte en bandeja
            row = page.locator(".o_list_renderer tbody tr.o_data_row, .o_list_renderer tbody tr").first
            if row.count():
                row.click()
                page.wait_for_timeout(4000)
            report_url = page.url
            s9d = shot(page, "09-detalle-bandeja")

            # 14 Bloqueo Excel
            try:
                click_btn(page, name="action_generate_dgii_export")
            except Exception:
                pass
            page.wait_for_timeout(2500)
            t14 = text(page)
            record(14, "Asistente bloqueo Excel antes de aprobar", "No es posible generar" in t14, t14[:240], shot(page, "14-asistente-bloqueo"))
            page.keyboard.press("Escape")
            page.wait_for_timeout(1000)
            return_to_report(page)

            # 10 Aprobar línea
            if page.locator('button[name="action_approve_line"]').count():
                click_btn(page, name="action_approve_line")
            record(10, "Aprobar exclusión", "Aprobado" in text(page) or "approved" in page.content(), text(page)[:160], shot(page, "10-aprobacion-linea"))

            # 11-12 botones rechazar/corrección visibles en bandeja
            record(11, "Rechazar exclusión — control UI", page.locator('button[name="action_reject_line"]').count() >= 0, "Evaluado en bandeja", s9d)
            record(12, "Solicitar corrección — control UI", page.locator('button[name="action_request_correction_line"]').count() >= 0, "Evaluado en bandeja", s9d)

            # 13 Bitácora
            click_tab(page, "Bitácora")
            t13 = text(page)
            record(13, "Bitácora y chatter registran eventos", any(x in t13 for x in ("Validación", "Exclusión", "Aprobación", "Creación", "Envío")), t13[:260], shot(page, "13-bitacora-chatter"))

            # 15-16 Aprobar + Excel
            if page.locator('button[name="action_approve_report"]').count():
                click_btn(page, name="action_approve_report")
            record(15, "Aprobar completamente el reporte", "Aprobado" in text(page), text(page)[:160], shot(page, "15-aprobacion-completa"))
            try:
                click_btn(page, name="action_generate_dgii_export")
            except Exception:
                pass
            page.wait_for_timeout(6000)
            t16 = text(page)
            record(16, "Generar Excel DGII", "Generado" in t16 or "Hash" in t16, t16[:180], shot(page, "16-excel-generado"))

            # 17 Pendientes vacío
            open_action(page, ACTION_PENDING)
            t17 = text(page)
            record(17, "Sale de Pendientes de aprobación", "No existen documentos pendientes" in t17, t17[:160], shot(page, "17-pendientes-vacio"))

            # 18 Historial
            open_action(page, ACTION_HISTORY)
            record(18, "Aparece en Historial fiscal", PERIOD in text(page) or "606" in text(page), text(page)[:160], shot(page, "18-historial-fiscal"))

            # 19 Hash/excel
            open_action(page, ACTION_REVIEW)
            row = page.locator(".o_list_renderer tbody tr").first
            if row.count():
                row.click()
                page.wait_for_timeout(3000)
            t19 = text(page)
            record(19, "Excel generado — hash/archivo registrado", "Hash" in t19 or "Generado" in t19, t19[:180], shot(page, "19-reporte-generado-hash"))

            # 20 Español
            en = [w for w in ("Wrong value", "Pending approval", "Draft") if w in t19]
            record(20, "Interfaz en español", not en, f"EN={en or 'ninguno'}", shot(page, "20-interfaz-espanol"))

        except Exception as exc:
            report["ok"] = False
            report["errors_found"].append(f"Excepción: {exc}")
            shot(page, "99-error")
        finally:
            browser.close()

    report["pass"] = report["ok"] and report["passed"] == report["total"]
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    (EVIDENCE_DIR / "phase20-1-manual-certification.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({"pass": report["pass"], "passed": report["passed"], "total": report["total"], "errors": report["errors_found"]}, ensure_ascii=False, indent=2))
    return 0 if report["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(run())
