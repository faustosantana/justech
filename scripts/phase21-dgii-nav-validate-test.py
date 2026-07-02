# -*- coding: utf-8 -*-
"""Validación navegación DGII — acciones, vistas, menús (sin 404/RPC)."""
from __future__ import annotations

DB = env.cr.dbname
if DB != "hellenia_test":
    raise SystemExit(f"ABORT: solo hellenia_test, actual={DB}")

report_data = {"checks": {}, "ok": True, "passed": 0, "total": 0, "pass": False}

ACTIONS = {
    "606": "justech_l10n_do_reports.action_justech_do_report_606",
    "607": "justech_l10n_do_reports.action_justech_do_report_607",
    "608": "justech_l10n_do_reports.action_justech_do_report_608",
    "609": "justech_l10n_do_reports.action_justech_do_report_609",
    "623": "justech_l10n_do_reports.action_justech_do_report_623",
    "review": "justech_l10n_do_reports.action_justech_do_fiscal_review",
    "pending": "justech_l10n_do_reports.action_justech_do_fiscal_review_pending",
    "history": "justech_l10n_do_reports.action_justech_do_fiscal_report",
}

MENUS = {
    "606": "justech_l10n_do_reports.menu_justech_do_report_606",
    "607": "justech_l10n_do_reports.menu_justech_do_report_607",
    "608": "justech_l10n_do_reports.menu_justech_do_report_608",
    "609": "justech_l10n_do_reports.menu_justech_do_report_609",
    "623": "justech_l10n_do_reports.menu_justech_do_report_623",
    "review": "justech_l10n_do_reports.menu_justech_do_fiscal_review",
    "pending": "justech_l10n_do_reports.menu_justech_do_fiscal_review_pending",
    "history": "justech_l10n_do_reports.menu_justech_do_reports_history",
}


def check(key, ok, detail=""):
    report_data["checks"][key] = {"ok": bool(ok), "detail": str(detail)[:400]}
    report_data["total"] += 1
    if ok:
        report_data["passed"] += 1
    else:
        report_data["ok"] = False


def validate_action(key, xid):
    act = env.ref(xid, raise_if_not_found=False)
    check(f"action_exists_{key}", bool(act), xid)
    if not act:
        return
    check(f"action_model_{key}", bool(act.res_model), act.res_model)
    try:
        action_dict = act._get_action_dict()
    except Exception as exc:
        check(f"action_dict_{key}", False, exc)
        return
    check(f"action_dict_{key}", True, act.res_model)
    model = action_dict["res_model"]
    if not env[model]._name:
        check(f"model_registry_{key}", False, model)
        return
    check(f"model_registry_{key}", True, model)
    views = action_dict.get("views")
    if views:
        for vid, mode in views:
            if vid:
                view = env["ir.ui.view"].browse(vid)
                check(f"view_exists_{key}_{mode}", view.exists(), f"{vid} {view.name if view else ''}")
                env[model].get_views([(vid, mode)])
            else:
                env[model].get_views([(False, mode)])
            check(f"get_views_{key}_{mode}", True, f"{vid},{mode}")
    else:
        for mode in (action_dict.get("view_mode") or "form").split(","):
            env[model].get_views([(False, mode.strip())])
            check(f"get_views_{key}_{mode.strip()}", True, mode)
    if action_dict.get("search_view_id"):
        sv = env["ir.ui.view"].browse(action_dict["search_view_id"][0])
        check(f"search_view_{key}", sv.exists(), sv.name if sv else action_dict["search_view_id"])
    if act.view_id:
        check(f"view_id_{key}", act.view_id.exists(), act.view_id.name)
        env[model].get_views([(act.view_id.id, act.view_mode.split(",")[0])])
    for av in act.view_ids:
        check(
            f"view_ids_{key}_{av.view_mode}",
            av.view_id.exists(),
            f"{av.view_id.id} {av.view_id.name}",
        )


for key, xid in ACTIONS.items():
    try:
        validate_action(key, xid)
    except Exception as exc:
        check(f"action_validate_{key}", False, exc)

for key, xid in MENUS.items():
    menu = env.ref(xid, raise_if_not_found=False)
    check(f"menu_exists_{key}", bool(menu), xid)
    if menu and menu.action:
        check(
            f"menu_action_{key}",
            menu.action._name == "ir.actions.act_window",
            menu.action.res_model if menu.action._name == "ir.actions.act_window" else menu.action._name,
        )
    elif menu:
        check(f"menu_action_{key}", False, "sin acción")

removed_menus = [
    "menu_justech_do_report_606_list",
    "menu_justech_do_report_607_list",
    "menu_justech_do_report_608_list",
    "menu_justech_do_report_609_list",
    "menu_justech_do_report_623_list",
]
for mid in removed_menus:
    check(f"removed_{mid}", not env.ref(f"justech_l10n_do_reports.{mid}", raise_if_not_found=False), mid)

report = env["justech.do.fiscal.report"].search([], limit=1)
if report:
    try:
        act = report.action_open_fiscal_review()
        check("python_open_review", act.get("type") == "ir.actions.act_window", act.get("views"))
    except Exception as exc:
        check("python_open_review", False, exc)

report_data["pass"] = report_data["ok"]
print(f"DGII_NAV:{report_data['passed']}/{report_data['total']}:{'PASS' if report_data['pass'] else 'FAIL'}")
for key, val in report_data["checks"].items():
    if not val["ok"]:
        print(f"  FAIL {key}: {val['detail']}")
