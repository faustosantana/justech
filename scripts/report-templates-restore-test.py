# -*- coding: utf-8 -*-
"""Restaura TEST desde backup tras comparación A/B (solo hellenia_test)."""
import json
import os

DB = env.cr.dbname
if DB != "hellenia_test":
    raise SystemExit(f"ABORT: solo hellenia_test, actual={DB}")

BACKUP = "/tmp/report-templates-comparison/backup/restore_backup.json"
if not os.path.exists(BACKUP):
    BACKUP = "/opt/odoo-projects/hellenia/evidence/report-templates-diagnostic/backup/restore_backup.json"
with open(BACKUP, encoding="utf-8") as f:
    backup = json.load(f)

steps = []
for mod_name in ["hellenia_reports", "hellenia_ux"]:
    mod = env["ir.module.module"].search([("name", "=", mod_name)], limit=1)
    if mod and backup["modules"].get(mod_name) == "installed" and mod.state != "installed":
        mod.button_immediate_install()
        steps.append(f"reinstalled_{mod_name}")
mod = env["ir.module.module"].search([("name", "=", "hellenia_reports")], limit=1)
if mod and mod.state == "installed":
    mod.button_immediate_upgrade()
    steps.append("upgraded_hellenia_reports")
env.cr.commit()

for vid, info in backup.get("view_states", {}).items():
    v = env["ir.ui.view"].browse(int(vid)).exists()
    if v:
        v.write({"active": info["active"]})
steps.append("views")

layout_xml = backup.get("company_layout_xml_id")
if layout_xml:
    layout = env.ref(layout_xml, raise_if_not_found=False)
    if layout:
        env.company.write({"external_report_layout_id": layout.id})
steps.append("layout")

for xmlid, pf_info in backup.get("paperformats", {}).items():
    try:
        act = env.ref(xmlid)
        pf_id = False
        if isinstance(pf_info, dict):
            pf_xml = pf_info.get("xml_id")
            if pf_xml:
                pf = env.ref(pf_xml, raise_if_not_found=False)
                pf_id = pf.id if pf else False
        elif isinstance(pf_info, int) and pf_info:
            pf = env["report.paperformat"].browse(pf_info).exists()
            pf_id = pf.id if pf else False
        if not pf_id:
            pf = env.ref("hellenia_reports.paperformat_hellenia_letter", raise_if_not_found=False)
            pf_id = pf.id if pf else False
        act.write({"paperformat_id": pf_id or False})
    except Exception as e:
        steps.append(f"pf_fail_{xmlid}:{str(e)[:60]}")
steps.append("paperformats")
env.cr.commit()

mods = {m.name: m.state for m in env["ir.module.module"].search([("name", "in", ["hellenia_reports", "hellenia_ux", "hellenia_account"])])}
print("RESTORE_OK:" + json.dumps({"steps": steps, "modules": mods}))
