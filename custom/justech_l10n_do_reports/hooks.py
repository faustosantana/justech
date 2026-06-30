# -*- coding: utf-8 -*-
"""Post-init: sincroniza período YYYYMM y fechas en reportes existentes."""
from __future__ import annotations


def post_init_hook(env):
    Report = env["justech.do.fiscal.report"].sudo()
    for report in Report.search([]):
        updates = {}
        if not report.period_code and report.date_from:
            updates["period_code"] = report.date_from.strftime("%Y%m")
        if updates:
            report.with_context(justech_skip_state_guard=True).write(updates)
        report._sync_dates_from_period_code()
    if hasattr(Report, "_compute_has_pending_approval"):
        Report.search([])._compute_has_pending_approval()
