"""Líneas persistentes de aplicación pago ↔ factura."""
from __future__ import annotations

from odoo import api, fields, models


class JustechPaymentApplicationLine(models.Model):
    _name = "justech.payment.application.line"
    _description = "Aplicación de pago por factura"
    _order = "invoice_date, invoice_name, id"

    payment_id = fields.Many2one(
        "account.payment",
        string="Pago",
        required=True,
        ondelete="cascade",
        index=True,
    )
    move_id = fields.Many2one("account.move", string="Factura", index=True, ondelete="set null")
    invoice_name = fields.Char(string="Factura", index=True)
    ncf = fields.Char(string="NCF", index=True)
    invoice_date = fields.Date(string="Fecha")
    invoice_total = fields.Monetary(string="Total factura", currency_field="currency_id")
    applied_amount = fields.Monetary(string="Monto aplicado", currency_field="currency_id")
    withholding_labels = fields.Char(string="Retenciones")
    withholding_amount = fields.Monetary(string="Monto retenido", currency_field="currency_id")
    net_amount = fields.Monetary(string="Neto", currency_field="currency_id")
    reconciliation_state = fields.Char(string="Estado conciliación")
    currency_id = fields.Many2one(related="payment_id.currency_id", store=True)
    company_id = fields.Many2one(related="payment_id.company_id", store=True, index=True)


class AccountPaymentApplication(models.Model):
    _inherit = "account.payment"

    justech_application_line_ids = fields.One2many(
        "justech.payment.application.line",
        "payment_id",
        string="Detalle por factura",
        copy=False,
    )
    justech_show_application_detail = fields.Boolean(
        compute="_compute_justech_show_application_detail",
    )

    @api.depends(
        "justech_application_line_ids",
        "justech_applied_amount",
        "justech_withholding_total",
        "reconciled_invoice_ids",
        "reconciled_bill_ids",
        "state",
    )
    def _compute_justech_show_application_detail(self):
        for pay in self:
            pay.justech_show_application_detail = bool(
                pay.justech_application_line_ids
                or pay.justech_applied_amount
                or pay.justech_withholding_total
                or pay.reconciled_invoice_ids
                or pay.reconciled_bill_ids
                or pay.state == "posted"
            )

    def _justech_applied_amount_for_invoice(self, move):
        """Monto aplicado a una factura según conciliaciones con el pago."""
        self.ensure_one()
        if not self.move_id or not move:
            return 0.0
        valid_types = self._get_valid_payment_account_types()
        pay_lines = self.move_id.line_ids.filtered(lambda l: l.account_id.account_type in valid_types)
        inv_lines = move.line_ids.filtered(lambda l: l.account_id.account_type in valid_types)
        applied = 0.0
        for inv_line in inv_lines:
            for partial in inv_line.matched_debit_ids | inv_line.matched_credit_ids:
                other = (
                    partial.debit_move_id
                    if partial.credit_move_id == inv_line
                    else partial.credit_move_id
                )
                if other in pay_lines:
                    applied += partial.amount
        if applied:
            return applied
        moves = self.reconciled_invoice_ids | self.reconciled_bill_ids
        if move in moves and len(moves) == 1 and self.justech_applied_amount:
            return self.justech_applied_amount
        if move in moves and len(moves) == 1:
            return self.amount
        return 0.0

    def _justech_reconciliation_label(self, move):
        labels = {
            "not_paid": "Sin pagar",
            "in_payment": "En proceso de pago",
            "partial": "Parcialmente pagada",
            "paid": "Pagada",
            "reversed": "Revertida",
        }
        return labels.get(move.payment_state, move.payment_state or "")

    def _justech_invoices_from_payment(self):
        """Facturas vinculadas al pago vía campos Odoo o conciliaciones."""
        self.ensure_one()
        moves = self.reconciled_invoice_ids | self.reconciled_bill_ids
        if moves:
            return moves
        moves = self.justech_withholding_line_ids.mapped("move_id")
        if moves:
            return moves
        if not self.move_id:
            return self.env["account.move"]
        valid_types = self._get_valid_payment_account_types()
        pay_lines = self.move_id.line_ids.filtered(lambda l: l.account_id.account_type in valid_types)
        found = self.env["account.move"]
        invoice_types = ("out_invoice", "out_refund", "in_invoice", "in_refund")
        for pay_line in pay_lines:
            for partial in pay_line.matched_debit_ids | pay_line.matched_credit_ids:
                other = (
                    partial.debit_move_id
                    if partial.credit_move_id == pay_line
                    else partial.credit_move_id
                )
                if other.move_id.move_type in invoice_types:
                    found |= other.move_id
        return found

    def _justech_sync_application_lines(self):
        AppLine = self.env["justech.payment.application.line"]
        for pay in self.filtered(lambda p: p.state == "posted"):
            moves = pay._justech_invoices_from_payment()
            pay.justech_application_line_ids.unlink()
            if not moves:
                continue
            for move in moves:
                wh_lines = pay.justech_withholding_line_ids.filtered(lambda w: w.move_id == move)
                wh_amount = sum(wh_lines.mapped("amount"))
                applied = pay._justech_applied_amount_for_invoice(move)
                if not applied and pay.justech_applied_amount and len(moves) == 1:
                    applied = pay.justech_applied_amount
                if not applied:
                    applied = pay.amount
                AppLine.create(
                    {
                        "payment_id": pay.id,
                        "move_id": move.id,
                        "invoice_name": move.name,
                        "ncf": self.env["justech.do.fiscal.data.provider"].get_ncf(move) or "",
                        "invoice_date": move.invoice_date,
                        "invoice_total": move.amount_total,
                        "applied_amount": applied,
                        "withholding_labels": ", ".join(filter(None, wh_lines.mapped("label"))),
                        "withholding_amount": wh_amount,
                        "net_amount": applied - wh_amount,
                        "reconciliation_state": pay._justech_reconciliation_label(move),
                    }
                )
