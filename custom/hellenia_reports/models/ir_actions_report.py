# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0.html)
from odoo import api, models

HELLENIA_QUOTATION_REPORT = "hellenia_reports.report_hellenia_quotation"
STANDARD_SALE_REPORT = "sale.report_saleorder"


class IrActionsReport(models.Model):
    _inherit = "ir.actions.report"

    def _hellenia_quotation_redirect_report(self, report, res_ids):
        """Redirige cotizaciones draft/sent al reporte independiente Hellenia."""
        if report.report_name != STANDARD_SALE_REPORT or not res_ids:
            return report
        ids = res_ids if isinstance(res_ids, list) else [res_ids]
        orders = self.env["sale.order"].browse(ids)
        if not orders or not all(o.state in ("draft", "sent") for o in orders):
            return report
        hellenia_report = self.env.ref(
            "hellenia_reports.action_report_hellenia_quotation",
            raise_if_not_found=False,
        )
        return hellenia_report or report

    @api.model
    def _render_qweb_pdf(self, report_ref, res_ids=None, data=None):
        report = self._get_report(report_ref)
        report = self._hellenia_quotation_redirect_report(report, res_ids)
        return super()._render_qweb_pdf(report.report_name, res_ids=res_ids, data=data)

    @api.model
    def _render_qweb_html(self, report_ref, res_ids=None, data=None):
        report = self._get_report(report_ref)
        report = self._hellenia_quotation_redirect_report(report, res_ids)
        return super()._render_qweb_html(report.report_name, res_ids=res_ids, data=data)

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
