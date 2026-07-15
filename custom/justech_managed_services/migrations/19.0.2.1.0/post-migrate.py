# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0.html)


def migrate(cr, version):
    from odoo import SUPERUSER_ID, api

    env = api.Environment(cr, SUPERUSER_ID, {})
    if "justech.ms.form.seed" in env:
        env["justech.ms.form.seed"].seed_catalog()
