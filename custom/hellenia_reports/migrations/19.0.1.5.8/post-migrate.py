# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0.html)
def migrate(cr, version):
    from odoo import api, SUPERUSER_ID

    env = api.Environment(cr, SUPERUSER_ID, {})
    if "res.company" in env and hasattr(
        env["res.company"], "hellenia_migrate_quotation_terms_to_html"
    ):
        env["res.company"].hellenia_migrate_quotation_terms_to_html()
