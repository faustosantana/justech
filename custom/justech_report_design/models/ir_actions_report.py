# -*- coding: utf-8 -*-
from odoo import api, models

_DELIVERY_REPORTS = frozenset(
    {
        "justech_report_design.report_justech_delivery_document",
        "justech_report_design.report_justech_delivery_document_sale",
        "justech_report_design.report_justech_delivery_document_invoice",
    }
)


class IrActionsReport(models.Model):
    _inherit = "ir.actions.report"

    @api.model
    def _jt_delivery_note_ids_for_report(self, report, res_ids):
        """Resuelve registros de conduce antes de imprimir desde otros modelos."""
        if not res_ids:
            return []
        Model = self.env[report.model]
        records = Model.browse(res_ids).exists()
        note_ids = []
        if report.model == "sale.order":
            for order in records:
                note_ids.append(order._jt_get_or_create_delivery_note().id)
        elif report.model == "account.move":
            for move in records:
                note_ids.append(move._jt_get_or_create_delivery_note().id)
        elif report.model == "stock.picking":
            for picking in records:
                note_ids.append(picking._jt_get_or_create_delivery_note().id)
        else:
            return list(res_ids)
        return note_ids

    @api.model
    def _render_qweb_pdf(self, report_ref, res_ids=None, data=None):
        report = self._get_report(report_ref)
        if report.report_name in _DELIVERY_REPORTS and report.model != "justech.delivery.note":
            note_ids = self._jt_delivery_note_ids_for_report(report, res_ids)
            note_report = self.env.ref(
                "justech_report_design.action_report_justech_delivery_note"
            )
            return super()._render_qweb_pdf(note_report.report_name, note_ids, data)
        return super()._render_qweb_pdf(report_ref, res_ids, data)

    @api.model
    def _render_qweb_html(self, report_ref, res_ids=None, data=None):
        report = self._get_report(report_ref)
        if report.report_name in _DELIVERY_REPORTS and report.model != "justech.delivery.note":
            note_ids = self._jt_delivery_note_ids_for_report(report, res_ids)
            note_report = self.env.ref(
                "justech_report_design.action_report_justech_delivery_note"
            )
            return super()._render_qweb_html(note_report.report_name, note_ids, data)
        return super()._render_qweb_html(report_ref, res_ids, data)
