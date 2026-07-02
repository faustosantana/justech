# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0.html)
from odoo import models


class BaseDocumentLayout(models.TransientModel):
    _inherit = "base.document.layout"

    def _get_preview_template(self):
        if (
            self.env.context.get("active_model") == "account.move"
            and self.env.context.get("active_id")
        ):
            return "justech_report_design.report_justech_invoice_wizard_iframe"
        return super()._get_preview_template()

    def _get_render_information(self, styles):
        res = super()._get_render_information(styles)
        if (
            self.env.context.get("active_model") == "account.move"
            and (active_id := self.env.context.get("active_id"))
        ):
            move = self.env["account.move"].browse(active_id)
            res["docs"] = move
            res["o"] = move
        return res
