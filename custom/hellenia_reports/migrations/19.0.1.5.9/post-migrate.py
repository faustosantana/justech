# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0.html)
def migrate(cr, version):
    from odoo import SUPERUSER_ID, api

    env = api.Environment(cr, SUPERUSER_ID, {})
    Company = env["res.company"]
    if hasattr(Company, "hellenia_migrate_quotation_terms_to_html"):
        Company.hellenia_migrate_quotation_terms_to_html()
    # Alinear texto base corporativo al copy aprobado en BUGFIX-QUOTATION-TERMS-1
    from odoo.addons.hellenia_reports.models.res_company import (
        DEFAULT_HELLENIA_QUOTATION_TERMS_HTML,
    )

    for company in Company.search([]):
        raw = str(company.hellenia_quotation_terms or "")
        if "días calendario" in raw or "confirmación del pago correspondiente" in raw:
            company.hellenia_quotation_terms = DEFAULT_HELLENIA_QUOTATION_TERMS_HTML
