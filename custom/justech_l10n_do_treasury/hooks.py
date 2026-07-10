"""Hooks tesorería — un solo icono Contabilidad (Enterprise accountant)."""
from __future__ import annotations


def _ensure_payments_under_accountant(env):
    accounting = env.ref("accountant.menu_accounting", raise_if_not_found=False)
    if not accounting:
        return
    pagos = env.ref("justech_l10n_do_treasury.menu_finance_payments_root", raise_if_not_found=False)
    if pagos and pagos.parent_id != accounting:
        pagos.parent_id = accounting
    audit = env.ref("justech_l10n_do_reports.menu_justech_do_audit_root", raise_if_not_found=False)
    if audit and audit.parent_id != accounting:
        audit.parent_id = accounting


def post_init_hook(env):
    _ensure_payments_under_accountant(env)
