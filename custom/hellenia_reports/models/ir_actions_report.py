# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0.html)
from odoo import models


class IrActionsReport(models.Model):
    _inherit = "ir.actions.report"

    def _build_wkhtmltopdf_args(
        self,
        paperformat_id,
        landscape,
        specific_paperformat_args=None,
        set_viewport_size=False,
    ):
        """Force UTF-8 so wkhtmltopdf renders Spanish accents and currency NBSP correctly."""
        command_args = super()._build_wkhtmltopdf_args(
            paperformat_id,
            landscape,
            specific_paperformat_args=specific_paperformat_args,
            set_viewport_size=set_viewport_size,
        )
        if "--encoding" not in command_args:
            command_args.extend(["--encoding", "utf-8"])
        return command_args
