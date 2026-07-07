"""Post-migrate UX-1 — integrar menús multimoneda bajo Contabilidad."""


def migrate(cr, version):
    from odoo import api, SUPERUSER_ID

    env = api.Environment(cr, SUPERUSER_ID, {})
    try:
        from odoo.addons.justech_multicurrency.hooks import _integrate_accounting_menus

        _integrate_accounting_menus(env)
    except Exception:
        pass
    try:
        env["hellenia.ui.menu.customizer"].apply_all()
    except Exception:
        pass
