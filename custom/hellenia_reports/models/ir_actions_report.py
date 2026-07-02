# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0.html)
from odoo import api, models


class IrActionsReport(models.Model):
    _inherit = "ir.actions.report"

    def get_paperformat(self):
        """Paperformat compacto solo para cotizaciones (draft/sent)."""
        self.ensure_one()
        if self.env.context.get("hellenia_use_quotation_paperformat"):
            paperformat = self.env.ref(
                "hellenia_reports.paperformat_hellenia_quotation",
                raise_if_not_found=False,
            )
            if paperformat:
                return paperformat
        return super().get_paperformat()

    @api.model
    def _render_qweb_pdf(self, report_ref, res_ids=None, data=None):
        report = self._get_report(report_ref)
        if report.report_name == "sale.report_saleorder" and res_ids:
            if isinstance(res_ids, int):
                res_ids = [res_ids]
            orders = self.env["sale.order"].browse(res_ids)
            if orders and all(o.state in ("draft", "sent") for o in orders):
                return super(
                    IrActionsReport,
                    self.with_context(hellenia_use_quotation_paperformat=True),
                )._render_qweb_pdf(report_ref, res_ids=res_ids, data=data)
        return super()._render_qweb_pdf(report_ref, res_ids=res_ids, data=data)

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
