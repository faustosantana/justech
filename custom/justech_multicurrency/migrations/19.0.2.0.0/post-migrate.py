def migrate(cr, version):
    from odoo import api, SUPERUSER_ID

    env = api.Environment(cr, SUPERUSER_ID, {})
    from odoo.addons.justech_multicurrency.hooks import _restrict_pricelist_menus

    _restrict_pricelist_menus(env)
